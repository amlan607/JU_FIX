"""Medical certificate and sick leave request model (FR-F1 to FR-F4).

An approved certificate carries a unique reference ID and a digital signature
hash. The hash is derived from the certificate's own immutable fields, so a
verifier can confirm the document has not been altered without the medical
centre disclosing any clinical detail (FR-F4).
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import CertificateStatus
from app.core.database import Base
from app.models.user import utc_now


class CertificateRequest(Base):
    """A request for a medical certificate or sick leave document.

    Attributes:
        reference_id: The public identifier used for verification (FR-F4).
        signature: Hash proving the approved content has not been altered.
        status: One of :class:`~app.core.constants.CertificateStatus`.
        doctor_remarks: The doctor's reason for approval or rejection (FR-F2).
        leave_start: First day of the requested leave.
        leave_end: Last day of the requested leave.
    """

    __tablename__ = "certificate_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_id: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )
    signature: Mapped[str | None] = mapped_column(String(64), nullable=True)

    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), nullable=False, index=True
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    leave_start: Mapped[date] = mapped_column(Date, nullable=False)
    leave_end: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CertificateStatus.SUBMITTED.value, index=True
    )
    doctor_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    @property
    def leave_days(self) -> int:
        """Return the inclusive number of days covered by the leave."""
        return (self.leave_end - self.leave_start).days + 1

    def __repr__(self) -> str:
        """Return a debug representation without clinical content."""
        return f"<CertificateRequest id={self.id} status={self.status} ref={self.reference_id}>"
