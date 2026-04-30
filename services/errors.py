class ServiceConfigurationError(RuntimeError):
    """Raised when an external service is called without required configuration."""


class ExternalServiceError(RuntimeError):
    """Raised when an external provider call fails permanently."""


class ProviderResponseError(RuntimeError):
    """Raised when a provider returns an unusable response shape."""


class BudgetExceededError(RuntimeError):
    """Raised when a provider call would exceed configured agent budgets."""
