#!/usr/bin/env python3
"""
Test timeline visualization
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import TransactionSimulator
from src.detector import detect_anomalies
from src.report import (
    create_timeline_figure,
    create_event_table,
    create_anomaly_summary,
    create_statistics_summary,
    format_statistics
)
from src.db_operations import (
    get_or_create_scenario,
    create_run,
    complete_run,
    get_trace_events
)

def test_timeline_visualization():
    """Test timeline view with a complete simulation"""
    print("=" * 60)
    print("Testing Timeline Visualization - Lost Update")
    print("=" * 60)
    
    # Create scenario and run
    scenario_id = get_or_create_scenario(
        name='test_timeline_viz',
        description='Test timeline visualization',
        isolation_level='READ COMMITTED'
    )
    
    run_id = create_run(scenario_id)
    print(f"\n✓ Created run_id: {run_id}")
    
    # Run simulator
    print("\n📊 Running Lost Update simulator...")
    simulator = TransactionSimulator(run_id)
    results = simulator.run_simulator('lost_update', t1_amount=50, t2_amount=-20)
    
    print(f"✓ Simulation complete!")
    print(f"  T1 final: {results['t1_final']}")
    print(f"  T2 final: {results['t2_final']}")
    print(f"  Actual:   {results['actual_final']}")
    
    # Get trace events
    print("\n📝 Retrieving trace events...")
    trace_events = get_trace_events(run_id)
    print(f"✓ Retrieved {len(trace_events)} trace events")
    
    # Detect anomalies
    print("\n🔍 Detecting anomalies...")
    anomalies = detect_anomalies(trace_events)
    print(f"✓ Detected {len(anomalies)} anomaly(ies)")
    
    # Create timeline figure
    print("\n📈 Creating timeline visualization...")
    fig = create_timeline_figure(trace_events, anomalies)
    print(f"✓ Timeline figure created with {len(fig.data)} traces")
    
    # Create event table
    print("\n📋 Creating event table...")
    df = create_event_table(trace_events)
    print(f"✓ Event table created with {len(df)} rows")
    print("\nEvent Table Preview:")
    print(df.to_string(index=False))
    
    # Create anomaly summary
    print("\n⚠️  Anomaly Summary:")
    summary = create_anomaly_summary(anomalies)
    print(summary)
    
    # Create statistics
    print("\n📊 Statistics:")
    stats = create_statistics_summary(trace_events, anomalies)
    stats_md = format_statistics(stats)
    print(stats_md)
    
    # Save figure as HTML
    output_file = "timeline_test.html"
    fig.write_html(output_file)
    print(f"\n✓ Timeline saved to: {output_file}")
    print("  Open this file in a browser to view the interactive timeline!")
    
    # Complete run
    complete_run(run_id, 'completed')
    
    print("\n" + "=" * 60)
    print("✓ Timeline visualization test complete!")
    print("=" * 60)
    
    return run_id

if __name__ == '__main__':
    try:
        run_id = test_timeline_visualization()
        print(f"\nRun ID: {run_id}")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
