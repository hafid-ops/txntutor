#!/usr/bin/env python3
"""
Quick test of UI controller components (without actually running Streamlit)
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.controller import show_connection_status, show_simulator_config
from config import config

def test_ui_components():
    """Test that UI controller components are importable and configured"""
    print("=" * 60)
    print("Testing UI Controller Components")
    print("=" * 60)
    
    print("\n✓ UI controller imported successfully")
    print(f"✓ App title: {config.APP_TITLE}")
    print(f"✓ App icon: {config.PAGE_ICON}")
    
    print("\n✓ Available simulators:")
    for key, desc in config.SIMULATORS.items():
        print(f"  - {key}: {desc}")
    
    print("\n✓ Database config:")
    print(f"  Host: {config.DB_HOST}:{config.DB_PORT}")
    print(f"  Database: {config.DB_NAME}")
    
    print("\n✓ LLM config:")
    print(f"  Provider: {config.LLM_PROVIDER}")
    print(f"  Model: {config.LLM_MODEL}")
    
    print("\n" + "=" * 60)
    print("✓ UI Controller is ready!")
    print("=" * 60)
    
    print("\nTo launch the app, run:")
    print("  streamlit run app.py")
    print("\nOr using the full path:")
    print("  c:/Users/Pc/Desktop/TxnTutor/.venv/Scripts/streamlit.exe run app.py")

if __name__ == '__main__':
    try:
        test_ui_components()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
