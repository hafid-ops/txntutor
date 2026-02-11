# Transaction Isolation Levels in TxnTutor

## Overview

Transaction isolation levels control how and when changes made by one transaction become visible to other concurrent transactions. They define the trade-off between **data consistency** and **concurrency performance**.

## PostgreSQL Isolation Levels

PostgreSQL implements 4 standard SQL isolation levels:

### 1. READ UNCOMMITTED
**Lowest isolation, highest concurrency**

- **Allows:** Dirty reads (reading uncommitted data from other transactions)
- **PostgreSQL Note:** Actually behaves like READ COMMITTED (PostgreSQL doesn't support true dirty reads)
- **Use Case:** Testing dirty read scenarios (theoretical)
- **Anomalies:** All anomalies possible

```python
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
```

**TxnTutor Simulators:**
- `dirty_read` - Demonstrates reading uncommitted data

---

### 2. READ COMMITTED (Default)
**Most commonly used isolation level**

- **Guarantees:** Only committed data is visible
- **Allows:** Non-repeatable reads, phantom reads
- **Prevents:** Dirty reads
- **Behavior:** Each query sees a consistent snapshot at query start time
- **Anomalies:** Lost updates, non-repeatable reads, phantom reads

```python
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
```

**TxnTutor Simulators:**
- `lost_update` - Both transactions read same value, one update is lost
- `non_repeatable_read` - Same query returns different results within transaction
- `phantom_read` - Range query sees different rows on second execution
- `deadlock` - Circular lock dependencies

**Characteristics:**
- ✓ Each statement sees latest committed data
- ✓ Good balance of consistency and performance
- ✗ Same query can return different results
- ✗ Susceptible to lost updates

---

### 3. REPEATABLE READ
**Snapshot isolation**

- **Guarantees:** All reads within transaction see consistent snapshot
- **Allows:** Write skew, serialization anomalies
- **Prevents:** Dirty reads, non-repeatable reads, phantom reads
- **Behavior:** Transaction sees snapshot from its start time
- **Anomalies:** Write skew, serialization anomalies

```python
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
```

**TxnTutor Simulators:**
- `write_skew` - Overlapping reads, disjoint writes violate constraints

**Characteristics:**
- ✓ Consistent reads throughout transaction
- ✓ Prevents phantom reads
- ✗ Can cause serialization failures
- ✗ Write skew still possible

**PostgreSQL Implementation:**
- Uses MVCC (Multi-Version Concurrency Control)
- May abort with serialization error if conflicts detected
- Better than SQL standard (also prevents phantom reads)

---

### 4. SERIALIZABLE
**Highest isolation, lowest concurrency**

- **Guarantees:** Transactions execute as if serial (one after another)
- **Allows:** Nothing - complete isolation
- **Prevents:** All anomalies
- **Behavior:** Full isolation with conflict detection
- **Anomalies:** None (fully consistent)

```python
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
```

**TxnTutor Note:** Not currently used in default simulators

**Características:**
- ✓ Complete data consistency
- ✓ No anomalies possible
- ✗ Lowest concurrency (more serialization failures)
- ✗ Performance overhead for conflict detection

---

## Anomaly-to-Isolation Level Matrix

| Anomaly Type | READ UNCOMMITTED | READ COMMITTED | REPEATABLE READ | SERIALIZABLE |
|--------------|------------------|----------------|-----------------|--------------|
| Dirty Read | ❌ Possible | ✅ Prevented | ✅ Prevented | ✅ Prevented |
| Lost Update | ❌ Possible | ❌ Possible | ❌ Possible* | ✅ Prevented |
| Non-Repeatable Read | ❌ Possible | ❌ Possible | ✅ Prevented | ✅ Prevented |
| Phantom Read | ❌ Possible | ❌ Possible | ✅ Prevented** | ✅ Prevented |
| Write Skew | ❌ Possible | ❌ Possible | ❌ Possible | ✅ Prevented |
| Deadlock | ❌ Possible | ❌ Possible | ❌ Possible | ❌ Possible*** |

\* Lost updates cause serialization errors in REPEATABLE READ  
\*\* PostgreSQL extension - SQL standard doesn't prevent this  
\*\*\* Deadlocks are lock conflicts, not isolation level anomalies

---

## TxnTutor Simulator Configuration

Each simulator uses the appropriate isolation level to demonstrate the anomaly:

```python
SIMULATOR_ISOLATION_LEVELS = {
    'lost_update': 'READ COMMITTED',      # Both read same value
    'dirty_read': 'READ UNCOMMITTED',     # Read uncommitted data
    'non_repeatable_read': 'READ COMMITTED',  # Same query, different results
    'phantom_read': 'READ COMMITTED',     # Different row count
    'write_skew': 'REPEATABLE READ',      # Constraint violation
    'deadlock': 'READ COMMITTED'          # Lock conflict
}
```

---

## Choosing the Right Isolation Level

### Use READ COMMITTED when:
- ✓ Standard OLTP application
- ✓ Need good concurrency
- ✓ Can handle non-repeatable reads
- ✓ Most web applications

### Use REPEATABLE READ when:
- ✓ Need consistent reads
- ✓ Long-running reports
- ✓ Complex multi-query transactions
- ✓ Can handle serialization failures

### Use SERIALIZABLE when:
- ✓ Financial transactions
- ✓ Absolute consistency required
- ✓ Can afford performance cost
- ✓ Critical data integrity

---

## Prevention Strategies

### Lost Update
**Fix:** Use `SELECT ... FOR UPDATE` or SERIALIZABLE
```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 'A' FOR UPDATE;
-- Now other transactions must wait
UPDATE accounts SET balance = balance + 50 WHERE id = 'A';
COMMIT;
```

### Dirty Read
**Fix:** Use READ COMMITTED or higher
```python
conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
```

### Non-Repeatable Read
**Fix:** Use REPEATABLE READ or SERIALIZABLE
```python
conn.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
```

### Phantom Read
**Fix:** Use REPEATABLE READ or SERIALIZABLE (in PostgreSQL)
```python
conn.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
```

### Write Skew
**Fix:** Use SERIALIZABLE or explicit locking
```sql
-- Option 1: SERIALIZABLE isolation
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

-- Option 2: Lock all read rows
SELECT * FROM accounts WHERE conditions FOR UPDATE;
```

### Deadlock
**Fix:** Lock resources in consistent order or use timeouts
```sql
-- Always lock accounts in alphabetical order
SELECT * FROM accounts WHERE id IN ('A', 'B') ORDER BY id FOR UPDATE;
```

---

## Setting Isolation Level in TxnTutor

### In Database Connection
```python
conn = psycopg2.connect(...)
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
```

### In SQL
```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
-- your queries
COMMIT;
```

### Per Session
```sql
SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

---

## References

- [PostgreSQL Documentation - Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [ANSI SQL-92 Isolation Levels](https://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt)
- [A Critique of ANSI SQL Isolation Levels](https://www.microsoft.com/en-us/research/publication/a-critique-of-ansi-sql-isolation-levels/)

---

## Testing in TxnTutor

Run simulators to see isolation levels in action:

```bash
python tests/test_simulator.py
```

Each test demonstrates how different isolation levels allow or prevent specific anomalies.
