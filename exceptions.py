"""Exceptions file."""


class EndpointErrorException(Exception):
    """An exception occurs when the endpoint fails to be accessed."""
    pass


class MissingEnvoirmentVariablesException(Exception):
    """An exception checks for absence of environment variables."""
    pass


class JsonErrorException(Exception):
    """An exception checks decode json."""
    pass


class RequestErrorException(Exception):
    """Error request"""
    pass


class TelegramErrorException(Exception):
    """An exception checks telegram error."""
    pass
