# Database operations for TxnTutor entities
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from src.database import (
    get_db_cursor,
    execute_query,
    execute_insert,
    execute_update
)

# ==================== SCENARIO ====================

def get_or_create_scenario(name: str, description: str = None, isolation_level: str = 'READ COMMITTED') -> int:
    """
    Get existing scenario by name or create new one
    
    Returns:
        scenario_id
    """
    # Check if scenario exists
    query = "SELECT scenario_id FROM scenario WHERE name = %s"
    with get_db_cursor() as cursor:
        cursor.execute(query, (name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
    
    # Create new scenario
    query = """
        INSERT INTO scenario (name, description, isolation_level)
        VALUES (%s, %s, %s)
        RETURNING scenario_id
    """
    return execute_insert(query, (name, description, isolation_level))

def get_all_scenarios() -> List[Dict]:
    """Get all scenarios"""
    query = "SELECT scenario_id, name, description, isolation_level FROM scenario ORDER BY name"
    results = execute_query(query)
    return [
        {
            'scenario_id': r[0],
            'name': r[1],
            'description': r[2],
            'isolation_level': r[3]
        }
        for r in results
    ]

# ==================== RUN ====================

def create_run(scenario_id: int, notes: str = None) -> int:
    """
    Create a new run for a scenario
    
    Returns:
        run_id
    """
    query = """
        INSERT INTO run (scenario_id, started_at, status, notes)
        VALUES (%s, %s, 'running', %s)
        RETURNING run_id
    """
    return execute_insert(query, (scenario_id, datetime.now(), notes))

def complete_run(run_id: int, status: str = 'completed'):
    """Mark a run as completed"""
    query = """
        UPDATE run
        SET status = %s,
            completed_at = %s,
            duration_ms = EXTRACT(EPOCH FROM (%s - started_at)) * 1000
        WHERE run_id = %s
    """
    now = datetime.now()
    execute_update(query, (status, now, now, run_id))

def get_run_details(run_id: int) -> Optional[Dict]:
    """Get run details with scenario info"""
    query = """
        SELECT r.run_id, r.started_at, r.completed_at, r.status, r.duration_ms,
               s.name, s.description, s.isolation_level
        FROM run r
        JOIN scenario s ON r.scenario_id = s.scenario_id
        WHERE r.run_id = %s
    """
    results = execute_query(query, (run_id,))
    if not results:
        return None
    
    r = results[0]
    return {
        'run_id': r[0],
        'started_at': r[1],
        'completed_at': r[2],
        'status': r[3],
        'duration_ms': r[4],
        'scenario_name': r[5],
        'scenario_description': r[6],
        'isolation_level': r[7]
    }

def get_recent_runs(limit: int = 10) -> List[Dict]:
    """Get recent runs with scenario info"""
    query = """
        SELECT r.run_id, r.started_at, r.status, r.duration_ms, s.name
        FROM run r
        JOIN scenario s ON r.scenario_id = s.scenario_id
        ORDER BY r.started_at DESC
        LIMIT %s
    """
    results = execute_query(query, (limit,))
    return [
        {
            'run_id': r[0],
            'started_at': r[1],
            'status': r[2],
            'duration_ms': r[3],
            'scenario_name': r[4]
        }
        for r in results
    ]

# ==================== TRANSACTION ====================

def create_transaction(run_id: int, tx_name: str, isolation_level: str = None) -> int:
    """
    Create a transaction record
    
    Returns:
        tx_id
    """
    query = """
        INSERT INTO tx (run_id, tx_name, isolation_level, started_at, status)
        VALUES (%s, %s, %s, %s, 'started')
        RETURNING tx_id
    """
    return execute_insert(query, (run_id, tx_name, isolation_level, datetime.now()))

def update_transaction_status(tx_id: int, status: str, committed_at: datetime = None, rolled_back: bool = False):
    """Update transaction status"""
    query = """
        UPDATE tx
        SET status = %s, committed_at = %s, rolled_back = %s
        WHERE tx_id = %s
    """
    execute_update(query, (status, committed_at, rolled_back, tx_id))

# ==================== TRACE EVENT ====================

def log_trace_event(
    run_id: int,
    tx_id: int,
    event_type: str,
    sequence_order: int,
    table_name: str = None,
    record_key: str = None,
    old_value: Any = None,
    new_value: Any = None,
    notes: str = None
) -> int:
    """
    Log a trace event
    
    Args:
        event_type: BEGIN, READ, WRITE, COMMIT, ROLLBACK
        sequence_order: Global ordering across all transactions
    
    Returns:
        event_id
    """
    query = """
        INSERT INTO trace_event 
        (run_id, tx_id, event_type, table_name, record_key, old_value, new_value, 
         timestamp, sequence_order, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING event_id
    """
    return execute_insert(query, (
        run_id, tx_id, event_type, table_name, record_key,
        str(old_value) if old_value is not None else None,
        str(new_value) if new_value is not None else None,
        datetime.now(), sequence_order, notes
    ))

def get_trace_events(run_id: int) -> List[Dict]:
    """Get all trace events for a run, ordered by sequence"""
    query = """
        SELECT te.event_id, te.tx_id, t.tx_name, te.event_type, te.table_name,
               te.record_key, te.old_value, te.new_value, te.timestamp, 
               te.sequence_order, te.notes
        FROM trace_event te
        JOIN tx t ON te.tx_id = t.tx_id
        WHERE te.run_id = %s
        ORDER BY te.sequence_order
    """
    results = execute_query(query, (run_id,))
    return [
        {
            'event_id': r[0],
            'tx_id': r[1],
            'tx_name': r[2],
            'event_type': r[3],
            'table_name': r[4],
            'record_key': r[5],
            'old_value': r[6],
            'new_value': r[7],
            'timestamp': r[8],
            'sequence_order': r[9],
            'notes': r[10]
        }
        for r in results
    ]

# ==================== ANOMALY ====================

def insert_anomaly(
    run_id: int,
    anomaly_type: str,
    description: str,
    severity: str = 'medium',
    affected_transactions: List[str] = None,
    event_sequence: List[int] = None
) -> int:
    """
    Insert an anomaly record
    
    Returns:
        anomaly_id
    """
    query = """
        INSERT INTO anomaly 
        (run_id, anomaly_type, severity, description, affected_transactions, event_sequence)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING anomaly_id
    """
    return execute_insert(query, (
        run_id,
        anomaly_type,
        severity,
        description,
        json.dumps(affected_transactions) if affected_transactions else None,
        json.dumps(event_sequence) if event_sequence else None
    ))

def get_anomalies(run_id: int) -> List[Dict]:
    """Get all anomalies for a run"""
    query = """
        SELECT anomaly_id, anomaly_type, severity, description, 
               affected_transactions, event_sequence, detected_at
        FROM anomaly
        WHERE run_id = %s
        ORDER BY detected_at
    """
    results = execute_query(query, (run_id,))
    return [
        {
            'anomaly_id': r[0],
            'anomaly_type': r[1],
            'severity': r[2],
            'description': r[3],
            'affected_transactions': json.loads(r[4]) if r[4] else [],
            'event_sequence': json.loads(r[5]) if r[5] else [],
            'detected_at': r[6]
        }
        for r in results
    ]

# ==================== EXPLANATION ====================

def insert_explanation(
    anomaly_id: int,
    llm_model: str,
    explanation_text: str,
    prompt_text: str = None,
    tokens_used: int = None,
    generation_time_ms: int = None
) -> int:
    """
    Insert an LLM-generated explanation
    
    Returns:
        explanation_id
    """
    query = """
        INSERT INTO explanation 
        (anomaly_id, llm_model, prompt_text, explanation_text, 
         tokens_used, generation_time_ms, generated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING explanation_id
    """
    return execute_insert(query, (
        anomaly_id,
        llm_model,
        prompt_text,
        explanation_text,
        tokens_used,
        generation_time_ms,
        datetime.now()
    ))

def get_explanations(anomaly_id: int) -> List[Dict]:
    """Get all explanations for an anomaly"""
    query = """
        SELECT explanation_id, llm_model, explanation_text, 
               tokens_used, generation_time_ms, generated_at
        FROM explanation
        WHERE anomaly_id = %s
        ORDER BY generated_at DESC
    """
    results = execute_query(query, (anomaly_id,))
    return [
        {
            'explanation_id': r[0],
            'llm_model': r[1],
            'explanation_text': r[2],
            'tokens_used': r[3],
            'generation_time_ms': r[4],
            'generated_at': r[5]
        }
        for r in results
    ]
