"""Validate and normalize one user row from an uploaded CSV file."""

import re
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = [
    "user_id",
    "name",
    "email",
    "monthly_income",
    "credit_score",
    "employment_status",
    "age",
]
ALLOWED_EMPLOYMENT = {"salaried", "self-employed", "business"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _text(row, key):
    """Return a trimmed cell value, treating missing and empty values alike."""
    value = row.get(key)
    return str(value).strip() if value is not None else ""


def _whole_number(value):
    """Convert a whole-number value to int, or return None when invalid."""
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number != number.to_integral_value():
        return None
    return int(number)


def validate_row(row):
    """Return (clean_row, None) for valid rows, otherwise (None, reason)."""
    user_id = _text(row, "user_id")
    if not user_id:
        return None, "user_id is empty"

    email = _text(row, "email")
    if not EMAIL_PATTERN.fullmatch(email):
        return None, f"invalid email: {email!r}"

    try:
        income = Decimal(_text(row, "monthly_income").replace(",", ""))
    except (InvalidOperation, ValueError):
        return None, "monthly_income is not a number"
    if not income.is_finite() or income <= 0:
        return None, "monthly_income must be a finite number above 0"

    credit_score = _whole_number(_text(row, "credit_score"))
    if credit_score is None or not 300 <= credit_score <= 900:
        return None, "credit_score must be a whole number from 300 to 900"

    age = _whole_number(_text(row, "age"))
    if age is None or not 18 <= age <= 100:
        return None, "age must be a whole number from 18 to 100"

    employment = _text(row, "employment_status").lower().replace("_", "-").replace(" ", "-")
    if employment not in ALLOWED_EMPLOYMENT:
        return None, f"unknown employment_status: {employment!r}"

    return {
        "user_id": user_id,
        "name": _text(row, "name") or None,
        "email": email,
        "monthly_income": income,
        "credit_score": credit_score,
        "employment_status": employment,
        "age": age,
    }, None
