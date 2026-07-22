class ServiceError(Exception):
    """Base exception for service-layer failures."""


class ResourceNotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""


class ResourceConflictError(ServiceError):
    """Raised when a uniqueness or state conflict occurs."""


class InvalidUpdateError(ServiceError):
    """Raised when an update violates a business rule."""