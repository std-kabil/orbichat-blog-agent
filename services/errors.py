class ServiceConfigurationError(RuntimeError):
    """Raised when an external service is called without required configuration."""


class ExternalServiceError(RuntimeError):
    """Raised when an external provider call fails permanently."""


class ProviderResponseError(RuntimeError):
    """Raised when a provider returns an unusable response shape."""
