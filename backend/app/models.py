from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class UserRole(str, Enum):
    STAFF = "staff"
    MANAGER = "manager"
    FINANCE = "finance"


class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100))

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    role: Mapped[UserRole] = mapped_column(String(20))

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    monthly_limit: Mapped[float] = mapped_column(
        Float,
        default=30000,
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    merchant: Mapped[str] = mapped_column(
        String(150)
    )

    description: Mapped[str] = mapped_column(
        Text
    )

    amount: Mapped[float] = mapped_column(
        Float
    )

    expense_date: Mapped[date] = mapped_column(
        Date
    )

    category: Mapped[str] = mapped_column(
        String(50)
    )

    status: Mapped[ClaimStatus] = mapped_column(
        String(20),
        default=ClaimStatus.DRAFT,
    )

    duplicate_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    duplicate_of: Mapped[int | None] = mapped_column(
        ForeignKey("claims.id"),
        nullable=True,
    )

    receipt_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    receipt_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class ClaimReview(Base):
    __tablename__ = "claim_reviews"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id")
    )

    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    action: Mapped[str] = mapped_column(
        String(30)
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )