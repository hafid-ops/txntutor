-- PostgreSQL Database Schema for TxnTutor
-- Transaction Lab: Simulates concurrent transactions, traces execution, detects anomalies

-- Drop existing tables if they exist
DROP TABLE IF EXISTS explanation CASCADE;
DROP TABLE IF EXISTS anomaly CASCADE;
DROP TABLE IF EXISTS trace_event CASCADE;
DROP TABLE IF EXISTS tx CASCADE;
DROP TABLE IF EXISTS run CASCADE;
DROP TABLE IF EXISTS scenario CASCADE;

-- SCENARIO: Defines different transaction test scenarios
CREATE TABLE scenario (
    scenario_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    isolation_level VARCHAR(50) DEFAULT 'READ COMMITTED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- RUN: Records each execution of a scenario
CREATE TABLE run (
    run_id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES scenario(scenario_id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed
    duration_ms INTEGER,
    notes TEXT
);

-- TX: Tracks individual transactions within a run
CREATE TABLE tx (
    tx_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run(run_id) ON DELETE CASCADE,
    tx_name VARCHAR(10) NOT NULL, -- T1, T2, etc.
    isolation_level VARCHAR(50),
    started_at TIMESTAMP,
    committed_at TIMESTAMP,
    rolled_back BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) -- started, committed, rolled_back, aborted
);

-- TRACE_EVENT: Logs every database operation (read, write, commit)
CREATE TABLE trace_event (
    event_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run(run_id) ON DELETE CASCADE,
    tx_id INTEGER REFERENCES tx(tx_id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL, -- BEGIN, READ, WRITE, COMMIT, ROLLBACK
    table_name VARCHAR(100),
    record_key VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sequence_order INTEGER, -- Global ordering of events across transactions
    notes TEXT
);

-- ANOMALY: Stores detected concurrency anomalies
CREATE TABLE anomaly (
    anomaly_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run(run_id) ON DELETE CASCADE,
    anomaly_type VARCHAR(50) NOT NULL, -- dirty_read, non_repeatable_read, phantom_read, lost_update, write_skew, deadlock
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    affected_transactions TEXT, -- JSON array of tx_ids or names
    event_sequence TEXT -- JSON array of event_ids involved
);

-- EXPLANATION: Stores LLM-generated explanations of anomalies
CREATE TABLE explanation (
    explanation_id SERIAL PRIMARY KEY,
    anomaly_id INTEGER NOT NULL REFERENCES anomaly(anomaly_id) ON DELETE CASCADE,
    llm_model VARCHAR(100), -- e.g., "gemini-pro" or "gpt-4"
    prompt_text TEXT,
    explanation_text TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER,
    generation_time_ms INTEGER
);

-- Create indexes for better query performance
CREATE INDEX idx_run_scenario ON run(scenario_id);
CREATE INDEX idx_run_started_at ON run(started_at);
CREATE INDEX idx_tx_run ON tx(run_id);
CREATE INDEX idx_trace_event_run ON trace_event(run_id);
CREATE INDEX idx_trace_event_tx ON trace_event(tx_id);
CREATE INDEX idx_trace_event_sequence ON trace_event(sequence_order);
CREATE INDEX idx_anomaly_run ON anomaly(run_id);
CREATE INDEX idx_explanation_anomaly ON explanation(anomaly_id);

-- Insert some default scenarios
INSERT INTO scenario (name, description, isolation_level) VALUES
    ('Lost Update', 'Two transactions read and update the same record, causing one update to be lost', 'READ COMMITTED'),
    ('Dirty Read', 'Transaction reads uncommitted data from another transaction', 'READ UNCOMMITTED'),
    ('Non-Repeatable Read', 'Transaction reads the same record twice and gets different values', 'READ COMMITTED'),
    ('Phantom Read', 'Transaction re-executes a query and sees different rows', 'READ COMMITTED'),
    ('Write Skew', 'Two transactions read overlapping data and make disjoint updates', 'REPEATABLE READ'),
    ('Deadlock', 'Two transactions wait for each other to release locks', 'READ COMMITTED');
