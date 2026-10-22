"""Generate a small BOM-prefixed CSV with both valid and invalid rows."""

import csv
from pathlib import Path

HEADER = [
    "user_id", "name", "email", "monthly_income", "credit_score",
    "employment_status", "age",
]
ROWS = [
    ["test-001", "Asha Rao", "asha@example.com", "50000", "720", "Salaried", "30"],
    ["test-002", "Ben Thomas", "ben@example.com", "42000", "690", "Self Employed", "35"],
    ["test-003", "Chitra Nair", "chitra@example.com", "90000", "760", "Business", "41"],
    ["test-004", "Dev Patel", "not-an-email", "50000", "700", "Salaried", "29"],
    ["test-005", "Esha Gupta", "esha@example.com", "50000", "700", "Salaried", "15"],
    ["test-006", "Farid Khan", "farid@example.com", "50000", "700", "Student", "25"],
    ["", "Gita Menon", "gita@example.com", "50000", "700", "Salaried", "33"],
    ["test-007", "Hari Singh", "hari@example.com", "-500", "700", "Salaried", "33"],
    ["test-001", "Asha Rao-Iyer", "asha@example.com", "55000", "725", "Salaried", "30"],
    ["test-008", "Ira Das", "ira@example.com", "60000", "950", "Salaried", "38"],
    ["test-009", "Jay Shah", "jay@example.com", "38000", "655", "Salaried", "27"],
]


def main():
    """Write the sample using Excel-style BOM and Windows line endings."""
    output = Path(__file__).resolve().parent.parent / "data" / "sample_small.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\r\n")
        writer.writerow(HEADER)
        writer.writerows(ROWS)
    print(f"Wrote {output}; expected 11 total, 5 valid, and 6 invalid rows.")


if __name__ == "__main__":
    main()
