
-- ═══════════════════════════════════════════════════════════════
-- DataTrust — Database Initialization
-- ═══════════════════════════════════════════════════════════════
-- Runs automatically when PostgreSQL container starts

-- Create application user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'datatrust_user') THEN
        CREATE ROLE datatrust_user WITH LOGIN PASSWORD 'datatrust_pass';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE datatrust TO datatrust_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO datatrust_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO datatrust_user;

-- Create tables
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    id_number VARCHAR(13),
    province VARCHAR(30),
    city VARCHAR(50),
    registration_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    account_type VARCHAR(30),
    balance NUMERIC(15, 2),
    currency VARCHAR(3) DEFAULT 'ZAR',
    opened_date DATE,
    status VARCHAR(20),
    branch_code VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    account_id VARCHAR(20) REFERENCES accounts(account_id),
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    transaction_date TIMESTAMP,
    amount NUMERIC(15, 2),
    currency VARCHAR(3) DEFAULT 'ZAR',
    transaction_type VARCHAR(30),
    status VARCHAR(20),
    description TEXT
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    policy_type VARCHAR(30),
    premium_amount NUMERIC(15, 2),
    coverage_amount NUMERIC(15, 2),
    start_date DATE,
    end_date DATE,
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id VARCHAR(20) PRIMARY KEY,
    policy_id VARCHAR(20) REFERENCES policies(policy_id),
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    claim_date DATE,
    claim_amount NUMERIC(15, 2),
    status VARCHAR(20),
    claim_type VARCHAR(30),
    description TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(20) PRIMARY KEY,
    policy_id VARCHAR(20) REFERENCES policies(policy_id),
    customer_id VARCHAR(20) REFERENCES customers(customer_id),
    payment_date DATE,
    amount NUMERIC(15, 2),
    currency VARCHAR(3) DEFAULT 'ZAR',
    payment_method VARCHAR(30),
    status VARCHAR(20)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_policies_customer ON policies(customer_id);
CREATE INDEX IF NOT EXISTS idx_claims_policy ON claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_customer ON claims(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_policy ON payments(policy_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);

-- Pipeline run tracking
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    triggered_by VARCHAR(50),
    stages_completed TEXT[],
    trust_scores JSONB,
    anomalies_found INTEGER,
    rows_recovered INTEGER,
    rows_quarantined INTEGER,
    duration_seconds NUMERIC(10, 2)
);

-- Trust score history (for trend tracking)
CREATE TABLE IF NOT EXISTS trust_score_history (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP DEFAULT NOW(),
    dataset_name VARCHAR(50),
    trust_score NUMERIC(5, 2),
    health_score NUMERIC(5, 2),
    anomaly_count INTEGER,
    recovery_rate NUMERIC(5, 2),
    verdict VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_trust_history_dataset ON trust_score_history(dataset_name);
CREATE INDEX IF NOT EXISTS idx_trust_history_date ON trust_score_history(recorded_at);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO datatrust_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO datatrust_user;

-- Done
DO $$ BEGIN RAISE NOTICE 'DataTrust database initialized successfully!'; END $$;

