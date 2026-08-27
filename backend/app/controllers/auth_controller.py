"""HTTP controller for accounts and authentication (FR-A).

Controllers stay lightweight: they validate the request shape through Pydantic,
call the service layer and wrap the result in the standard envelope
(Architecture 1.5).
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import success_response
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserResponse,
    VerifyAccountRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Accounts and Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """Create a new account and issue a verification token (FR-A1, FR-A2, FR-A3)."""
    result = auth_service.register_user(db, payload)
    return success_response(
        {
            "user": UserResponse.model_validate(result["user"]).model_dump(),
            "verification_required": result["verification_required"],
            "admin_approval_required": result["admin_approval_required"],
            "message": result["message"],
            "verification_token": result["verification_token"],
        }
    )


@router.post("/verify-account")
def verify_account(payload: VerifyAccountRequest, db: Session = Depends(get_db)) -> dict:
    """Activate an account using its verification token (FR-A2)."""
    user = auth_service.verify_account(db, payload.token)
    return success_response(
        {
            "user": UserResponse.model_validate(user).model_dump(),
            "message": "Your account has been verified.",
        }
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """Authenticate a user and issue a JWT session token (FR-A4, FR-A6, FR-A7)."""
    result = auth_service.authenticate(db, payload.identifier, payload.password)
    return success_response(
        {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "expires_at": result["expires_at"],
            "user": UserResponse.model_validate(result["user"]).model_dump(),
        }
    )


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Revoke the current session so the token can no longer be used (FR-A9)."""
    raw_token = request.headers.get("Authorization", "").partition(" ")[2]
    claims = decode_access_token(raw_token) or {}
    auth_service.logout(db, current_user, claims.get("jti", ""))
    return success_response({"message": "You have been signed out."})


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Start a password reset for a verified contact method (FR-A5)."""
    reset_token = auth_service.start_password_reset(db, payload.identifier)
    return success_response(
        {
            "message": "If the account exists, a reset link has been sent to the verified contact.",
            "reset_token": reset_token,
        }
    )


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Complete a password reset and end existing sessions (FR-A5)."""
    auth_service.complete_password_reset(db, payload.token, payload.new_password)
    return success_response({"message": "Your password has been updated. Please sign in."})


@router.get("/me")
def read_own_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Return the signed in user's own profile (FR-A8)."""
    return success_response(UserResponse.model_validate(current_user).model_dump())


@router.patch("/me")
def update_own_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update the signed in user's own profile (FR-A8)."""
    user = auth_service.update_profile(db, current_user, payload)
    return success_response(UserResponse.model_validate(user).model_dump())
