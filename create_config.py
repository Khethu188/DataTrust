
#!/usr/bin/env python3
"""Run this to create config.yaml in the project root."""

config_text = """project:
  name: DataTrust
  version: 1.0.0
  author: Khethukuthula Sabela

paths:
  clean_data: data/clean
  corrupted_data: data/corrupted
  recovered_data: data/recovered
  quarantine_data: data/quarantine
  reports: data/reports
  dashboard: data/dashboard/index.html
  contracts: src/contracts
  logs: logs

generation:
  customers: 10000
  accounts: 15000
  transactions: 25000
  policies: 8000
  claims: 4500
  payments: 2800
  corruption_rate: 0.05

validation:
  trust_score_weights:
    pass: 1.0
    warn: 0.5
    fail: 0.0

anomaly_detection:
  z_score_threshold: 3.5
  iqr_multiplier: 2.5
  isolation_forest:
    contamination: 0.05
    n_estimators: 100
    random_state: 42
  severity_thresholds:
    critical_rate: 0.05
    high_rate: 0.02
    medium_rate: 0.01

recovery:
  outlier_cap_iqr_multiplier: 3.0
  default_currency: ZAR
  recovery_order:
    - customers
    - accounts
    - policies
    - transactions
    - claims
    - payments

database:
  host: localhost
  port: 5432
  name: datatrust
  user: datatrust_user
  password: datatrust_pass
"""

with open("config.yaml", "w", encoding="utf-8") as f:
    f.write(config_text.strip() + "\n")

print("config.yaml created successfully!")

