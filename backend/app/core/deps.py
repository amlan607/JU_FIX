"""Reusable FastAPI dependencies for authentication and role based access control.

Every authorisation decision is made on the backend (NFR-B, Coding Standard 3.6).
The frontend may hide a control, but it never grants access.
"""

from collections.abc import Callable, Iterable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.constants import AccountStatus, UserRole
from app.core.database import get_db
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.models.session_token import SessionToken
from app.models.user import User


def _extract_bearer_token(request: Request) -> str:
    """Read the bearer token from the Authorization header.

    Args:
        request: The incoming HTTP request.

    Returns:
        str: The raw JWT string.

    Raises:
        AuthenticationError: When the header is missing or malformed.
    """
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Authentication credentials were not provided.")
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the authenticated user from the request.

    The token signature, the revocation record and the account status are all
    checked, so a logged out or suspended user cannot keep using a valid token.

    Args:
        request: The incoming HTTP request.
        db: The active database session.

    Returns:
        User: The authenticated and active user.

    Raises:
        AuthenticationError: When the token is invalid, revoked or the account
            is not active.
    """
    token = _extract_bearer_token(request)
    claims = decode_access_token(token)
    if claims is None:
        raise AuthenticationError("The session token is invalid or has expired.")

    session_token = db.query(SessionToken).filter(SessionToken.token_id == claims.get("jti")).first()
    if session_token is None or session_token.revoked_at is not None:
        raise AuthenticationError("The session is no longer active. Please sign in again.")

    user = db.get(User, int(claims.get("sub", 0)))
    if user is None:
        raise AuthenticationError("The account linked to this session no longer exists.")
    if user.status != AccountStatus.ACTIVE.value:
        raise AuthenticationError("This account is not active.")

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Build a dependency that allows only the given roles.

    Args:
        *allowed_roles: The roles permitted to call the endpoint.

    Returns:
        Callable: A FastAPI dependency returning the authorised user.

    Example:
        >>> @router.get("/admin/reports", dependencies=[Depends(require_roles(UserRole.ADMIN))])
        ... def list_reports() -> dict: ...
    """
    permitted: set[str] = {role.value for role in allowed_roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        """Return the current user when the role is permitted."""
        if current_user.role not in permitted:
            raise PermissionDeniedError("Your role does not permit this action.")
        return current_user

    return dependency


def user_has_role(user: User, roles: Iterable[UserRole]) -> bool:
    """Report whether ``user`` holds any of ``roles``.

    Args:
        user: The user to inspect.
        roles: The roles to test against.

    Returns:
        bool: ``True`` when the user holds one of the roles.
    """
    return user.role in {role.value for role in roles}
