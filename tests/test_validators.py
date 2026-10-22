"""Unit tests for row validation; these tests do not need Postgres or S3."""

from lambdas.common.validators import validate_row


def good_row(**changes):
    """Return one valid user row with selected fields replaced."""
    row = {
        "user_id": "u1",
        "name": "Asha",
        "email": "asha@example.com",
        "monthly_income": "50000",
        "credit_score": "720",
        "employment_status": "Salaried",
        "age": "30",
    }
    row.update(changes)
    return row


def test_valid_row_is_trimmed_and_normalized():
    clean, error = validate_row(good_row(user_id=" u1 ", employment_status="Self Employed"))
    assert error is None
    assert clean["user_id"] == "u1"
    assert clean["employment_status"] == "self-employed"
    assert clean["credit_score"] == 720


def test_blank_name_is_stored_as_null():
    clean, error = validate_row(good_row(name="  "))
    assert error is None
    assert clean["name"] is None


def test_all_supported_employment_types_are_normalized():
    for status in ("Salaried", "Self-Employed", "Business"):
        clean, error = validate_row(good_row(employment_status=status))
        assert error is None
        assert clean["employment_status"] == status.lower()


def test_each_invalid_rule_is_rejected():
    invalid = [
        {"user_id": ""},
        {"email": "not-an-email"},
        {"monthly_income": "0"},
        {"monthly_income": "NaN"},
        {"credit_score": "299"},
        {"credit_score": "901"},
        {"credit_score": "700.5"},
        {"age": "17"},
        {"age": "101"},
        {"employment_status": "student"},
    ]
    for changes in invalid:
        clean, error = validate_row(good_row(**changes))
        assert clean is None and error, f"should reject: {changes}"


def test_missing_cells_do_not_raise():
    clean, error = validate_row({"user_id": "u1"})
    assert clean is None
    assert error
