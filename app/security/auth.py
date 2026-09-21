"""Authentication boundary and IdentityProvider abstraction for AutoPlanner Gateway."""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from fastapi import Header

from app.config import settings
from app.exceptions import UnauthenticatedError, ForbiddenError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Represents the authenticated caller identity."""

    user_id: str
    client_id: str
    tier: str = "standard"
    is_authenticated: bool = True


class IdentityProvider(ABC):
    """Abstract interface for verifying client/user identity."""

    @abstractmethod
    async def verify_token(self, token: str) -> AuthenticatedIdentity:
        """Verifies a bearer token and returns the corresponding identity.
        
        Raises UnauthenticatedError or ForbiddenError if invalid.
        """
        pass


class ConfigurableIdentityProvider(IdentityProvider):
    """Default identity provider validating against configured keys and dev tokens."""

    async def verify_token(self, token: str) -> AuthenticatedIdentity:
        # Check against dev token if not in production
        if not settings.is_production and settings.DEV_BEARER_TOKEN and token == settings.DEV_BEARER_TOKEN:
            return AuthenticatedIdentity(
                user_id="dev-user",
                client_id="dev-client",
                tier="development",
                is_authenticated=True,
            )

        # Check against configured API keys
        if settings.API_KEYS and token in settings.API_KEYS:
            key_index = settings.API_KEYS.index(token)
            return AuthenticatedIdentity(
                user_id=f"api-client-{key_index}",
                client_id=f"client-{key_index}",
                tier="standard",
                is_authenticated=True,
            )

        # If we reach here, token was unrecognized
        raise UnauthenticatedError("Invalid or expired Bearer token.")


# Module singleton identity provider instance
_default_identity_provider: IdentityProvider = ConfigurableIdentityProvider()


def get_identity_provider() -> IdentityProvider:
    return _default_identity_provider


def set_identity_provider(provider: IdentityProvider) -> None:
    global _default_identity_provider
    _default_identity_provider = provider


async def get_current_identity(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> AuthenticatedIdentity:
    """FastAPI dependency to extract and verify caller identity from Authorization header."""
    if not authorization:
        # Permit anonymous ONLY if explicitly configured in non-production environment
        if not settings.AUTH_REQUIRED and not settings.is_production:
            logger.warning("Permitting anonymous request: AUTH_REQUIRED is false in development.")
            return AuthenticatedIdentity(
                user_id="anonymous-dev",
                client_id="anonymous-client",
                tier="development",
                is_authenticated=False,
            )
        raise UnauthenticatedError("Missing Authorization header with Bearer token.")

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthenticatedError(
            "Malformed Authorization header. Format must be 'Bearer <token>'."
        )

    token = parts[1].strip()
    if not token:
        raise UnauthenticatedError("Bearer token must not be empty.")

    provider = get_identity_provider()
    return await provider.verify_token(token)
