#!/usr/bin/env python3

#!/usr/bin/env python3
"""
DataTrust — Load synthetic data into PostgreSQL
================================================
Creates tables with proper constraints and foreign keys,
then loads both clean and corrupted datasets.

Usage:
    python src/data_generation/load_to_postgres.py
    python src/data_generation/load_to_postgres.py --corrupted
"""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


# ── Configuration ────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "datatrust",
    "user": "datatrust_user",
    "password": "datatrust123",
}

CLEAN_DIR = Path("data/clean")
CORRUPTED_DIR = Path("data/corrupted")


# ── Schema Definition ────────────────────────────────────────
CREATE_SCHEMA_SQL = """
-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ── Customers (root entity) ─────────────────────────────
CREATE TABLE customers (
    customer_id         VARCHAR(10) PRIMARY KEY,
    first_name          VARCHAR(50),
    last_name           VARCHAR(50),
    id_number           VARCHAR(13),
    date_of_birth       VARCHAR(10),
    gender              VARCHAR(1),
    email               VARCHAR(100),
    phone               VARCHAR(20),
    province            VARCHAR(50),
    city                VARCHAR(50),
    registration_date   VARCHAR(10),
    customer_segment    VARCHAR(20),
    kyc_status          VARCHAR(10),
    risk_rating         VARCHAR(10),
    is_active           BOOLEAN
);

-- ── Accounts ────────────────────────────────────────────
CREATE TABLE accounts (
    account_id          VARCHAR(10) PRIMARY KEY,
    customer_id         VARCHAR(50),
    account_type        VARCHAR(20),
    currency            VARCHAR(5),
    balance             DECIMAL(15, 2),
    opened_date         VARCHAR(10),
    status              VARCHAR(10),
    branch_code         VARCHAR(10),
    interest_rate       DECIMAL(5, 2),
    last_activity_date  VARCHAR(10)
);

-- ── Transactions ────────────────────────────────────────
CREATE TABLE transactions (
    transaction_id      VARCHAR(10),
    customer_id         VARCHAR(50),
    account_id          VARCHAR(50),
    amount              DECIMAL(15, 2),
    currency            VARCHAR(5),
    transaction_date    VARCHAR(20),
    transaction_time    VARCHAR(8),
    transaction_type    VARCHAR(20),
    description         VARCHAR(100),
    channel             VARCHAR(10),
    status              VARCHAR(10),
    reference_number    VARCHAR(30)
);

-- ── Policies ────────────────────────────────────────────
CREATE TABLE policies (
    policy_id           VARCHAR(10) PRIMARY KEY,
    customer_id         VARCHAR(50),
    policy_type         VARCHAR(20),
    status              VARCHAR(10),
    start_date          VARCHAR(10),
    end_date            VARCHAR(10),
    premium_amount      DECIMAL(15, 2),
    cover_amount        DECIMAL(15, 2),
    currency            VARCHAR(5),
    payment_frequency   VARCHAR(10),
    beneficiary_count   INTEGER,
    underwriting_status VARCHAR(15)
);

-- ── Claims ──────────────────────────────────────────────
CREATE TABLE claims (
    claim_id            VARCHAR(10),
    policy_id           VARCHAR(50),
    customer_id         VARCHAR(50),
    claim_type          VARCHAR(20),
    claim_date          VARCHAR(20),
    claim_amount        DECIMAL(15, 2),
    approved_amount     DECIMAL(15, 2),
    currency            VARCHAR(5),
    status              VARCHAR(15),
    assessor_id         VARCHAR(10),
    resolution_date     VARCHAR(10),
    rejection_reason    VARCHAR(50)
);

-- ── Payments ────────────────────────────────────────────
CREATE TABLE payments (
    payment_id          VARCHAR(12),
    customer_id         VARCHAR(50),
    account_id          VARCHAR(50),
    policy_id           VARCHAR(50),
    amount              DECIMAL(15, 2),
    currency            VARCHAR(5),
    payment_date        VARCHAR(10),
    payment_method      VARCHAR(15),
    status              VARCHAR(10),
    reference           VARCHAR(30),
    failure_reason      VARCHAR(30)
);

-- ── Indexes for query performance ───────────────────────
CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_policies_customer ON policies(customer_id);
CREATE INDEX idx_claims_policy ON claims(policy_id);
CREATE INDEX idx_claims_customer ON claims(customer_id);
CREATE INDEX idx_payments_customer ON payments(customer_id);
CREATE INDEX idx_payments_account ON payments(account_id);
"""


def get_engine():
    """Create SQLAlchemy engine."""
    url = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(url)


def create_tables(engine):
    """Create all tables with schema."""
    print("Creating tables...")
    with engine.connect() as conn:
        conn.execute(text(CREATE_SCHEMA_SQL))
        conn.commit()
    print("  ✓ All tables created")


def load_dataset(engine, name, data_dir):
    """Load a single CSV into its corresponding table."""
    filepath = data_dir / f"{name}.csv"
    if not filepath.exists():
        print(f"  ✗ {filepath} not found — skipping")
        return

    df = pd.read_csv(filepath)
    df.to_sql(name, engine, if_exists="append", index=False)
    print(f"  ✓ {name:<15} {len(df):>8,} rows loaded")


def verify_counts(engine):
    """Print row counts for all tables."""
    tables = ["customers", "accounts", "transactions", "policies", "claims", "payments"]
    print("\nVerification:")
    with engine.connect() as conn:
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table:<15} {count:>8,} rows")


def main():
    parser = argparse.ArgumentParser(description="Load DataTrust data into PostgreSQL")
    parser.add_argument(
        "--corrupted", action="store_true",
        _ = "Load corrupted data instead of clean data",
    )
    args = parser.parse_args()

    data_dir = CORRUPTED_DIR if args.corrupted else CLEAN_DIR
    label = "CORRUPTED" if args.corrupted else "CLEAN"

    print("=" * 60)
    print(f"DataTrust — Loading {label} data into PostgreSQL")
    print("=" * 60)

    engine = get_engine()

    # Create fresh tables
    create_tables(engine)

    # Load each dataset
    print(f"\nLoading from {data_dir}/")
    datasets = ["customers", "accounts", "transactions", "policies", "claims", "payments"]
    for name in datasets:
        load_dataset(engine, name, data_dir)

    # Verify
    verify_counts(engine)

    print("\n" + "=" * 60)
    print("DONE ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
