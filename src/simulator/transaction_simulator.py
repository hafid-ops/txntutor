# Transaction Simulator - Executes concurrent T1, T2
import psycopg2
import threading
import time
import logging
from typing import Dict, Any, Callable
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import config
from src.db_operations import (
    create_transaction,
    update_transaction_status,
    log_trace_event
)
from datetime import datetime

logger = logging.getLogger(__name__)

class TransactionSimulator:
    """Simulates concurrent transactions to demonstrate concurrency anomalies"""
    
    def __init__(self, run_id: int):
        self.run_id = run_id
        self.sequence_counter = 0
        self.sequence_lock = threading.Lock()
    
    def _setup_test_table(self):
        """Create accounts table for testing"""
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop and recreate for clean state
        cursor.execute("DROP TABLE IF EXISTS accounts CASCADE")
        cursor.execute("""
            CREATE TABLE accounts (
                account_id VARCHAR(10) PRIMARY KEY,
                balance INTEGER NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO accounts VALUES ('A', 100, NOW())")
        cursor.execute("INSERT INTO accounts VALUES ('B', 200, NOW())")
        
        cursor.close()
        conn.close()
    
    def _get_next_sequence(self) -> int:
        """Thread-safe sequence number generator"""
        with self.sequence_lock:
            self.sequence_counter += 1
            return self.sequence_counter
    
    def _log_event(self, tx_id: int, tx_name: str, event_type: str, **kwargs):
        """Log a trace event"""
        log_trace_event(
            run_id=self.run_id,
            tx_id=tx_id,
            event_type=event_type,
            sequence_order=self._get_next_sequence(),
            **kwargs
        )
        logger.info(f"{tx_name}: {event_type} {kwargs}")
    
    def run_simulator(self, simulator_type: str, t1_amount: int = 50, t2_amount: int = -20) -> Dict[str, Any]:
        """
        Run a specific simulator pattern
        
        Args:
            simulator_type: One of the 6 patterns
            t1_amount: Amount for T1 operation
            t2_amount: Amount for T2 operation
        
        Returns:
            Dict with execution results
        """
        simulators = {
            'lost_update': self._simulate_lost_update,
            'dirty_read': self._simulate_dirty_read,
            'non_repeatable_read': self._simulate_non_repeatable_read,
            'phantom_read': self._simulate_phantom_read,
            'write_skew': self._simulate_write_skew,
            'deadlock': self._simulate_deadlock
        }
        
        simulator_func = simulators.get(simulator_type)
        if not simulator_func:
            raise ValueError(f"Unknown simulator type: {simulator_type}")
        
        # Setup test table with initial balance of 100
        self._setup_test_table()
        
        return simulator_func(t1_amount, t2_amount)
    
    # ==================== LOST UPDATE ====================
    
    def _simulate_lost_update(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Lost Update: Both transactions read the same value, then write different values.
        T1 writes t1_amount, T2 writes t2_amount. The second commit overwrites the first.
        """
        results = {'t1_final': None, 't2_final': None, 'actual_final': None}
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                # BEGIN
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # READ
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='A', old_value=balance)
                
                time.sleep(0.1)  # Let T2 also read
                
                # WRITE (set to t1_amount directly)
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t1_amount,))
                self._log_event(tx_id, 'T1', 'WRITE', table_name='accounts', record_key='A', 
                               old_value=balance, new_value=t1_amount)
                
                time.sleep(0.1)
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T1', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
                results['t1_final'] = t1_amount
                
            except Exception as e:
                conn.rollback()
                self._log_event(tx_id, 'T1', 'ROLLBACK', notes=str(e))
                update_transaction_status(tx_id, 'rolled_back', rolled_back=True)
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.05)  # Start slightly after T1
                
                # BEGIN
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # READ
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='A', old_value=balance)
                
                time.sleep(0.15)  # Let T1 commit first
                
                # WRITE (overwrites T1's update with t2_amount)
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t2_amount,))
                self._log_event(tx_id, 'T2', 'WRITE', table_name='accounts', record_key='A',
                               old_value=balance, new_value=t2_amount)
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
                results['t2_final'] = t2_amount
                
            except Exception as e:
                conn.rollback()
                self._log_event(tx_id, 'T2', 'ROLLBACK', notes=str(e))
                update_transaction_status(tx_id, 'rolled_back', rolled_back=True)
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        # Create transaction records
        tx1_id = create_transaction(self.run_id, 'T1', 'READ COMMITTED')
        tx2_id = create_transaction(self.run_id, 'T2', 'READ COMMITTED')
        
        # Run concurrently
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        # Check final value
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
        results['actual_final'] = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return results
    
    # ==================== DIRTY READ ====================
    
    def _simulate_dirty_read(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Dirty Read: T2 reads uncommitted data from T1, then T1 rolls back.
        """
        results = {'t2_read_value': None, 'actual_final': None}
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
            cursor = conn.cursor()
            
            try:
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # READ
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='A', old_value=balance)
                
                # WRITE (but don't commit yet) — set to t1_amount directly
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t1_amount,))
                self._log_event(tx_id, 'T1', 'WRITE', table_name='accounts', record_key='A',
                               old_value=balance, new_value=t1_amount)
                
                time.sleep(0.2)  # Let T2 read the uncommitted value
                
                # ROLLBACK
                conn.rollback()
                self._log_event(tx_id, 'T1', 'ROLLBACK', notes='Intentional rollback for dirty read demo')
                update_transaction_status(tx_id, 'rolled_back', rolled_back=True)
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.1)  # Wait for T1 to write
                
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # READ (dirty - uncommitted data from T1)
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='A', 
                               old_value=balance, notes='DIRTY READ - uncommitted data')
                
                results['t2_read_value'] = balance
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        tx1_id = create_transaction(self.run_id, 'T1', 'READ UNCOMMITTED')
        tx2_id = create_transaction(self.run_id, 'T2', 'READ UNCOMMITTED')
        
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        # Check final value
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
        results['actual_final'] = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return results
    
    # ==================== NON-REPEATABLE READ ====================
    
    def _simulate_non_repeatable_read(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Non-Repeatable Read: T1 reads a value, T2 updates it, T1 reads again and gets different value.
        """
        results = {'t1_first_read': None, 't1_second_read': None}
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # FIRST READ
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance1 = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='A', 
                               old_value=balance1, notes='First read')
                results['t1_first_read'] = balance1
                
                time.sleep(0.2)  # Let T2 update
                
                # SECOND READ (non-repeatable)
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance2 = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='A',
                               old_value=balance2, notes='Second read - NON-REPEATABLE')
                results['t1_second_read'] = balance2
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T1', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.1)  # Wait for T1's first read
                
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # READ and UPDATE
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='A', old_value=balance)
                
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t2_amount,))
                self._log_event(tx_id, 'T2', 'WRITE', table_name='accounts', record_key='A',
                               old_value=balance, new_value=t2_amount)
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        tx1_id = create_transaction(self.run_id, 'T1', 'READ COMMITTED')
        tx2_id = create_transaction(self.run_id, 'T2', 'READ COMMITTED')
        
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        return results
    
    # ==================== PHANTOM READ ==
    
    def _simulate_phantom_read(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Phantom Read: T1 queries a range, T2 inserts a new row, T1 queries again and sees different rows.
        """
        results = {'t1_first_count': None, 't1_second_count': None}
        
        # Insert additional account for range query
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO accounts VALUES ('C', 150, NOW()) ON CONFLICT DO NOTHING")
        conn.commit()
        cursor.close()
        conn.close()
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # FIRST QUERY (range)
                cursor.execute("SELECT COUNT(*) FROM accounts WHERE balance >= 100")
                count1 = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='COUNT(*)',
                               old_value=count1, notes='First count query')
                results['t1_first_count'] = count1
                
                time.sleep(0.2)  # Let T2 insert
                
                # SECOND QUERY (phantom appears)
                cursor.execute("SELECT COUNT(*) FROM accounts WHERE balance >= 100")
                count2 = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='COUNT(*)',
                               old_value=count2, notes='Second count - PHANTOM READ')
                results['t1_second_count'] = count2
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T1', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.1)  # Wait for T1's first query
                
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # INSERT new row with t2_amount as balance
                cursor.execute("INSERT INTO accounts VALUES ('D', %s, NOW())", (t2_amount,))
                self._log_event(tx_id, 'T2', 'WRITE', table_name='accounts', record_key='D',
                               old_value=None, new_value=t2_amount, notes='Insert new account')
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        tx1_id = create_transaction(self.run_id, 'T1', 'READ COMMITTED')
        tx2_id = create_transaction(self.run_id, 'T2', 'READ COMMITTED')
        
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        return results
    
    # ==================== WRITE SKEW ====================
    
    def _simulate_write_skew(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Write Skew: Both transactions read overlapping data and make disjoint updates
        that violate a constraint.
        Example: Total balance must be >= 100. Both read balances, both write to different accounts.
        """
        results = {'initial_total': None, 'final_total': None}
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
            cursor = conn.cursor()
            
            try:
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # READ both accounts
                cursor.execute("SELECT SUM(balance) FROM accounts WHERE account_id IN ('A', 'B')")
                total = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='SUM(A,B)',
                               old_value=total, notes='Read total balance')
                
                time.sleep(0.05)
                
                # UPDATE account A (assuming constraint: total >= 100)
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A'")
                balance_a = cursor.fetchone()[0]
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t1_amount,))
                self._log_event(tx_id, 'T1', 'WRITE', table_name='accounts', record_key='A',
                               old_value=balance_a, new_value=t1_amount)
                
                time.sleep(0.1)
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T1', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.03)  # Overlap with T1
                
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # READ both accounts
                cursor.execute("SELECT SUM(balance) FROM accounts WHERE account_id IN ('A', 'B')")
                total = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='SUM(A,B)',
                               old_value=total, notes='Read total balance')
                
                # UPDATE account B
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'B'")
                balance_b = cursor.fetchone()[0]
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'B'", (t2_amount,))
                self._log_event(tx_id, 'T2', 'WRITE', table_name='accounts', record_key='B',
                               old_value=balance_b, new_value=t2_amount)
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except Exception as e:
                conn.rollback()
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        # Get initial total
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(balance) FROM accounts WHERE account_id IN ('A', 'B')")
        results['initial_total'] = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        tx1_id = create_transaction(self.run_id, 'T1', 'REPEATABLE READ')
        tx2_id = create_transaction(self.run_id, 'T2', 'REPEATABLE READ')
        
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        # Get final total
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(balance) FROM accounts WHERE account_id IN ('A', 'B')")
        results['final_total'] = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return results
    
    # ==================== DEADLOCK ====================
    
    def _simulate_deadlock(self, t1_amount: int, t2_amount: int) -> Dict:
        """
        Deadlock: T1 locks A then tries to lock B, T2 locks B then tries to lock A.
        """
        results = {'deadlock_occurred': False, 'deadlock_victim': None}
        
        def t1_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                self._log_event(tx_id, 'T1', 'BEGIN')
                
                # Lock A
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A' FOR UPDATE")
                balance_a = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='A',
                               old_value=balance_a, notes='Lock acquired on A')
                
                time.sleep(0.1)  # Let T2 lock B
                
                # Try to lock B (deadlock!)
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'B' FOR UPDATE")
                balance_b = cursor.fetchone()[0]
                self._log_event(tx_id, 'T1', 'READ', table_name='accounts', record_key='B',
                               old_value=balance_b, notes='Lock acquired on B')
                
                # Update both
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t1_amount,))
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'B'", (t1_amount,))
                self._log_event(tx_id, 'T1', 'WRITE', table_name='accounts', record_key='A,B',
                               old_value=f"{balance_a},{balance_b}", new_value=f"{t1_amount},{t1_amount}")
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T1', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except psycopg2.extensions.TransactionRollbackError as e:
                # Deadlock detected!
                results['deadlock_occurred'] = True
                results['deadlock_victim'] = 'T1'
                conn.rollback()
                self._log_event(tx_id, 'T1', 'ROLLBACK', notes=f'DEADLOCK VICTIM: {str(e)}')
                update_transaction_status(tx_id, 'rolled_back', rolled_back=True)
                logger.info(f"T1 was deadlock victim")
            except Exception as e:
                conn.rollback()
                logger.error(f"T1 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        def t2_logic(tx_id):
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            cursor = conn.cursor()
            
            try:
                time.sleep(0.05)  # Start slightly after T1
                
                self._log_event(tx_id, 'T2', 'BEGIN')
                
                # Lock B
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'B' FOR UPDATE")
                balance_b = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='B',
                               old_value=balance_b, notes='Lock acquired on B')
                
                time.sleep(0.1)  # Let T1 try to lock B
                
                # Try to lock A (deadlock!)
                cursor.execute("SELECT balance FROM accounts WHERE account_id = 'A' FOR UPDATE")
                balance_a = cursor.fetchone()[0]
                self._log_event(tx_id, 'T2', 'READ', table_name='accounts', record_key='A',
                               old_value=balance_a, notes='Lock acquired on A')
                
                # Update both
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'A'", (t2_amount,))
                cursor.execute("UPDATE accounts SET balance = %s WHERE account_id = 'B'", (t2_amount,))
                self._log_event(tx_id, 'T2', 'WRITE', table_name='accounts', record_key='A,B',
                               old_value=f"{balance_a},{balance_b}", new_value=f"{t2_amount},{t2_amount}")
                
                # COMMIT
                conn.commit()
                self._log_event(tx_id, 'T2', 'COMMIT')
                update_transaction_status(tx_id, 'committed', datetime.now())
                
            except psycopg2.extensions.TransactionRollbackError as e:
                # Deadlock detected!
                results['deadlock_occurred'] = True
                results['deadlock_victim'] = 'T2'
                conn.rollback()
                self._log_event(tx_id, 'T2', 'ROLLBACK', notes=f'DEADLOCK VICTIM: {str(e)}')
                update_transaction_status(tx_id, 'rolled_back', rolled_back=True)
                logger.info(f"T2 was deadlock victim")
            except Exception as e:
                conn.rollback()
                logger.error(f"T2 error: {e}")
            finally:
                cursor.close()
                conn.close()
        
        tx1_id = create_transaction(self.run_id, 'T1', 'READ COMMITTED')
        tx2_id = create_transaction(self.run_id, 'T2', 'READ COMMITTED')
        
        t1_thread = threading.Thread(target=t1_logic, args=(tx1_id,))
        t2_thread = threading.Thread(target=t2_logic, args=(tx2_id,))
        
        t1_thread.start()
        t2_thread.start()
        
        t1_thread.join()
        t2_thread.join()
        
        return results
