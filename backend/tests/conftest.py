"""Shared pytest fixtures.

Every test runs against a throwaway in-memory SQLite database so that tests are
isolated, deterministic and safe to run in CI (Testing Standard 3.11).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AccountStatus, UserRole
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import create_app
from app.models.doctor_profile import DoctorProfile
from app.models.user import User

TEST_PASSWORD = "JuFix@2026"


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Provide a clean in-memory database session for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(name="client")
def client_fixture(db_session):
    """Provide a ``TestClient`` wired to the in-memory session."""
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(
    db_session,
    *,
    university_id: str = "STU-2021-370",
    role: UserRole = UserRole.STUDENT,
    status: AccountStatus = AccountStatus.ACTIVE,
    full_name: str = "Test User",
    email: str | None = None,
) -> User:
    """Insert and return an active test user.

    Args:
        db_session: The active test database session.
        university_id: The unique login handle.
        role: The role assigned to the account.
        status: The account status.
        full_name: Display name.
        email: Optional email address.

    Returns:
        User: The persisted user row.
    """
    user = User(
        university_id=university_id,
        full_name=full_name,
        email=email or f"{university_id.lower()}@ju.edu.bd",
        password_hash=hash_password(TEST_PASSWORD),
        role=role.value,
        status=status.value,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_doctor(db_session, *, university_id: str = "DOC-2001", speciality: str = "General Medicine") -> User:
    """Insert a doctor account together with its clinical profile."""
    doctor = make_user(
        db_session,
        university_id=university_id,
        role=UserRole.DOCTOR,
        full_name="Dr. Test Doctor",
    )
    db_session.add(
        DoctorProfile(user_id=doctor.id, speciality=speciality, room_number="R-101", consultation_minutes=20)
    )
    db_session.commit()
    return doctor


def auth_header(client, university_id: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    """Log in and return an Authorization header for the given account.

    Args:
        client: The FastAPI test client.
        university_id: The account login handle.
        password: The account password.

    Returns:
        dict[str, str]: A header dict containing the bearer token.
    """
    response = client.post(
        "/api/auth/login",
        json={"identifier": university_id, "password": password},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
