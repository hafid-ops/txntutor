"""Check what's in the database"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # Check scenarios
        cur.execute('SELECT COUNT(*) FROM scenario')
        print(f"✓ Scenarios: {cur.fetchone()[0]}")
        
        # Check runs
        cur.execute('SELECT COUNT(*) FROM run')
        print(f"✓ Runs: {cur.fetchone()[0]}")
        
        # Check trace events
        cur.execute('SELECT COUNT(*) FROM trace_event')
        print(f"✓ Trace Events: {cur.fetchone()[0]}")
        
        # Check anomalies
        cur.execute('SELECT COUNT(*) FROM anomaly')
        print(f"✓ Anomalies: {cur.fetchone()[0]}")
        
        # Check explanations
        cur.execute('SELECT COUNT(*) FROM explanation')
        print(f"✓ Explanations: {cur.fetchone()[0]}")
        
        print("\n" + "="*50)
        
        # Show recent runs
        cur.execute("""
            SELECT run_id, scenario_id, status, started_at 
            FROM run 
            ORDER BY started_at DESC 
            LIMIT 3
        """)
        
        runs = cur.fetchall()
        if runs:
            print("\nRecent Runs:")
            for run in runs:
                print(f"  Run {run[0]}: Scenario {run[1]}, Status: {run[2]}, Started: {run[3]}")
        else:
            print("\n⚠️  No runs found yet. Run a simulation from Streamlit first!")
