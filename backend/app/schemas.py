from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import UserRole


class UserCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    email: str = Field(
        min_length=3,
        max_length=255,
    )

    role: UserRole

    manager_id: int | None = None

    monthly_limit: float = Field(
        default=30000,
        gt=0,
    )


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    manager_id: int | None
    monthly_limit: float

    model_config = ConfigDict(
        from_attributes=True
    )


class ClaimCreate(BaseModel):
    merchant: str = Field(
        min_length=1,
        max_length=150,
    )

    description: str = Field(
        min_length=1
    )

    amount: float = Field(
        gt=0
    )

    expense_date: date

    category: str = Field(
        min_length=1,
        max_length=50,
    )


class ClaimResponse(BaseModel):
    id: int
    employee_id: int
    merchant: str
    description: str
    amount: float
    expense_date: date
    category: str
    status: str
    duplicate_score: float
    duplicate_of: int | None

    receipt_filename: str | None
    receipt_path: str | None

    created_at: datetime
    paid_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )


class ClaimReviewResponse(BaseModel):
    id: int
    claim_id: int
    reviewer_id: int
    action: str
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class ReceiptParseRequest(BaseModel):
    text: str = Field(
        min_length=1
    )


class ReceiptParseResponse(BaseModel):
    merchant: str | None
    description: str | None
    amount: float | None
    expense_date: date | None
    category: str | None