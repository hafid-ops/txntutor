#!/usr/bin/env python3
"""
Verify database setup and show current state
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import execute_query
from config import config

def show_database_info():
    """Display database configuration and contents"""
    print("\n" + "="*60)
    print("DATABASE CONFIGURATION")
    print("="*60)
    print(f"Host: {config.DB_HOST}:{config.DB_PORT}")
    print(f"Database: {config.DB_NAME}")
    print(f"User: {config.DB_USER}")
    
    # Show all tables
    print("\n" + "="*60)
    print("TABLES")
    print("="*60)
    tables = execute_query("""
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = t.table_name AND table_schema = 'public') as column_count
        FROM information_schema.tables t
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    for table_name, col_count in tables:
        # Get row count
        row_count = execute_query(f"SELECT COUNT(*) FROM {table_name}")[0][0]
        print(f"  {table_name:<20} {col_count} columns, {row_count} rows")
    
    # Show default scenarios
    print("\n" + "="*60)
    print("DEFAULT SCENARIOS")
    print("="*60)
    scenarios = execute_query("""
        SELECT name, description, isolation_level
        FROM scenario
        ORDER BY scenario_id
    """)
    
    for i, (name, desc, iso_level) in enumerate(scenarios, 1):
        print(f"\n{i}. {name}")
        print(f"   Level: {iso_level}")
        print(f"   Desc:  {desc}")
    
    print("\n" + "="*60)
    print("✓ Database is ready for transaction simulation!")
    print("="*60)

if __name__ == '__main__':
    try:
        show_database_info()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
