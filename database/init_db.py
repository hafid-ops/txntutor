# Database initialization script
import psycopg2
from psycopg2 import sql
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

def create_database():
    """Create the TxnTutor database if it doesn't exist"""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database='postgres',
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.DB_NAME,)
        )
        
        if not cursor.fetchone():
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(config.DB_NAME)
                )
            )
            print(f"✓ Database '{config.DB_NAME}' created successfully")
        else:
            print(f"✓ Database '{config.DB_NAME}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False

def run_schema():
    """Execute the schema.sql file to create tables"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        cursor.execute(schema_sql)
        conn.commit()
        
        print("✓ Schema created successfully")
        print("✓ Tables: scenario, run, tx, trace_event, anomaly, explanation")
        print("✓ Default scenarios inserted")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error running schema: {e}")
        return False

def verify_setup():
    """Verify the database setup"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['scenario', 'run', 'tx', 'trace_event', 'anomaly', 'explanation']
        missing = set(expected_tables) - set(tables)
        
        if missing:
            print(f"✗ Missing tables: {missing}")
            return False
        
        # Check scenarios
        cursor.execute("SELECT COUNT(*) FROM scenario")
        scenario_count = cursor.fetchone()[0]
        
        print(f"\n✓ Verification successful")
        print(f"  - All 6 core tables exist")
        print(f"  - {scenario_count} default scenarios loaded")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

if __name__ == '__main__':
    print("=== TxnTutor Database Initialization ===")
    print(f"Host: {config.DB_HOST}:{config.DB_PORT}")
    print(f"Database: {config.DB_NAME}\n")
    
    if not create_database():
        sys.exit(1)
    
    if not run_schema():
        sys.exit(1)
    
    if not verify_setup():
        sys.exit(1)
    
    print("\n🎉 Database initialization complete!")
