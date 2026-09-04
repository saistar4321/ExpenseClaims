from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Claim, ClaimReview, ClaimStatus, User, UserRole


ALLOWED_TRANSITIONS = {
    ClaimStatus.DRAFT: {
        ClaimStatus.SUBMITTED,
    },
    ClaimStatus.SUBMITTED: {
        ClaimStatus.APPROVED,
        ClaimStatus.REJECTED,
    },
    ClaimStatus.APPROVED: {
        ClaimStatus.PAID,
    },
    ClaimStatus.REJECTED: set(),
    ClaimStatus.PAID: set(),
}


def get_claim(db: Session, claim_id: int) -> Claim:
    claim = db.get(Claim, claim_id)

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found",
        )

    return claim


def transition_claim(
    db: Session,
    claim: Claim,
    actor: User,
    new_status: ClaimStatus,
    comment: str | None = None,
) -> Claim:

    current_status = ClaimStatus(claim.status)

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition: "
                f"{current_status.value} -> {new_status.value}"
            ),
        )

    # Employee submits their own claim.
    if new_status == ClaimStatus.SUBMITTED:
        if actor.id != claim.employee_id:
            raise HTTPException(
                status_code=403,
                detail="Only the claim owner can submit the claim",
            )

    # Only managers can approve/reject.
    if new_status in {
        ClaimStatus.APPROVED,
        ClaimStatus.REJECTED,
    }:
        if actor.role != UserRole.MANAGER:
            raise HTTPException(
                status_code=403,
                detail="Only a manager can approve or reject a claim",
            )

        # Critical assessment rule:
        # a manager cannot approve their own claim.
        if actor.id == claim.employee_id:
            raise HTTPException(
                status_code=403,
                detail="A manager cannot approve their own claim",
            )
        employee = db.get(User, claim.employee_id)

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Claim employee not found",
            )

        if employee.manager_id != actor.id:
            raise HTTPException(
                status_code=403,
                detail="Manager is not assigned to this employee",
            )

    # Finance performs payment.
    if new_status == ClaimStatus.PAID:
        if actor.role != UserRole.FINANCE:
            raise HTTPException(
                status_code=403,
                detail="Only Finance can mark a claim as paid",
            )

        claim.paid_at = datetime.now(timezone.utc)

    claim.status = new_status

    review = ClaimReview(
        claim_id=claim.id,
        reviewer_id=actor.id,
        action=new_status.value,
        comment=comment,
    )

    db.add(review)
    db.commit()
    db.refresh(claim)

    return claim