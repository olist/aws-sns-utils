from unittest import mock

import pytest

from aws_sns_utils.client import SNSClient


@pytest.fixture
def sns_client():
    client = SNSClient()
    client.client = mock.Mock()
    client.aws_account_id = "423839475175"
    client.region_name = "us-east-1"
    return client
