#!/usr/bin/env python3
"""
Test Gemini API connection with the configured API key
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force reload of config to pick up new .env values
import importlib
import config as config_module
importlib.reload(config_module)
from config import config

from src.llm import get_llm_service

def test_gemini_connection():
    """Test Gemini API connection"""
    print("=" * 60)
    print("Testing Gemini API Connection")
    print("=" * 60)
    
    print(f"\nProvider: {config.LLM_PROVIDER}")
    print(f"Model: {config.LLM_MODEL}")
    print(f"API Key: {config.LLM_API_KEY[:20]}...{config.LLM_API_KEY[-4:]}")
    
    # Test connection
    print("\n🔍 Testing connection...")
    llm = get_llm_service()
    success, message = llm.test_connection()
    
    if success:
        print(f"\n✅ {message}")
    else:
        print(f"\n❌ {message}")
        return False
    
    # Test a simple explanation generation
    print("\n🤖 Testing explanation generation...")
    
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
    
    result = llm.generate_explanation(
        anomaly_type='lost_update',
        trace_events=sample_trace,
        anomaly_description='T1 updated account A, but T2 overwrote it.',
        context={'isolation_level': 'READ COMMITTED'}
    )
    
    if result['explanation'] and not result['explanation'].startswith('Failed'):
        print("\n✅ Explanation generated successfully!")
        print(f"\nModel: {result['model']}")
        print(f"Tokens: {result.get('tokens_used', 'N/A')}")
        print(f"Time: {result['generation_time_ms']}ms")
        print(f"\n{'─' * 60}")
        print("EXPLANATION PREVIEW:")
        print(f"{'─' * 60}")
        # Show first 500 characters
        preview = result['explanation'][:500]
        print(preview)
        if len(result['explanation']) > 500:
            print("...")
        print(f"{'─' * 60}")
        return True
    else:
        print(f"\n❌ Failed to generate explanation: {result['explanation']}")
        return False

if __name__ == '__main__':
    try:
        success = test_gemini_connection()
        if success:
            print("\n✅ Gemini is ready to use!")
            print("\n💡 Restart Streamlit to use the new configuration:")
            print("   streamlit run app.py")
            sys.exit(0)
        else:
            print("\n❌ Gemini connection failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
