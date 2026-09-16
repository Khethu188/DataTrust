
#!/usr/bin/env python3
"""
DataTrust — Synthetic Financial Data Generator & Corruption Injector
====================================================================
Generates 6 interrelated datasets for a South African financial
institution, plus a corruption injector that introduces realistic
data-quality defects for testing the DataTrust validation engine.

Usage:
    python generate_data.py                      # Generate clean + corrupted
    python generate_data.py --clean-only         # Generate clean data only
    python generate_data.py --output-dir ./data  # Custom output directory
    python generate_data.py --format parquet     # Output as Parquet

Datasets:
    customers      — 1,000 records × 15 columns
    accounts       — 1,500 records × 10 columns
    transactions   — 50,000 records × 12 columns
    policies       — 800 records × 12 columns
    claims         — 2,000 records × 12 columns
    payments       — 10,000 records × 11 columns

Total: 65,300 clean records
"""

import argparse
import json
import os  # noqa: F401
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ── Configuration ────────────────────────────────────────────
SEED = 42
TODAY = datetime(2026, 9, 15)

DATASET_CONFIG = {
    "customers": 1_000,
    "accounts": 1_500,
    "transactions": 50_000,
    "policies": 800,
    "claims": 2_000,
    "payments": 10_000,
}


# ── Reference Data ───────────────────────────────────────────
SA_PROVINCES = [
    "Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
    "Free State", "Limpopo", "Mpumalanga", "North West", "Northern Cape",
]

SA_CITIES = {
    "Gauteng": ["Johannesburg", "Pretoria", "Sandton", "Centurion", "Midrand"],
    "Western Cape": ["Cape Town", "Stellenbosch", "Paarl", "George"],
    "KwaZulu-Natal": ["Durban", "Pietermaritzburg", "Umhlanga", "Ballito"],
    "Eastern Cape": ["Port Elizabeth", "East London", "Makhanda"],
    "Free State": ["Bloemfontein", "Welkom"],
    "Limpopo": ["Polokwane", "Tzaneen"],
    "Mpumalanga": ["Nelspruit", "Witbank"],
    "North West": ["Rustenburg", "Mahikeng"],
    "Northern Cape": ["Kimberley", "Upington"],
}

FIRST_NAMES = [
    "Thabo", "Sipho", "Nomsa", "Lerato", "Bongani", "Zanele", "Mandla",
    "Naledi", "Kagiso", "Palesa", "Tshepo", "Lindiwe", "Sibusiso", "Ayanda",
    "Mpho", "Nokuthula", "Themba", "Busisiwe", "Siyabonga", "Nompumelelo",
    "Khethukuthula", "Andile", "Nhlanhla", "Zinhle", "Lwazi", "Thandiwe",
    "Vusi", "Nonhlanhla", "Dumisani", "Precious", "Thandeka", "Mthunzi",
    "Nosipho", "Bheki", "Anele", "Nokukhanya", "Sandile", "Mbali",
]

LAST_NAMES = [
    "Nkosi", "Dlamini", "Zulu", "Ndlovu", "Mkhize", "Mokoena", "Molefe",
    "Khumalo", "Sithole", "Ngcobo", "Pillay", "Govender", "Naidoo",
    "Maharaj", "Van der Merwe", "Botha", "Du Plessis", "Pretorius",
    "Jacobs", "Williams", "Abrahams", "Petersen", "Mahlangu", "Maseko",
    "Chauke", "Mabaso", "Radebe", "Cele", "Zwane", "Shabalala",
]

