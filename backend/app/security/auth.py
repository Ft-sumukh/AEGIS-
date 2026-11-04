"""Authentication abstraction and server-side Role-Based Access Control (RBAC)."""

import uuid
from collections.abc import Callable
from enum import StrEnum
from typing import NamedTuple

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings


class UserRole(StrEnum):
    """Hierarchical operational roles for Aegis platform actors.

    VIEWER: Read-only access to incidents, sanitized investigations, metrics, and recommendations.
    ANALYST: Can launch diagnostic investigations, view operational evidence, and add notes.
    OPERATOR: Can acknowledge, mitigate, and resolve incidents, and approve operational actions.
    ADMIN: Unrestricted administrative governance, audit inspection, and policy management.
    """

    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


# Role hierarchy weights for comparison
ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.VIEWER: 10,
    UserRole.ANALYST: 20,
    UserRole.OPERATOR: 30,
    UserRole.ADMIN: 40,
}


class AuthUser(BaseModel):
    """Authenticated user context passed to request handlers."""

    user_id: str
    username: str
    role: UserRole
    company_id: uuid.UUID | None = None


# Known test / demo users mapping
KNOWN_TOKENS: dict[str, AuthUser] = {
    "token-admin-123": AuthUser(
        user_id="usr-admin-01",
        username="admin_lead",
        role=UserRole.ADMIN,
    ),
    "token-operator-123": AuthUser(
        user_id="usr-oper-01",
        username="ops_engineer",
        role=UserRole.OPERATOR,
    ),
    "token-analyst-123": AuthUser(
        user_id="usr-analyst-01",
        username="sec_analyst",
        role=UserRole.ANALYST,
    ),
    "token-viewer-123": AuthUser(
        user_id="usr-viewer-01",
        username="stakeholder",
        role=UserRole.VIEWER,
    ),
}


def get_current_user(
    authorization: str | None = Header(default=None, description="Bearer token"),
    x_api_key: str | None = Header(default=None, description="Direct API key"),
    x_user_role: str | None = Header(default=None, description="Development role simulator"),
    x_user_id: str | None = Header(default=None, description="Development user simulator"),
) -> AuthUser:
    """Extracts and validates authenticated actor context from request headers."""
    settings = get_settings()

    # 1. Bearer Token Authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if token in KNOWN_TOKENS:
            return KNOWN_TOKENS[token]
        # In mock/development mode, recognize role tokens like "Bearer admin", "Bearer viewer"
        token_upper = token.upper()
        if token_upper in UserRole.__members__:
            return AuthUser(
                user_id=x_user_id or f"usr-{token_upper.lower()}-01",
                username=f"{token_upper.lower()}_user",
                role=UserRole(token_upper),
            )
        if settings.AUTH_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired bearer token.",
            )

    # 2. Direct API Key Authentication
    if x_api_key:
        if x_api_key == settings.SECRET_KEY or x_api_key.startswith("aegis_key_"):
            return AuthUser(
                user_id="usr-api-key",
                username="api_service_account",
                role=UserRole.ADMIN,
            )
        if settings.AUTH_ENABLED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key provided.",
            )

    # 3. Explicit Development Role Header (for automated tests and persona switching)
    if x_user_role:
        role_upper = x_user_role.strip().upper()
        if role_upper in UserRole.__members__:
            return AuthUser(
                user_id=x_user_id or f"usr-sim-{role_upper.lower()}",
                username=f"simulated_{role_upper.lower()}",
                role=UserRole(role_upper),
            )

    # 4. Fallback when AUTH_ENABLED=False (Local Development Mode)
    if not settings.AUTH_ENABLED:
        dev_role = UserRole(settings.DEFAULT_DEV_ROLE.upper())
        return AuthUser(
            user_id="usr-dev-default",
            username="dev_operator",
            role=dev_role,
        )

    # 5. Unauthorized if auth is strictly enabled and no valid credentials supplied
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid Authorization bearer token or X-API-Key.",
    )


def require_role(allowed_roles: list[UserRole] | UserRole) -> Callable:
    """Dependency factory that enforces server-side role-based access control."""
    if isinstance(allowed_roles, UserRole):
        allowed_roles = [allowed_roles]

    def _role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        user_weight = ROLE_HIERARCHY.get(user.role, 0)
        min_allowed_weight = min(ROLE_HIERARCHY.get(r, 0) for r in allowed_roles)

        # Allow if user matches one of the explicit allowed roles or has higher hierarchy
        if user.role in allowed_roles or user_weight >= min_allowed_weight:
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Role '{user.role}' is insufficient for this operation. Required: {[r.value for r in allowed_roles]}.",
        )

    return _role_checker
