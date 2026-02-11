#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for LLM Service (Ollama integration)
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import get_llm_service
from config import config

def test_ollama_connection():
    """Test if Ollama is running and model is available"""
    print("=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    
    llm = get_llm_service()
    
    print(f"\nProvider: {llm.provider}")
    print(f"Model: {llm.model}")
    print(f"Base URL: {llm.ollama_base_url}")
    
    success, message = llm.test_connection()
    
    if success:
        print(f"\n✓ {message}")
        return True
    else:
        print(f"\n✗ {message}")
        print("\nTo fix this:")
        print("1. Install Ollama: https://ollama.ai/")
        print(f"2. Run: ollama pull {llm.model}")
        print("3. Make sure Ollama is running")
        return False

def test_ollama_generation():
    """Test LLM explanation generation with a sample anomaly"""
    print("\n" + "=" * 60)
    print("Testing LLM Explanation Generation")
    print("=" * 60)
    
    llm = get_llm_service()
    
    # Sample trace events for a lost update scenario
    sample_trace = [
        {'tx_name': 'T1', 'event_type': 'BEGIN'},
        {'tx_name': 'T2', 'event_type': 'BEGIN'},
        {'tx_name': 'T1', 'event_type': 'READ', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100'},
        {'tx_name': 'T2', 'event_type': 'READ', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100'},
        {'tx_name': 'T1', 'event_type': 'WRITE', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100', 'new_value': '150'},
        {'tx_name': 'T1', 'event_type': 'COMMIT'},
        {'tx_name': 'T2', 'event_type': 'WRITE', 'table_name': 'accounts', 'record_key': 'A', 'old_value': '100', 'new_value': '80'},
        {'tx_name': 'T2', 'event_type': 'COMMIT'},
    ]
    
    print("\nSample Scenario: Lost Update")
    print("- T1 reads balance (100), adds 50, commits (150)")
    print("- T2 reads balance (100), subtracts 20, commits (80)")
    print("- Final value: 80 (T1's update is lost!)")
    
    print("\nGenerating explanation...")
    
    result = llm.generate_explanation(
        anomaly_type='lost_update',
        trace_events=sample_trace,
        anomaly_description='T1 updated account A, but T2 overwrote it with a value based on the old balance.',
        context={'isolation_level': 'READ COMMITTED'}
    )
    
    print(f"\n{'─' * 60}")
    print("EXPLANATION:")
    print(f"{'─' * 60}")
    print(result['explanation'])
    print(f"{'─' * 60}")
    print(f"\nModel: {result['model']}")
    print(f"Tokens: {result['tokens_used']}")
    print(f"Time: {result['generation_time_ms']}ms")
    
    return True

def main():
    print("\n🔬 TxnTutor LLM Service Test\n")
    
    # Test 1: Connection
    if not test_ollama_connection():
        print("\n⚠️  Cannot proceed without Ollama connection")
        return 1
    
    # Test 2: Generation
    try:
        test_ollama_generation()
        print("\n✓ All tests passed!")
        return 0
    except Exception as e:
        print(f"\n✗ Generation test failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
