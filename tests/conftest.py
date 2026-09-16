# DataTrust - Shared Test Fixtures
import pandas as pd
import numpy as np  # noqa: F401


def make_customers(n=100):
    """Generate a small customers DataFrame for testing."""
    return pd.DataFrame({
        "customer_id": range(1, n + 1),
        "first_name": [f"Name{i}" for i in range(1, n + 1)],
        "last_name": [f"Surname{i}" for i in range(1, n + 1)],
        "email": [f"user{i}@example.com" for i in range(1, n + 1)],
        "phone": [f"+2781{i:07d}" for i in range(1, n + 1)],
        "province": np.random.choice(
            ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape"],
            size=n
        ),
        "city": [f"City{i}" for i in range(1, n + 1)],
        "id_number": [f"990101{i:07d}" for i in range(1, n + 1)],
    })


def make_accounts(n=100):
    """Generate a small accounts DataFrame for testing."""
    return pd.DataFrame({
        "account_id": range(1, n + 1),
        "customer_id": np.random.randint(1, 51, size=n),
        "account_type": np.random.choice(
            ["savings", "cheque", "investment"], size=n
        ),
        "balance": np.random.uniform(100, 50000, size=n).round(2),
        "currency": "ZAR",
        "branch_code": np.random.randint(100000, 999999, size=n),
    })


def make_transactions(n=200):
    """Generate a small transactions DataFrame for testing."""
    return pd.DataFrame({
        "transaction_id": range(1, n + 1),
        "account_id": np.random.randint(1, 51, size=n),
        "amount": np.random.uniform(10, 10000, size=n).round(2),
        "transaction_type": np.random.choice(
            ["debit", "credit", "transfer"], size=n
        ),
        "status": np.random.choice(
            ["completed", "pending", "failed"], size=n
        ),
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
    })
