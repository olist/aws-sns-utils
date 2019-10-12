from unittest import mock

import asynctest
import pytest
from botocore.exceptions import ClientError

from aws_sns_utils.client import AsyncSNSClient, BaseSNSClient, SNSClient
from aws_sns_utils.exceptions import SNSClientPublishError, SNSClientTopicNotFound


@pytest.fixture
def account_id():
    return "000000080085"


@pytest.fixture
def async_sns_client(request, event_loop):
    return AsyncSNSClient()


@pytest.fixture
def base_sns_client():
    return BaseSNSClient()


def test_base_sns_client_handle_exception_publish_error(base_sns_client):
    exception = ClientError({"Error": {"Code": "Fodeu"}}, "error")

    with pytest.raises(SNSClientPublishError):
        base_sns_client.handle_exception(exception, None, None, None)


def test_base_sns_client_handle_exception_topic_not_found(base_sns_client):
    exception = ClientError({"Error": {"Code": "NotFound"}}, "error")

    with pytest.raises(SNSClientTopicNotFound):
        base_sns_client.handle_exception(exception, None, None, None)


def test_base_sns_client_prepare_message_attributes(base_sns_client):
    attributes = {"string": "strong", "number": 666, "bin": b"imagineimafile", "list": ["a", "b", "c"]}

    message_attributes = base_sns_client._prepare_message_attributes(attributes)

    assert message_attributes == {
        "string": {"DataType": "String", "StringValue": "strong"},
        "number": {"DataType": "Number", "StringValue": "666"},
        "bin": {"DataType": "Binary", "BinaryValue": b"imagineimafile"},
        "list": {"DataType": "String.Array", "StringValue": '["a", "b", "c"]'},
    }


def test_base_sns_client_prepare_message_attributes_empty(base_sns_client):
    assert base_sns_client._prepare_message_attributes({}) == {}


def test_sns_client_get_topic_arn(sns_client):
    assert (
        sns_client.get_topic_arn("sns_publisher__test")
        == "arn:aws:sns:us-east-1:423839475175:sns_publisher__test"
    )


def test_sns_client_get_topic_arn_with_endpoint_url():
    sns_client = SNSClient(endpoint_url="http://localhost:4100")
    sns_client.region_name = "us-east-1"
    assert (
        sns_client.get_topic_arn("sns_publisher__test")
        == "arn:aws:sns:us-east-1:000000000000:sns_publisher__test"
    )


def test_sns_client_get_topic_arn_with_endpoint_url_and_envvar(account_id, monkeypatch):
    monkeypatch.setenv("AWS_ACCOUNT_ID", account_id)
    sns_client = SNSClient(endpoint_url="http://localhost:4100")
    sns_client.region_name = "us-east-1"
    expected = "arn:aws:sns:us-east-1:{}:sns_publisher__test".format(account_id)
    assert sns_client.get_topic_arn("sns_publisher__test") == expected


def test_sns_client_dry_run(sns_client):
    sns_client.dry_run = True
    sns_client.publish("sns_publisher", "test", {"message": True})
    assert sns_client.client.call_count == 0


def test_sns_client_publish(sns_client):
    assert sns_client.publish("sns_publisher", "test", {"message": True}, {"at": "tr"})

    sns_client.client.publish.assert_called_with(
        Message='{"default": "{\\"message\\": true}"}',
        MessageStructure="json",
        TopicArn="arn:aws:sns:us-east-1:423839475175:sns_publisher__test",
        MessageAttributes={"at": {"DataType": "String", "StringValue": "tr"}},
    )


def test_sns_client_publish_handle_exception(sns_client):
    client_error = ClientError({"Error": {"Code": "NotFound", "Message": "Error"}}, "error")
    sns_client.handle_exception = mock.Mock(side_effect=SNSClientPublishError)
    sns_client.client.publish = mock.Mock(side_effect=client_error)

    with pytest.raises(SNSClientPublishError):
        sns_client.publish("team_india", "rulez", {"message": True})

    sns_client.handle_exception.assert_called_once()


def test_sns_client_publish_with_invalid_topic_name(sns_client):
    client_error = ClientError({"Error": {"Code": "NotFound", "Message": "Error"}}, "error")
    sns_client.client.publish = mock.Mock(side_effect=client_error)
    with pytest.raises(SNSClientTopicNotFound) as excinfo:
        sns_client.publish("team_india", "rulez", {"message": True})
    assert (
        str(excinfo.value.args[0])
        == "error_publishing_message, prefix=team_india, topic=rulez, arn=arn:aws:sns:us-east-1:423839475175:team_india__rulez, error=ClientError('An error occurred (NotFound) when calling the error operation: Error')"
    )


def test_sns_client_publish_with_error(sns_client):
    client_error = ClientError({"Error": {"Code": "500", "Message": "Error"}}, "error")
    sns_client.client.publish = mock.Mock(side_effect=client_error)
    with pytest.raises(SNSClientPublishError) as excinfo:
        sns_client.publish("sns_publisher", "test", {"message": True})
    assert (
        str(excinfo.value.args[0])
        == "error_publishing_message, prefix=sns_publisher, topic=test, arn=arn:aws:sns:us-east-1:423839475175:sns_publisher__test, error=ClientError('An error occurred (500) when calling the error operation: Error')"
    )