ACCOUNT_TYPES = ["SAVINGS", "CHEQUE", "FIXED_DEPOSIT", "MONEY_MARKET", "CREDIT"]
TRANSACTION_TYPES = [
    "PAYMENT", "TRANSFER", "DEPOSIT", "WITHDRAWAL",
    "DEBIT_ORDER", "FEE", "INTEREST", "REVERSAL",
]
POLICY_TYPES = ["LIFE", "FUNERAL", "INVESTMENT", "RETIREMENT", "HEALTH", "SHORT_TERM"]
POLICY_STATUSES = ["ACTIVE", "LAPSED", "CANCELLED", "MATURED", "PAID_UP"]
CLAIM_STATUSES = ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "PAID", "DISPUTED"]
CLAIM_TYPES = ["DEATH", "DISABILITY", "HOSPITAL", "MATURITY", "SURRENDER", "RETRENCHMENT"]
PAYMENT_METHODS = ["EFT", "DEBIT_ORDER", "CASH", "CARD", "MOBILE"]
PAYMENT_STATUSES = ["COMPLETED", "PENDING", "FAILED", "REVERSED"]


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def random_date(start, end=None):
    """Return a random datetime between start and end.

    Args:
        start: int (year) or datetime object.
        end: datetime object. Defaults to TODAY.
    """
    if end is None:
        end = TODAY
    if isinstance(start, int):
        start = datetime(start, 1, 1)
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def random_id_number() -> str:
    """Generate a realistic-looking SA ID number (13 digits)."""
    year = random.randint(60, 99) if random.random() < 0.3 else random.randint(0, 26)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    seq = random.randint(0, 9999)
    citizen = random.choice([0, 1])
    return f"{year:02d}{month:02d}{day:02d}{seq:04d}{citizen}8{random.randint(0, 9)}"


def random_phone() -> str:
    """Generate a realistic SA mobile number."""
    prefix = random.choice([
        "060", "061", "062", "063", "064", "065", "066", "067",
        "068", "069", "071", "072", "073", "074", "076", "078",
        "079", "081", "082", "083", "084",
    ])
    return f"+27{prefix[1:]}{random.randint(1000000, 9999999)}"


def random_email(first: str, last: str) -> str:
    """Generate a plausible email address."""
    domain = random.choice(["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"])
    sep = random.choice([".", "_", ""])
    num = random.randint(1, 999)
    return f"{first.lower()}{sep}{last.lower().replace(' ', '')}{num}@{domain}"


# ═══════════════════════════════════════════════════════════════
# DATA GENERATORS
# ═══════════════════════════════════════════════════════════════

