"""Development seed script.

Creates a small, realistic dataset so every teammate can run the application and
see populated screens. Run with ``python -m app.seed`` from the ``backend`` folder.

The seed is idempotent: running it twice does not duplicate rows.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.constants import AccountStatus, UserRole
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.doctor_profile import DoctorProfile
from app.models.user import User

#: Password used by every seeded demo account. Development only.
DEMO_PASSWORD = "JuFix@2026"

SEED_USERS = [
    ("STU-2021-370", "Oywon Islam", "oywon@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("STU-2021-350", "Mir Mohaiminul Islam", "mohaiminul@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("STU-2021-360", "Amlan Dutta Rahul", "amlan@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("STU-2021-375", "Ziad Muhammad Tahzeeb Rahman", "ziad@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("STU-2021-376", "Shadman Rahman", "shadman@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("STU-2021-364", "Md Sher Ali", "sher@ju.edu.bd", UserRole.STUDENT, "CSE", None),
    ("FAC-1001", "Dr. Nasima Akter", "nasima@ju.edu.bd", UserRole.FACULTY, "Physics", "Professor"),
    ("DOC-2001", "Dr. Rashedul Karim", "rashedul@ju.edu.bd", UserRole.DOCTOR, "Medical Centre", "Medical Officer"),
    ("DOC-2002", "Dr. Farhana Yasmin", "farhana@ju.edu.bd", UserRole.DOCTOR, "Medical Centre", "Medical Officer"),
    ("PHR-3001", "Habibur Rahman", "habibur@ju.edu.bd", UserRole.PHARMACIST, "Pharmacy", "Pharmacist"),
    ("ADM-4001", "Medical Centre Admin", "admin@ju.edu.bd", UserRole.ADMIN, "Administration", "System Admin"),
]

DOCTOR_PROFILES = {
    "DOC-2001": ("General Medicine", "R-101", 20),
    "DOC-2002": ("Paediatrics", "R-104", 15),
}


def seed_users(db: Session) -> dict[str, User]:
    """Insert the demo accounts if they are not present.

    Args:
        db: The active database session.

    Returns:
        dict[str, User]: Seeded users keyed by university id.
    """
    created: dict[str, User] = {}
    for university_id, name, email, role, department, designation in SEED_USERS:
        user = db.query(User).filter(User.university_id == university_id).first()
        if user is None:
            user = User(
                university_id=university_id,
                full_name=name,
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role.value,
                status=AccountStatus.ACTIVE.value,
                email_verified=True,
                department=department,
                designation=designation,
            )
            db.add(user)
            db.flush()
        created[university_id] = user
    return created


def seed_doctor_profiles(db: Session, users: dict[str, User]) -> None:
    """Attach clinical profiles to the seeded doctor accounts.

    Args:
        db: The active database session.
        users: Seeded users keyed by university id.
    """
    for university_id, (speciality, room, minutes) in DOCTOR_PROFILES.items():
        doctor = users.get(university_id)
        if doctor is None:
            continue
        exists = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor.id).first()
        if exists is None:
            db.add(
                DoctorProfile(
                    user_id=doctor.id,
                    speciality=speciality,
                    room_number=room,
                    consultation_minutes=minutes,
                )
            )


def run_seed() -> None:
    """Create the schema and populate the development dataset."""
    init_db()
    db = SessionLocal()
    try:
        users = seed_users(db)
        seed_doctor_profiles(db, users)
        db.commit()
        print(f"Seeded {len(users)} accounts. Demo password: {DEMO_PASSWORD}")
        print("Try:  ADM-4001 (admin)  DOC-2001 (doctor)  STU-2021-370 (student)")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
