from pathlib import Path
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import (
    Claim,
    ClaimReview,
    ClaimStatus,
    User,
    UserRole,
)
from .schemas import (
    ClaimCreate,
    ClaimResponse,
    ClaimReviewResponse,
    ReceiptParseRequest,
    ReceiptParseResponse,
    UserCreate,
    UserResponse,
)
from .services.claims import (
    get_claim,
    transition_claim,
)
from .services.duplicate import check_duplicate
from .services.receipt_parser import parse_receipt


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Expense Claims API",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Receipt storage
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "expense-claims-api",
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    if data.manager_id is not None:
        manager = db.get(
            User,
            data.manager_id,
        )

        if not manager:
            raise HTTPException(
                status_code=404,
                detail="Manager not found",
            )

        if manager.role != UserRole.MANAGER:
            raise HTTPException(
                status_code=400,
                detail="manager_id must reference a manager",
            )

    user = User(
        name=data.name,
        email=data.email,
        role=data.role,
        manager_id=data.manager_id,
        monthly_limit=data.monthly_limit,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@app.get(
    "/users",
    response_model=list[UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .order_by(User.id)
        .all()
    )


@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.get(
        User,
        user_id,
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

@app.post(
    "/claims",
    response_model=ClaimResponse,
    status_code=201,
)
def create_claim(
    data: ClaimCreate,
    employee_id: int,
    db: Session = Depends(get_db),
):
    employee = db.get(
        User,
        employee_id,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    if employee.role != UserRole.STAFF:
        raise HTTPException(
            status_code=403,
            detail="Only staff users can create employee claims",
        )

    claim = Claim(
        employee_id=employee.id,
        merchant=data.merchant,
        description=data.description,
        amount=data.amount,
        expense_date=data.expense_date,
        category=data.category,
        status=ClaimStatus.DRAFT,
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    duplicate_score, duplicate_of = check_duplicate(
        db,
        claim,
    )

    claim.duplicate_score = duplicate_score
    claim.duplicate_of = duplicate_of

    db.commit()
    db.refresh(claim)

    return claim


@app.get(
    "/claims",
    response_model=list[ClaimResponse],
)
def list_claims(
    employee_id: int | None = None,
    status: ClaimStatus | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Claim)

    if employee_id is not None:
        query = query.filter(
            Claim.employee_id == employee_id
        )

    if status is not None:
        query = query.filter(
            Claim.status == status
        )

    return (
        query
        .order_by(Claim.id)
        .all()
    )


@app.get(
    "/claims/{claim_id}",
    response_model=ClaimResponse,
)
def read_claim(
    claim_id: int,
    db: Session = Depends(get_db),
):
    return get_claim(
        db,
        claim_id,
    )


# ---------------------------------------------------------------------------
# Receipt upload
# ---------------------------------------------------------------------------

@app.post(
    "/claims/{claim_id}/receipt",
    response_model=ClaimResponse,
)
def upload_receipt(
    claim_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed",
        )

    extension = allowed_types[
        file.content_type
    ]

    filename = (
        f"{uuid4().hex}"
        f"{extension}"
    )

    claim_dir = (
        UPLOAD_DIR
        / str(claim.id)
    )

    claim_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        claim_dir
        / filename
    )

    content = file.file.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Receipt image must be 5 MB or smaller",
        )

    destination.write_bytes(
        content
    )

    claim.receipt_filename = file.filename
    claim.receipt_path = str(
        destination
    )

    db.commit()
    db.refresh(claim)

    return claim


@app.get(
    "/claims/{claim_id}/receipt"
)
def get_receipt(
    claim_id: int,
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    if not claim.receipt_path:
        raise HTTPException(
            status_code=404,
            detail="No receipt uploaded for this claim",
        )

    path = Path(
        claim.receipt_path
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Receipt file not found",
        )

    return FileResponse(path)


# ---------------------------------------------------------------------------
# Claim workflow
# ---------------------------------------------------------------------------

@app.post(
    "/claims/{claim_id}/submit",
    response_model=ClaimResponse,
)
def submit_claim(
    claim_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    employee = db.get(
        User,
        employee_id,
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return transition_claim(
        db,
        claim,
        employee,
        ClaimStatus.SUBMITTED,
    )


@app.post(
    "/claims/{claim_id}/approve",
    response_model=ClaimResponse,
)
def approve_claim(
    claim_id: int,
    manager_id: int,
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    manager = db.get(
        User,
        manager_id,
    )

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager not found",
        )

    return transition_claim(
        db,
        claim,
        manager,
        ClaimStatus.APPROVED,
    )


@app.post(
    "/claims/{claim_id}/reject",
    response_model=ClaimResponse,
)
def reject_claim(
    claim_id: int,
    manager_id: int,
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    manager = db.get(
        User,
        manager_id,
    )

    if not manager:
        raise HTTPException(
            status_code=404,
            detail="Manager not found",
        )

    return transition_claim(
        db,
        claim,
        manager,
        ClaimStatus.REJECTED,
    )


@app.post(
    "/claims/{claim_id}/pay",
    response_model=ClaimResponse,
)
def pay_claim(
    claim_id: int,
    finance_id: int,
    db: Session = Depends(get_db),
):
    claim = get_claim(
        db,
        claim_id,
    )

    finance = db.get(
        User,
        finance_id,
    )

    if not finance:
        raise HTTPException(
            status_code=404,
            detail="Finance user not found",
        )

    return transition_claim(
        db,
        claim,
        finance,
        ClaimStatus.PAID,
    )


# ---------------------------------------------------------------------------
# Claim reviews / audit trail
# ---------------------------------------------------------------------------

@app.get(
    "/claims/{claim_id}/reviews",
    response_model=list[ClaimReviewResponse],
)
def list_claim_reviews(
    claim_id: int,
    db: Session = Depends(get_db),
):
    get_claim(
        db,
        claim_id,
    )

    return (
        db.query(ClaimReview)
        .filter(
            ClaimReview.claim_id == claim_id
        )
        .order_by(ClaimReview.id)
        .all()
    )


# ---------------------------------------------------------------------------
# Receipt parser
# ---------------------------------------------------------------------------

@app.post(
    "/receipts/parse",
    response_model=ReceiptParseResponse,
)
def parse_receipt_endpoint(
    data: ReceiptParseRequest,
):
    return parse_receipt(
        data.text
    )