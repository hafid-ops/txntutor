#!/usr/bin/env python3
"""
Test anomaly detection with a real simulator run
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import TransactionSimulator
from src.detector import detect_anomalies
from src.db_operations import (
    get_or_create_scenario,
    create_run,
    complete_run,
    get_trace_events,
    insert_anomaly
)

def test_anomaly_detection():
    """Test anomaly detector with lost update simulator"""
    print("=" * 60)
    print("Testing Anomaly Detection - Lost Update")
    print("=" * 60)
    
    # Create scenario and run
    scenario_id = get_or_create_scenario(
        name='test_anomaly_detection',
        description='Test anomaly detection',
        isolation_level='READ COMMITTED'
    )
    
    run_id = create_run(scenario_id)
    print(f"\n✓ Created run_id: {run_id}")
    
    # Run lost update simulator
    print("\n📊 Running Lost Update simulator...")
    simulator = TransactionSimulator(run_id)
    results = simulator.run_simulator('lost_update', t1_amount=50, t2_amount=-20)
    
    print(f"\n✓ Simulation complete!")
    print(f"  T1 final: {results['t1_final']}")
    print(f"  T2 final: {results['t2_final']}")
    print(f"  Actual:   {results['actual_final']}")
    
    # Get trace events
    print("\n📝 Retrieving trace events...")
    trace_events = get_trace_events(run_id)
    print(f"✓ Retrieved {len(trace_events)} trace events")
    
    # Detect anomalies
    print("\n🔍 Running anomaly detection...")
    anomalies = detect_anomalies(trace_events)
    
    if anomalies:
        print(f"\n⚠️  Detected {len(anomalies)} anomaly(ies):\n")
        
        for i, anomaly in enumerate(anomalies, 1):
            print(f"{i}. {anomaly['type'].upper()}")
            print(f"   Severity: {anomaly['severity']}")
            print(f"   Affected: {', '.join(anomaly['affected_transactions'])}")
            print(f"   Description:")
            print(f"   {anomaly['description']}\n")
            
            # Insert into database
            anomaly_id = insert_anomaly(
                run_id=run_id,
                anomaly_type=anomaly['type'],
                description=anomaly['description'],
                severity=anomaly['severity'],
                affected_transactions=anomaly['affected_transactions'],
                event_sequence=anomaly['event_sequence']
            )
            print(f"   ✓ Inserted to database as anomaly_id: {anomaly_id}")
    else:
        print("\n✓ No anomalies detected")
    
    # Complete run
    complete_run(run_id, 'completed')
    
    print("\n" + "=" * 60)
    print("✓ Test complete!")
    print("=" * 60)
    
    return run_id, anomalies

if __name__ == '__main__':
    try:
        run_id, anomalies = test_anomaly_detection()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
