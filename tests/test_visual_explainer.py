"""Test the visual explainer"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.report.visual_explainer import create_problem_solution_card, create_anomaly_diagram

# Test problem/solution card
print("Testing problem/solution card...")
card = create_problem_solution_card('dirty_read')
print("✓ Card generated")
print(card[:200] + "...")

# Test anomaly diagram
print("\nTesting anomaly diagram...")
sample_events = [
    {'tx_name': 'T1', 'event_type': 'BEGIN'},
    {'tx_name': 'T1', 'event_type': 'READ', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100'},
    {'tx_name': 'T2', 'event_type': 'BEGIN'},
    {'tx_name': 'T2', 'event_type': 'READ', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100'},
    {'tx_name': 'T1', 'event_type': 'WRITE', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100', 'new_value': '150'},
    {'tx_name': 'T1', 'event_type': 'COMMIT'},
    {'tx_name': 'T2', 'event_type': 'WRITE', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100', 'new_value': '80'},
    {'tx_name': 'T2', 'event_type': 'COMMIT'},
]

fig = create_anomaly_diagram(sample_events, 'lost_update')
print(f"✓ Figure generated with {len(fig.data)} traces")

print("\n✅ All visual explainer tests passed!")
