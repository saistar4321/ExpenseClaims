from sqlalchemy.orm import Session

from ..models import Claim


def check_duplicate(
    db: Session,
    claim: Claim,
) -> tuple[float, int | None]:
    """
    Conservative duplicate detection.

    A claim is considered a likely duplicate when the same employee
    has another claim with the same merchant, amount and expense date.
    """

    existing = (
        db.query(Claim)
        .filter(
            Claim.employee_id == claim.employee_id,
            Claim.id != claim.id,
            Claim.merchant == claim.merchant,
            Claim.amount == claim.amount,
            Claim.expense_date == claim.expense_date,
        )
        .first()
    )

    if existing:
        return 100.0, existing.id

    return 0.0, None