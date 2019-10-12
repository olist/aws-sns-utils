from unittest import mock

import pytest

from aws_sns_utils.client import SNSClient


@pytest.fixture
def mock_boto_client_sns():
    topics = {
        "Topics": [
            {"TopicArn": "arn:aws:region:id:TEST__test1"},
            {"TopicArn": "arn:aws:region:id:TEST__test2"},
            {"TopicArn": "arn:aws:region:id:TEST2__test1"},
            {"TopicArn": "arn:aws:region:id:test__test_status"},
        ]
    }
    client = mock.Mock(list_topics=mock.Mock(return_value=topics), publish=mock.Mock())
    return mock.patch("boto3.client", return_value=client)


@pytest.fixture
def sns_client():
    client = SNSClient()
    client.client = mock.Mock()
    client.aws_account_id = "423839475175"
    client.region_name = "us-east-1"
    return client
