# Expense Claims Management API

A backend REST API for managing employee expense claims through a controlled approval and payment workflow.

## Features

- User management
- Employee, Manager and Finance roles
- Expense claim creation
- Claim status workflow
- Role-based authorization
- Manager-to-employee validation
- Duplicate claim detection
- Receipt text parsing
- Claim review/audit trail
- SQLite database
- FastAPI interactive API documentation

## Technology Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite
- Pytest
- Uvicorn

## Project Structure

```text
ExpenseClaims/
│
├── README.md
├── .env.example
├── .gitignore
│
└── backend/
    ├── requirements.txt
    ├── seed.py
    ├── expense_claims.db
    │
    ├── app/
    │   ├── __init__.py
    │   ├── database.py
    │   ├── main.py
    │   ├── models.py
    │   ├── schemas.py
    │   │
    │   └── services/
    │       ├── __init__.py
    │       ├── claims.py
    │       ├── duplicate.py
    │       └── receipt_parser.py
    │
    └── tests/