def generate_customers(n: int = DATASET_CONFIG["customers"]) -> pd.DataFrame:
    """Generate synthetic customer records."""
    rows = []
    for i in range(1, n + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        province = random.choice(SA_PROVINCES)
        city = random.choice(SA_CITIES[province])
        rows.append({
            "customer_id": f"C{i:04d}",
            "first_name": first,
            "last_name": last,
            "id_number": random_id_number(),
            "date_of_birth": random_date(1950, datetime(2005, 1, 1)).strftime("%Y-%m-%d"),
            "gender": random.choice(["M", ""]),
            "email": random_email(first, last),
            "phone": random_phone(),
            "province": province,
            "city": city,
            "registration_date": random_date(2015).strftime("%Y-%m-%d"),
            "customer_segment": random.choices(
                ["RETAIL", "PREMIUM", "PRIVATE_WEALTH", "CORPORATE"],
                weights=[50, 30, 10, 10],
            )[0],
            "kyc_status": random.choices(
                ["VERIFIED", "PENDING", "EXPIRED"], weights=[85, 10, 5]
            )[0],
            "risk_rating": random.choices(
                ["LOW", "MEDIUM", "HIGH"], weights=[60, 30, 10]
            )[0],
            "is_active": random.choices([True, False], weights=[90, 10])[0],
        })
    return pd.DataFrame(rows)


def generate_accounts(
    customers_df: pd.DataFrame,
    n: int = DATASET_CONFIG["accounts"],
) -> pd.DataFrame:
    """Generate synthetic account records linked to customers."""
    customer_ids = customers_df["customer_id"].tolist()
    rows = []
    for i in range(1, n + 1):
        acc_type = random.choice(ACCOUNT_TYPES)
        open_date = random_date(2016)
        balance_ranges = {
            "SAVINGS": (100, 500_000),
            "CHEQUE": (-5_000, 200_000),
            "FIXED_DEPOSIT": (10_000, 2_000_000),
            "MONEY_MARKET": (50_000, 5_000_000),
            "CREDIT": (-100_000, 0),
        }
        lo, hi = balance_ranges[acc_type]
        rows.append({
            "account_id": f"A{i:04d}",
            "customer_id": random.choice(customer_ids),
            "account_type": acc_type,
            "currency": "ZAR",
            "balance": round(random.uniform(lo, hi), 2),
            "opened_date": open_date.strftime("%Y-%m-%d"),
            "status": random.choices(
                ["ACTIVE", "DORMANT", "CLOSED", "FROZEN"],
                weights=[80, 10, 7, 3],
            )[0],
            "branch_code": f"BR{random.randint(100, 999)}",
            "interest_rate": round(random.uniform(0.5, 12.5), 2) if acc_type != "CHEQUE" else 0.0,
            "last_activity_date": random_date(open_date, TODAY).strftime("%Y-%m-%d"),
        })
    return pd.DataFrame(rows)


def generate_transactions(
    accounts_df: pd.DataFrame,
    n: int = DATASET_CONFIG["transactions"],
) -> pd.DataFrame:
    """Generate synthetic transaction records linked to accounts."""
    account_ids = accounts_df["account_id"].tolist()
    acct_to_cust = dict(zip(accounts_df["account_id"], accounts_df["customer_id"]))
    rows = []
    for i in range(1, n + 1):
        acc = random.choice(account_ids)
        txn_type = random.choice(TRANSACTION_TYPES)

        # Realistic lognormal distributions per transaction type
        amount_params = {
            "FEE": ("uniform", 5, 500),
            "INTEREST": ("uniform", 10, 5_000),
            "PAYMENT": ("lognormal", 7, 1.2),
            "DEBIT_ORDER": ("lognormal", 7, 1.2),
            "TRANSFER": ("lognormal", 7.5, 1.5),
            "DEPOSIT": ("lognormal", 8, 1.0),
            "WITHDRAWAL": ("lognormal", 6.5, 1.0),
            "REVERSAL": ("uniform", 50, 50_000),
        }
        dist, p1, p2 = amount_params[txn_type]
        if dist == "uniform":
            amount = round(random.uniform(p1, p2), 2)
        else:
            amount = round(min(np.random.lognormal(p1, p2), 2_000_000), 2)

        rows.append({
            "transaction_id": f"TX{i:06d}",
            "customer_id": acct_to_cust[acc],
            "account_id": acc,
            "amount": amount,
            "currency": "ZAR",
            "transaction_date": random_date(2024).strftime("%Y-%m-%d"),
            "transaction_time": f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
            "transaction_type": txn_type,
            "description": f"{txn_type.replace('_', ' ').title()} - Ref {random.randint(100000, 999999)}",
            "channel": random.choices(
                ["ONLINE", "MOBILE", "BRANCH", "ATM", "POS"],
                weights=[30, 35, 10, 15, 10],
            )[0],
            "status": random.choices(
                ["COMPLETED", "PENDING", "FAILED", "REVERSED"],
                weights=[88, 5, 4, 3],
            )[0],
            "reference_number": f"REF{uuid.uuid4().hex[:12].upper()}",
        })
    return pd.DataFrame(rows)


def generate_policies(
    customers_df: pd.DataFrame,
    n: int = DATASET_CONFIG["policies"],
) -> pd.DataFrame:
    """Generate synthetic insurance policy records."""
    customer_ids = customers_df["customer_id"].tolist()
    rows = []
    for i in range(1, n + 1):
        policy_type = random.choice(POLICY_TYPES)
        start_date = random_date(2015)
        term_years = random.choice([5, 10, 15, 20, 25, 30])
        end_date = start_date + timedelta(days=term_years * 365)

        premium_cover = {
            "LIFE": (200, 5_000, 100, 500),
            "FUNERAL": (50, 500, None, None),
            "INVESTMENT": (500, 20_000, 10, 50),
            "RETIREMENT": (1_000, 30_000, 20, 100),
            "HEALTH": (800, 8_000, None, None),
            "SHORT_TERM": (100, 3_000, None, None),
        }
        p_lo, p_hi, c_lo, c_hi = premium_cover[policy_type]
        premium = round(random.uniform(p_lo, p_hi), 2)
        if c_lo is not None:
            cover = round(premium * random.uniform(c_lo, c_hi), 2)
        elif policy_type == "FUNERAL":
            cover = round(random.uniform(10_000, 100_000), 2)
        elif policy_type == "HEALTH":
            cover = round(random.uniform(100_000, 5_000_000), 2)
        else:
            cover = round(random.uniform(50_000, 2_000_000), 2)

        rows.append({
            "policy_id": f"POL{i:04d}",
            "customer_id": random.choice(customer_ids),
            "policy_type": policy_type,
            "status": random.choices(POLICY_STATUSES, weights=[60, 15, 10, 10, 5])[0],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "premium_amount": premium,
            "cover_amount": cover,
            "currency": "ZAR",
            "payment_frequency": random.choice(["MONTHLY", "QUARTERLY", "ANNUALLY"]),
            "beneficiary_count": random.randint(1, 5),
            "underwriting_status": random.choices(
                ["STANDARD", "SUBSTANDARD", "DECLINED", "PREFERRED"],
                weights=[60, 20, 5, 15],
            )[0],
        })
    return pd.DataFrame(rows)


def generate_claims(
    policies_df: pd.DataFrame,
    n: int = DATASET_CONFIG["claims"],
) -> pd.DataFrame:
    """Generate synthetic insurance claim records."""
    policy_ids = policies_df["policy_id"].tolist()
    pol_to_cust = dict(zip(policies_df["policy_id"], policies_df["customer_id"]))
    rows = []
    for i in range(1, n + 1):
        pol = random.choice(policy_ids)
        claim_date = random_date(2023)
        claim_amount = round(min(np.random.lognormal(10, 1.5), 5_000_000), 2)
        status = random.choices(CLAIM_STATUSES, weights=[10, 15, 30, 15, 25, 5])[0]
        approved_amount = (
            round(claim_amount * random.uniform(0.5, 1.0), 2)
            if status in ("APPROVED", "PAID") else None
        )
        rows.append({
            "claim_id": f"CLM{i:05d}",
            "policy_id": pol,
            "customer_id": pol_to_cust[pol],
            "claim_type": random.choice(CLAIM_TYPES),
            "claim_date": claim_date.strftime("%Y-%m-%d"),
            "claim_amount": claim_amount,
            "approved_amount": approved_amount,
            "currency": "ZAR",
            "status": status,
            "assessor_id": f"ASR{random.randint(100, 200)}",
            "resolution_date": (
                (claim_date + timedelta(days=random.randint(5, 90))).strftime("%Y-%m-%d")
                if status in ("APPROVED", "REJECTED", "PAID") else None
            ),
            "rejection_reason": (
                random.choice([
                    "Policy lapsed", "Exclusion clause",
                    "Insufficient documentation", "Waiting period",
                    "Pre-existing condition",
                ]) if status == "REJECTED" else None
            ),
        })
    return pd.DataFrame(rows)


def generate_payments(
    accounts_df: pd.DataFrame,
    policies_df: pd.DataFrame,
    n: int = DATASET_CONFIG["payments"],
) -> pd.DataFrame:
    """Generate synthetic payment records."""
    customer_ids = accounts_df["customer_id"].unique().tolist()
    account_ids = accounts_df["account_id"].tolist()
    policy_ids = policies_df["policy_id"].tolist()
    rows = []
    for i in range(1, n + 1):
        status = random.choices(PAYMENT_STATUSES, weights=[82, 8, 7, 3])[0]
        rows.append({
            "payment_id": f"PAY{i:06d}",
            "customer_id": random.choice(customer_ids),
            "account_id": random.choice(account_ids),
            "policy_id": random.choice(policy_ids) if random.random() < 0.6 else None,
            "amount": round(min(np.random.lognormal(7, 1.0), 500_000), 2),
            "currency": "ZAR",
            "payment_date": random_date(2024).strftime("%Y-%m-%d"),
            "payment_method": random.choice(PAYMENT_METHODS),
            "status": status,
            "reference": f"PAYREF{uuid.uuid4().hex[:10].upper()}",
            "failure_reason": (
                random.choice([
                    "Insufficient funds", "Account closed",
                    "Technical error", "Limit exceeded", "Invalid account",
                ]) if status == "FAILED" else None
            ),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════
# CORRUPTION INJECTOR
# ═══════════════════════════════════════════════════════════════

class CorruptionInjector:
    """Introduces realistic data-quality defects into clean DataFrames.

    Every method returns the corrupted DataFrame and appends to
    self.log so the caller can build a full corruption manifest.
    """

    def __init__(self, seed: int = SEED):
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.log: list[dict[str, Any]] = []

    def _sample_idx(self, df: pd.DataFrame, n: int):
        return df.sample(n=min(n, len(df)), random_state=self.np_rng).index

    # ── Individual corruption methods ────────────────────────

    def inject_duplicates(self, df: pd.DataFrame, n: int) -> pd.DataFrame:
        """Insert exact duplicate rows."""
        dupes = df.sample(n=min(n, len(df)), random_state=self.np_rng)
        result = pd.concat([df, dupes], ignore_index=True)
        self.log.append({
            "type": "DUPLICATE_ROWS",
            "count": len(dupes),
            "description": f"Injected {len(dupes)} exact duplicate rows",
        })
        return result

    def inject_nulls(self, df: pd.DataFrame, columns: list[str], frac: float = 0.03) -> pd.DataFrame:
        """Set random values to None in specified columns."""
        result = df.copy()
        total = 0
        for col in columns:
            idx = self._sample_idx(result, int(len(result) * frac))
            result.loc[idx, col] = None
            total += len(idx)
        self.log.append({
            "type": "MISSING_VALUES",
            "count": total,
            "columns": columns,
            "description": f"Injected {total} null values across {columns}",
        })
        return result

    def inject_negative_amounts(self, df: pd.DataFrame, col: str = "amount", n: int = 100) -> pd.DataFrame:
        """Flip amounts to negative (invalid for most financial contexts)."""
        result = df.copy()
        idx = self._sample_idx(result, n)
        result.loc[idx, col] = -abs(result.loc[idx, col])
        self.log.append({
            "type": "NEGATIVE_AMOUNTS",
            "count": len(idx),
            "description": f"Flipped {len(idx)} amounts to negative",
        })
        return result

    def inject_invalid_dates(self, df: pd.DataFrame, col: str, n: int = 100) -> pd.DataFrame:
        """Insert future dates and malformed date strings."""
        result = df.copy()
        idx = self._sample_idx(result, n)
        bad = []
        for _ in range(len(idx)):
            choice = self.rng.choice(["future", "malformed", "impossible"])
            if choice == "future":
                bad.append((TODAY + timedelta(days=self.rng.randint(30, 365))).strftime("%Y-%m-%d"))
            elif choice == "malformed":
                bad.append(self.rng.choice([
                    "2026-13-45", "not-a-date", "00/00/0000", "2026-02-30", "",
                ]))
            else:
                bad.append(self.rng.choice(["1899-01-01", "2099-12-31", "0001-01-01"]))
        result.loc[idx, col] = bad
        self.log.append({
            "type": "INVALID_DATES",
            "count": len(idx),
            "column": col,
            "description": f"Injected {len(idx)} invalid dates in {col}",
        })
        return result

    def inject_invalid_currencies(self, df: pd.DataFrame, col: str = "currency", n: int = 100) -> pd.DataFrame:
        """Replace valid currency codes with invalid ones."""
        result = df.copy()
        idx = self._sample_idx(result, n)
        bad = [self.rng.choice(["USD", "EUR", "GBP", "XXX", "ZZZ", "", None]) for _ in range(len(idx))]
        result.loc[idx, col] = bad
        self.log.append({
            "type": "INVALID_CURRENCY",
            "count": len(idx),
            "description": f"Replaced {len(idx)} currency values with invalid codes",
        })
        return result

    def inject_broken_foreign_keys(self, df: pd.DataFrame, fk_col: str, n: int = 100) -> pd.DataFrame:
        """Replace foreign keys with non-existent IDs."""
        result = df.copy()
        idx = self._sample_idx(result, n)
        fake = [f"FAKE_{uuid.uuid4().hex[:8].upper()}" for _ in range(len(idx))]
        result.loc[idx, fk_col] = fake
        self.log.append({
            "type": "BROKEN_FOREIGN_KEY",
            "count": len(idx),
            "column": fk_col,
            "description": f"Replaced {len(idx)} {fk_col} values with non-existent IDs",
        })
        return result

    def inject_abnormal_amounts(
        self, df: pd.DataFrame, col: str = "amount", n: int = 50, multiplier: int = 100,
    ) -> pd.DataFrame:
        """Create abnormally large transaction amounts (outliers)."""
        result = df.copy()
        idx = self._sample_idx(result, n)
        result.loc[idx, col] = result.loc[idx, col] * multiplier
        self.log.append({
            "type": "ABNORMAL_AMOUNTS",
            "count": len(idx),
            "description": f"Multiplied {len(idx)} amounts by {multiplier}x",
        })
        return result

    def inject_schema_violation(
        self, df: pd.DataFrame, add_col: str = "__unexpected_col", drop_col: str | None = None,
    ) -> pd.DataFrame:
        """Add unexpected column and/or drop expected column."""
        result = df.copy()
        result[add_col] = "unexpected_value"
        desc = f"Added unexpected column '{add_col}'"
        if drop_col and drop_col in result.columns:
            result = result.drop(columns=[drop_col])
            desc += f"; Dropped expected column '{drop_col}'"
        self.log.append({"type": "SCHEMA_VIOLATION", "description": desc})
        return result

    # ── Preset corruption profiles ───────────────────────────

    def corrupt_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply heavy corruption to transactions (demo centerpiece)."""
        result = self.inject_duplicates(df, n=500)
        result = self.inject_nulls(result, ["customer_id", "account_id"], frac=0.02)
        result = self.inject_negative_amounts(result, "amount", n=300)
        result = self.inject_invalid_dates(result, "transaction_date", n=400)
        result = self.inject_invalid_currencies(result, "currency", n=200)
        result = self.inject_broken_foreign_keys(result, "customer_id", n=350)
        result = self.inject_broken_foreign_keys(result, "account_id", n=250)
        result = self.inject_abnormal_amounts(result, "amount", n=150, multiplier=100)
        return result

    def corrupt_claims(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply moderate corruption to claims."""
        result = self.inject_duplicates(df, n=80)
        result = self.inject_nulls(result, ["policy_id", "claim_amount"], frac=0.04)
        result = self.inject_broken_foreign_keys(result, "policy_id", n=100)
        result = self.inject_negative_amounts(result, "claim_amount", n=50)
        result = self.inject_invalid_dates(result, "claim_date", n=60)
        return result

    def corrupt_payments(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply moderate corruption to payments."""
        result = self.inject_duplicates(df, n=120)
        result = self.inject_nulls(result, ["customer_id", "amount"], frac=0.025)
        result = self.inject_invalid_currencies(result, "currency", n=80)
        result = self.inject_abnormal_amounts(result, "amount", n=60, multiplier=50)
        return result

    def corrupt_customers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply light corruption to customers."""
        result = self.inject_nulls(df, ["email", "phone", "id_number"], frac=0.02)
        result = self.inject_duplicates(result, n=15)
        return result

    def corrupt_accounts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply light corruption to accounts."""
        result = self.inject_nulls(df, ["customer_id"], frac=0.015)
        result = self.inject_broken_foreign_keys(result, "customer_id", n=30)
        return result

    def corrupt_policies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply light corruption to policies."""
        result = self.inject_nulls(df, ["customer_id", "premium_amount"], frac=0.02)
        result = self.inject_negative_amounts(result, "premium_amount", n=20)
        return result


# ═══════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

def generate_all(seed: int = SEED) -> dict[str, pd.DataFrame]:
    """Generate all 6 clean datasets with proper FK relationships."""
    random.seed(seed)
    np.random.seed(seed)

    print("Generating clean datasets...")
    customers = generate_customers()
    print(f"  ✓ customers      {len(customers):>8,} rows × {len(customers.columns):>2} cols")

    accounts = generate_accounts(customers)
    print(f"  ✓ accounts       {len(accounts):>8,} rows × {len(accounts.columns):>2} cols")

    transactions = generate_transactions(accounts)
    print(f"  ✓ transactions   {len(transactions):>8,} rows × {len(transactions.columns):>2} cols")

    policies = generate_policies(customers)
    print(f"  ✓ policies       {len(policies):>8,} rows × {len(policies.columns):>2} cols")

    claims = generate_claims(policies)
    print(f"  ✓ claims         {len(claims):>8,} rows × {len(claims.columns):>2} cols")

    payments = generate_payments(accounts, policies)
    print(f"  ✓ payments       {len(payments):>8,} rows × {len(payments.columns):>2} cols")

    total = sum(len(df) for df in [customers, accounts, transactions, policies, claims, payments])
    print(f"\n  TOTAL: {total:,} clean records")

    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "policies": policies,
        "claims": claims,
        "payments": payments,
    }


def corrupt_all(
    clean: dict[str, pd.DataFrame], seed: int = SEED,
) -> tuple[dict[str, pd.DataFrame], list]:
    """Apply corruption profiles to all datasets."""
    injector = CorruptionInjector(seed=seed)

    print("\nInjecting corruptions...")
    corrupted = {
        "transactions": injector.corrupt_transactions(clean["transactions"]),
        "claims": injector.corrupt_claims(clean["claims"]),
        "payments": injector.corrupt_payments(clean["payments"]),
        "customers": injector.corrupt_customers(clean["customers"]),
        "accounts": injector.corrupt_accounts(clean["accounts"]),
        "policies": injector.corrupt_policies(clean["policies"]),
    }

    print(f"\n  Total corruption operations: {len(injector.log)}")
    for name in clean:
        delta = len(corrupted[name]) - len(clean[name])
        sign = f"+{delta}" if delta > 0 else str(delta)
        print(f"  {name:<15} {len(clean[name]):>8,} → {len(corrupted[name]):>8,}  ({sign} rows)")

    return corrupted, injector.log


def save_datasets(
    datasets: dict[str, pd.DataFrame],
    output_dir: str,
    fmt: str = "csv",
) -> None:
    """Save datasets to disk as CSV or Parquet."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    for name, df in datasets.items():
        filepath = path / f"{name}.{fmt}"
        if fmt == "csv":
            df.to_csv(filepath, index=False)
        elif fmt == "parquet":
            df.to_parquet(filepath, index=False)
        print(f"  Saved {filepath}  ({len(df):,} rows)")


def save_corruption_manifest(log: list, output_dir: str) -> None:
    """Save the corruption log as JSON for traceability."""
    path = Path(output_dir) / "corruption_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {"generated_at": TODAY.isoformat(), "corruptions": log},
            f, indent=2, default=str,
        )
    print(f"  Saved {path}")


# ═══════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="DataTrust Synthetic Data Generator")
    parser.add_argument("--output-dir", default="data", help="Root output directory")
    parser.add_argument("--clean-only", action="store_true", help="Generate clean data only")
    parser.add_argument("--format", choices=["csv", "parquet"], default="csv", help="Output format")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed for reproducibility")
    args = parser.parse_args()

    print("=" * 60)
    print("DataTrust — Synthetic Financial Data Generator")
    print("=" * 60)

    clean = generate_all(seed=args.seed)

    print(f"\nSaving clean data to {args.output_dir}/clean/")
    save_datasets(clean, f"{args.output_dir}/clean", fmt=args.format)

    if not args.clean_only:
        corrupted, corruption_log = corrupt_all(clean, seed=args.seed)
        print(f"\nSaving corrupted data to {args.output_dir}/corrupted/")
        save_datasets(corrupted, f"{args.output_dir}/corrupted", fmt=args.format)
        save_corruption_manifest(corruption_log, f"{args.output_dir}/corrupted")

    print("\n" + "=" * 60)
    print("DONE ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
