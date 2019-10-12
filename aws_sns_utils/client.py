import logging
import os
from decimal import Decimal

import aiobotocore
import boto3
from botocore.exceptions import ClientError
from cached_property import threaded_cached_property
from json_encoder import json

from .exceptions import SNSClientPublishError, SNSClientTopicNotFound

logger = logging.getLogger(__name__)

MESSAGE_ATTRIBUTES_TYPE = {
    str: "String",
    int: "Number",
    Decimal: "Number",
    float: "Number",
    bytes: "Binary",
    list: "String.Array",
    tuple: "String.Array",
}


class BaseSNSClient:
    def __init__(self, endpoint_url=None, use_ssl=True, dry_run=False, log_level="debug", **kwargs):
        self.endpoint_url = endpoint_url
        self.use_ssl = use_ssl
        self.dry_run = dry_run
        self.client_options = kwargs
        self.log_level = log_level

    @threaded_cached_property
    def region_name(self):
        return self.client._client_config.region_name

    @property
    def log(self):
        return getattr(logger, self.log_level)

    @staticmethod
    def _prepare_message_attributes(attributes):
        message_attributes = {}
        for key, value in attributes.items():
            attr_type = MESSAGE_ATTRIBUTES_TYPE[type(value)]
            value_key = "BinaryValue" if attr_type == "Binary" else "StringValue"
            value = json.dumps(value) if attr_type in ("String.Array", "Number") else value
            message_attributes[key] = {"DataType": attr_type, value_key: value}
        return message_attributes

    def handle_exception(self, exc, prefix, topic, topic_arn):
        error_msg = (
            "error_publishing_message, "
            "prefix={}, "
            "topic={}, "
            "arn={}, "
            "error={!r}".format(prefix, topic, topic_arn, exc)
        )
        logger.error(error_msg)
        if exc.response["Error"]["Code"] == "NotFound":
            raise SNSClientTopicNotFound(error_msg)
        raise SNSClientPublishError(error_msg)


class SNSClient(BaseSNSClient):
    @threaded_cached_property
    def client(self):
        return boto3.client(
            "sns", endpoint_url=self.endpoint_url, use_ssl=self.use_ssl, **self.client_options
        )

    @threaded_cached_property
    def aws_account_id(self):
        if self.endpoint_url:
            return os.environ.get("AWS_ACCOUNT_ID", "000000000000")

        sts_client = boto3.client("sts", endpoint_url=self.endpoint_url, use_ssl=self.use_ssl)
        return sts_client.get_caller_identity()["Account"]

    def get_topic_arn(self, topic_name):
        return "arn:aws:sns:{}:{}:{}".format(self.region_name, self.aws_account_id, topic_name)

    def publish(self, prefix, topic, message_data, message_attributes=None):
        message_attributes = message_attributes or {}
        message_attributes = self._prepare_message_attributes(message_attributes)

        if self.dry_run:
            logger.info(
                "message=SNSClient.publish called, "
                "prefix={}, "
                "topic={}, "
                "message_data={!r}, "
                "message_attributes={!r}".format(prefix, topic, message_data, message_attributes)
            )
            return

        topic_arn = self.get_topic_arn("{}__{}".format(prefix, topic))
        message = json.dumps({"default": json.dumps(message_data)})

        try:
            self.client.publish(
                TopicArn=topic_arn,
                MessageStructure="json",
                Message=message,
                MessageAttributes=message_attributes,
            )
        except ClientError as exc:
            self.handle_exception(exc, prefix, topic, topic_arn)

        self.log(
            "published_message, "
            "prefix={}, "
            "topic={}, "
            "arn={}, "
            "message={!r}, "
            "message_attributes={!r}".format(prefix, topic, topic_arn, message, message_attributes)
        )

        return True


class AsyncSNSClient(BaseSNSClient):
    def __init__(self, endpoint_url=None, use_ssl=True, dry_run=False, **kwargs):
        super().__init__(endpoint_url, use_ssl, dry_run, **kwargs)
        self._session = aiobotocore.get_session()
        self.aws_account_id = None

    @threaded_cached_property
    def client(self):
        return self._session.create_client(
            "sns", endpoint_url=self.endpoint_url, use_ssl=self.use_ssl, **self.client_options
        )

    async def get_aws_account_id(self):
        if self.endpoint_url:
            return os.environ.get("AWS_ACCOUNT_ID", "000000000000")

        sts_client = self._session.create_client("sts", endpoint_url=self.endpoint_url, use_ssl=self.use_ssl)
        identity = await sts_client.get_caller_identity()
        return identity["Account"]

    async def get_topic_arn(self, topic_name):
        if self.aws_account_id is None:
            self.aws_account_id = await self.get_aws_account_id()

        return "arn:aws:sns:{}:{}:{}".format(self.region_name, self.aws_account_id, topic_name)

    async def publish(self, prefix, topic, message_data, message_attributes=None):
        message_attributes = message_attributes or {}
        message_attributes = self._prepare_message_attributes(message_attributes)

        if self.dry_run:
            logger.info(
                "message=SNSClient.publish called, "
                "prefix={}, "
                "topic={}, "
                "message_data={!r}, "
                "message_attributes={!r}".format(prefix, topic, message_data, message_attributes)
            )
            return

        topic_arn = await self.get_topic_arn("{}__{}".format(prefix, topic))
        message = json.dumps({"default": json.dumps(message_data)})

        try:
            await self.client.publish(
                TopicArn=topic_arn,
                MessageStructure="json",
                Message=message,
                MessageAttributes=message_attributes,
            )
        except ClientError as exc:
            self.handle_exception(exc, prefix, topic, topic_arn)

        self.log(
            "published_message, "
            "prefix={}, "
            "topic={}, "
            "arn={}, "
            "message={!r}, "
            "message_attributes={!r}".format(prefix, topic, topic_arn, message, message_attributes)
        )

        return True
