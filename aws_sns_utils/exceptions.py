class SNSClientException(Exception):
    pass


class SNSClientTopicNotFound(SNSClientException):
    pass


class SNSClientPublishError(SNSClientException):
    pass
