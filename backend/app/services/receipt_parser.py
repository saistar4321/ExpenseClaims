import re
from datetime import date


def _find_amount(text: str) -> float | None:
    patterns = [
        r"(?:total|amount|grand\s+total)\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]{1,2})?)",
        r"(?:₹|rs\.?|inr)\s*([0-9]+(?:\.[0-9]{1,2})?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def _find_date(text: str) -> date | None:
    patterns = [
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        try:
            groups = match.groups()

            if len(groups) == 3 and len(groups[0]) == 4:
                return date(
                    int(groups[0]),
                    int(groups[1]),
                    int(groups[2]),
                )

            return date(
                int(groups[2]),
                int(groups[1]),
                int(groups[0]),
            )

        except ValueError:
            return None

    return None


def parse_receipt(text: str) -> dict:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    merchant = lines[0] if lines else None

    return {
        "merchant": merchant,
        "description": "Receipt expense",
        "amount": _find_amount(text),
        "expense_date": _find_date(text),
        "category": None,
    }