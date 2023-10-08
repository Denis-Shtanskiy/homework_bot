class EndpointErrorException(Exception):
    """An exception occurs when the endpoint fails to be accessed"""
    pass

class MissingEnvoirmentVariablesException(Exception):
    """An exception checks for absence of environment variables."""
    pass
