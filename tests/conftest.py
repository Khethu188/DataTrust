
#!/usr/bin/env python3
"""
DataTrust — Shared Test Fixtures
===================================
Provides reusable test data for all test modules.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add project paths so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "validation"))
sys.path.insert(0, str(project_root / "src" / "data_generation"))
sys.path.insert(0, str(project_root / "src" / "utils"))


@pytest.fixture
def sample_customers():
    """Clean customer dataset."""
    return pd.DataFrame({
        "customer_id": [f"CUST-{i:05d}" for i in range(1, 101)],
        "first_name": [f"Name{i}" for i in range(1, 101)],
        "last_name": [f"Surname{i}" for i in range(1, 101)],
        "email": [f"user{i}@example.com" for i in range(1, 101)],
        "phone": [f"+27{np.random.randint(600000000, 899999999)}" for _ in range(100)],
        "province": np.random.choice(
            ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
             "Free State", "Limpopo", "Mpumalanga", "North West", "Northern Cape"],
            100
        ),
        "city": [f"City{i}" for i in range(1, 101)],
        "registration_date": pd.date_range("2020-01-01", periods=100, freq="D").strftime("%Y-%m-%d"),
        "is_active": np.random.choice([True, False], 100, p=[0.85, 0.15]),
    })


@pytest.fixture
def sample_transactions(sample_customers):
    """Clean transaction dataset."""
    customer_ids = sample_customers["customer_id"].tolist()
    return pd.DataFrame({
        "transaction_id": [f"TXN-{i:06d}" for i in range(1, 201)],
        "customer_id": np.random.choice(customer_ids, 200),
        "account_id": [f"ACC-{np.random.randint(1, 50):05d}" for _ in range(200)],
        "transaction_date": pd.date_range("2024-01-01", periods=200, freq="4h").strftime("%Y-%m-%d"),
        "amount": np.round(np.random.uniform(50, 50000, 200), 2),
        "currency": ["ZAR"] * 200,
        "transaction_type": np.random.choice(
            ["deposit", "withdrawal", "transfer", "payment"], 200
        ),
        "status": np.random.choice(
            ["completed", "pending", "failed", "reversed"], 200, p=[0.7, 0.15, 0.1, 0.05]
        ),
    })


@pytest.fixture
def corrupted_transactions(sample_transactions):
    """Transaction dataset with injected corruptions."""
    df = sample_transactions.copy()

    # Inject nulls
    df.loc[0:4, "amount"] = np.nan
    df.loc[5:9, "customer_id"] = np.nan

    # Inject negatives
    df.loc[10:14, "amount"] = -500.00

    # Inject duplicates
    dupes = df.iloc[20:25].copy()
    df = pd.concat([df, dupes], ignore_index=True)

    # Inject invalid currency
    df.loc[30:34, "currency"] = "INVALID"

    # Inject invalid status
    df.loc[35:39, "status"] = "BOGUS_STATUS"

    return df


@pytest.fixture
def sample_policies(sample_customers):
    """Clean policy dataset."""
    customer_ids = sample_customers["customer_id"].tolist()
    return pd.DataFrame({
        "policy_id": [f"POL-{i:05d}" for i in range(1, 51)],
        "customer_id": np.random.choice(customer_ids, 50),
        "policy_type": np.random.choice(
            ["life", "vehicle", "home", "health", "business"], 50
        ),
        "premium_amount": np.round(np.random.uniform(200, 5000, 50), 2),
        "start_date": pd.date_range("2023-01-01", periods=50, freq="7D").strftime("%Y-%m-%d"),
        "end_date": pd.date_range("2024-01-01", periods=50, freq="7D").strftime("%Y-%m-%d"),
        "status": np.random.choice(["active", "lapsed", "cancelled", "expired"], 50),
    })