@mock.patch("boto3.client")
def test_sns_client_initialization(boto3_mock_client):
    sns_client = SNSClient(
        endpoint_url=None,
        use_ssl=True,
        dry_run=True,
        region_name="us-east-1",
        aws_access_key_id="my_access_key_id",
        aws_secret_access_key="my_secret_access_key",
    )

    assert sns_client.client
    boto3_mock_client.assert_called_with(
        "sns",
        endpoint_url=None,
        use_ssl=True,
        region_name="us-east-1",
        aws_access_key_id="my_access_key_id",
        aws_secret_access_key="my_secret_access_key",
    )


def test_sns_client_initialization_with_invalid_parameter():
    sns_client = SNSClient(
        endpoint_url=None,
        use_ssl=True,
        dry_run=True,
        region_name="us-east-1",
        aws_access_key_id="my_access_key_id",
        aws_secret_access_key="my_secret_access_key",
        im_invalid_param="im_invalid",
    )
    with pytest.raises(TypeError) as exc:
        sns_client.client

    expected_exception_message = "client() got an unexpected keyword argument 'im_invalid_param'"
    assert expected_exception_message == exc.value.args[0]


@pytest.mark.asyncio
async def test_async_sns_client(async_sns_client):
    assert async_sns_client._session
    assert async_sns_client.aws_account_id is None


@pytest.mark.asyncio
async def test_async_sns_client_get_aws_account_id():
    async_sns_client = AsyncSNSClient()
    async_sns_client._session.create_client = mock.Mock()
    mock_get_caller_identity = asynctest.CoroutineMock()
    async_sns_client._session.create_client.return_value.get_caller_identity = mock_get_caller_identity

    assert await async_sns_client.get_aws_account_id()

    async_sns_client._session.create_client.assert_called_once_with(
        "sts", endpoint_url=async_sns_client.endpoint_url, use_ssl=async_sns_client.use_ssl
    )
    mock_get_caller_identity.assert_called_once_with()


@pytest.mark.asyncio
async def test_async_sns_client_get_aws_account_id_custom_endpoint(monkeypatch):
    monkeypatch.delenv("AWS_ACCOUNT_ID", raising=False)
    async_sns_client = AsyncSNSClient(endpoint_url="http://hue.com/")

    result = await async_sns_client.get_aws_account_id()

    assert result == "000000000000"


@pytest.mark.asyncio
async def test_async_sns_client_get_aws_account_id_custom_endpoint_custom_account_id(
    async_sns_client, account_id, monkeypatch
):
    monkeypatch.setenv("AWS_ACCOUNT_ID", account_id)
    async_sns_client = AsyncSNSClient(endpoint_url="http://hue.com/")

    result = await async_sns_client.get_aws_account_id()

    assert result == account_id


@pytest.mark.asyncio
async def test_async_sns_client_get_topic_arn(async_sns_client, account_id):
    topic_name = "top__ico"
    async_sns_client.get_aws_account_id = asynctest.CoroutineMock(return_value=account_id)
    async_sns_client.region_name = "us-east-1"

    result = await async_sns_client.get_topic_arn(topic_name)

    assert result == "arn:aws:sns:us-east-1:{}:{}".format(account_id, topic_name)
    async_sns_client.get_aws_account_id.assert_called_once()


@pytest.mark.asyncio
async def test_async_sns_client_get_topic_arn_cached_account_id(async_sns_client):
    topic_name = "top__ico"
    async_sns_client.aws_account_id = "000000000000"
    async_sns_client.get_aws_account_id = asynctest.CoroutineMock()
    async_sns_client.region_name = "us-east-1"

    result = await async_sns_client.get_topic_arn(topic_name)

    assert result == "arn:aws:sns:us-east-1:000000000000:{}".format(topic_name)
    async_sns_client.get_aws_account_id.assert_not_called()


@pytest.mark.asyncio
async def test_async_sns_client_publish():
    async_sns_client = AsyncSNSClient()
    async_sns_client.aws_account_id = "123"
    async_sns_client.client = mock.Mock(publish=asynctest.CoroutineMock())
    async_sns_client.region_name = "us-east-1"
    message = {"msg": True}

    result = await async_sns_client.publish("top", "ico", message, {"at": "tr"})

    assert result is True
    async_sns_client.client.publish.assert_called_once_with(
        TopicArn="arn:aws:sns:us-east-1:123:top__ico",
        MessageStructure="json",
        Message='{"default": "{\\"msg\\": true}"}',
        MessageAttributes={"at": {"DataType": "String", "StringValue": "tr"}},
    )


@pytest.mark.asyncio
async def test_async_sns_client_publish_dry_run():
    async_sns_client = AsyncSNSClient(dry_run=True)
    async_sns_client.client = asynctest.CoroutineMock()

    result = await async_sns_client.publish("sns_publisher", "test", {"message": True})

    assert result is None
    async_sns_client.client.publish.assert_not_called()


@pytest.mark.asyncio
async def test_async_sns_client_publish_client_error():
    async_sns_client = AsyncSNSClient()
    async_sns_client.aws_account_id = "123"
    async_sns_client.region_name = "us-east-1"
    client_error = ClientError({"Error": {"Code": "Eita Geovana", "Message": "Error"}}, "error")
    async_sns_client.client = mock.Mock(publish=asynctest.CoroutineMock(side_effect=client_error))

    with pytest.raises(SNSClientPublishError):
        await async_sns_client.publish("sns_publisher", "test", {"message": True})
