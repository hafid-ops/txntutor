#!/usr/bin/env python3
"""
Test script for Transaction Simulator
"""
import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import TransactionSimulator
from src.db_operations import (
    get_or_create_scenario,
    create_run,
    complete_run,
    get_trace_events
)
from config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')

def test_lost_update():
    """Test Lost Update simulator"""
    print("=" * 60)
    print("Testing Lost Update Simulator")
    print("=" * 60)
    
    # Create scenario and run
    scenario_id = get_or_create_scenario(
        name='test_lost_update',
        description='Test lost update pattern',
        isolation_level='READ COMMITTED'
    )
    
    run_id = create_run(scenario_id, notes='Test run for lost update')
    print(f"\n✓ Created run_id: {run_id}")
    
    # Run simulator
    simulator = TransactionSimulator(run_id)
    print("\n📊 Executing T1 and T2 concurrently...")
    
    results = simulator.run_simulator('lost_update', t1_amount=50, t2_amount=-20)
    
    print(f"\n✓ Simulation complete!")
    print(f"  T1 calculated final: {results['t1_final']} (100 + 50 = 150)")
    print(f"  T2 calculated final: {results['t2_final']} (100 - 20 = 80)")
    print(f"  Actual final value:  {results['actual_final']}")
    
    if results['actual_final'] == results['t2_final']:
        print(f"\n⚠️  ANOMALY DETECTED: T1's update was lost!")
        print(f"  Expected: {results['t1_final']} (if both updates applied: {100 + 50 - 20})")
        print(f"  Got:      {results['actual_final']}")
    
    # Complete run
    complete_run(run_id, 'completed')
    
    # Show trace events
    print("\n📝 Trace Events:")
    print("-" * 60)
    events = get_trace_events(run_id)
    for event in events:
        tx_name = event['tx_name']
        event_type = event['event_type']
        table = event.get('table_name', '')
        key = event.get('record_key', '')
        old_val = event.get('old_value', '')
        new_val = event.get('new_value', '')
        
        if event_type == 'BEGIN':
            print(f"{event['sequence_order']:2d}. {tx_name}: BEGIN")
        elif event_type == 'READ':
            print(f"{event['sequence_order']:2d}. {tx_name}: READ {table}[{key}] = {old_val}")
        elif event_type == 'WRITE':
            print(f"{event['sequence_order']:2d}. {tx_name}: WRITE {table}[{key}] = {new_val} (was {old_val})")
        elif event_type == 'COMMIT':
            print(f"{event['sequence_order']:2d}. {tx_name}: COMMIT")
        elif event_type == 'ROLLBACK':
            print(f"{event['sequence_order']:2d}. {tx_name}: ROLLBACK")
    
    print("\n✓ Lost Update test complete!")
    return run_id

def test_deadlock():
    """Test Deadlock simulator"""
    print("\n" + "=" * 60)
    print("Testing Deadlock Simulator")
    print("=" * 60)
    
    scenario_id = get_or_create_scenario(
        name='test_deadlock',
        description='Test deadlock pattern',
        isolation_level='READ COMMITTED'
    )
    
    run_id = create_run(scenario_id, notes='Test run for deadlock')
    print(f"\n✓ Created run_id: {run_id}")
    
    simulator = TransactionSimulator(run_id)
    print("\n📊 Executing T1 and T2 with conflicting locks...")
    
    results = simulator.run_simulator('deadlock', t1_amount=10, t2_amount=20)
    
    print(f"\n✓ Simulation complete!")
    print(f"  Deadlock occurred: {results['deadlock_occurred']}")
    print(f"  Deadlock victim:   {results.get('deadlock_victim', 'None')}")
    
    complete_run(run_id, 'completed')
    
    print("\n✓ Deadlock test complete!")
    return run_id

def main():
    print("\n🔬 TxnTutor Transaction Simulator Test\n")
    
    try:
        # Test 1: Lost Update
        run_id1 = test_lost_update()
        
        # Test 2: Deadlock
        run_id2 = test_deadlock()
        
        print("\n" + "=" * 60)
        print("✓ All simulator tests passed!")
        print(f"  Run IDs created: {run_id1}, {run_id2}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
