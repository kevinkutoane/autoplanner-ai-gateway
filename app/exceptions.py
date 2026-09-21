"""Canonical gateway exception hierarchy."""

from typing import Optional


class GatewayException(Exception):
    """Base exception for all domain and HTTP errors in AutoPlanner AI Gateway."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.request_id = request_id


class InvalidRequestError(GatewayException):
    def __init__(self, message: str, request_id: Optional[str] = None):
        super().__init__(400, "INVALID_REQUEST", message, request_id)


class UnauthenticatedError(GatewayException):
    def __init__(self, message: str = "Authentication credentials missing or invalid.", request_id: Optional[str] = None):
        super().__init__(401, "UNAUTHENTICATED", message, request_id)


class ForbiddenError(GatewayException):
    def __init__(self, message: str = "Access forbidden.", request_id: Optional[str] = None):
        super().__init__(403, "FORBIDDEN", message, request_id)


class UnknownOperationError(GatewayException):
    def __init__(self, message: str = "The requested AI operation is unknown.", request_id: Optional[str] = None):
        super().__init__(404, "UNKNOWN_OPERATION", message, request_id)


class RequestTooLargeError(GatewayException):
    def __init__(self, message: str = "Request payload exceeds size limit.", request_id: Optional[str] = None):
        super().__init__(413, "REQUEST_TOO_LARGE", message, request_id)


class RateLimitedError(GatewayException):
    def __init__(self, message: str = "AI usage limit reached. Please try again later.", request_id: Optional[str] = None):
        super().__init__(429, "RATE_LIMITED", message, request_id)


class AIProviderError(GatewayException):
    def __init__(self, message: str = "Upstream AI provider encountered an error.", request_id: Optional[str] = None):
        super().__init__(502, "AI_PROVIDER_ERROR", message, request_id)


class AIServiceUnavailableError(GatewayException):
    def __init__(self, message: str = "AI Gateway is temporarily unavailable.", request_id: Optional[str] = None):
        super().__init__(503, "AI_SERVICE_UNAVAILABLE", message, request_id)


class InternalError(GatewayException):
    def __init__(self, message: str = "An unexpected error occurred.", request_id: Optional[str] = None):
        super().__init__(500, "INTERNAL_ERROR", message, request_id)
