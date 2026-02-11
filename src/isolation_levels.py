# Transaction Isolation Levels Reference
"""
Quick reference for PostgreSQL transaction isolation levels and their behaviors.
"""

import psycopg2.extensions

# Isolation level constants (for easy reference)
class IsolationLevel:
    READ_UNCOMMITTED = psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED
    READ_COMMITTED = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
    REPEATABLE_READ = psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ
    SERIALIZABLE = psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE

# Mapping of isolation level names to constants
ISOLATION_LEVELS = {
    'READ UNCOMMITTED': IsolationLevel.READ_UNCOMMITTED,
    'READ COMMITTED': IsolationLevel.READ_COMMITTED,
    'REPEATABLE READ': IsolationLevel.REPEATABLE_READ,
    'SERIALIZABLE': IsolationLevel.SERIALIZABLE,
}

# Isolation levels used by each simulator
SIMULATOR_ISOLATION_LEVELS = {
    'lost_update': 'READ COMMITTED',
    'dirty_read': 'READ UNCOMMITTED',
    'non_repeatable_read': 'READ COMMITTED',
    'phantom_read': 'READ COMMITTED',
    'write_skew': 'REPEATABLE READ',
    'deadlock': 'READ COMMITTED'
}

# Anomaly prevention matrix
ANOMALY_PREVENTION = {
    'READ UNCOMMITTED': {
        'dirty_read': False,
        'lost_update': False,
        'non_repeatable_read': False,
        'phantom_read': False,
        'write_skew': False,
    },
    'READ COMMITTED': {
        'dirty_read': True,  # Prevented
        'lost_update': False,
        'non_repeatable_read': False,
        'phantom_read': False,
        'write_skew': False,
    },
    'REPEATABLE READ': {
        'dirty_read': True,  # Prevented
        'lost_update': True,  # Prevented (causes serialization error)
        'non_repeatable_read': True,  # Prevented
        'phantom_read': True,  # Prevented (PostgreSQL extension)
        'write_skew': False,
    },
    'SERIALIZABLE': {
        'dirty_read': True,  # Prevented
        'lost_update': True,  # Prevented
        'non_repeatable_read': True,  # Prevented
        'phantom_read': True,  # Prevented
        'write_skew': True,  # Prevented
    }
}

# Isolation level descriptions
ISOLATION_DESCRIPTIONS = {
    'READ UNCOMMITTED': 'Allows reading uncommitted data (dirty reads). PostgreSQL treats this as READ COMMITTED.',
    'READ COMMITTED': 'Default level. Each query sees committed data. Allows non-repeatable reads and phantoms.',
    'REPEATABLE READ': 'Snapshot isolation. Consistent reads throughout transaction. Prevents phantoms in PostgreSQL.',
    'SERIALIZABLE': 'Highest isolation. Transactions execute as if serial. Prevents all anomalies.'
}

# Performance characteristics
ISOLATION_PERFORMANCE = {
    'READ UNCOMMITTED': {'concurrency': 'Highest', 'consistency': 'Lowest', 'locks': 'Minimal'},
    'READ COMMITTED': {'concurrency': 'High', 'consistency': 'Medium', 'locks': 'Statement-level'},
    'REPEATABLE READ': {'concurrency': 'Medium', 'consistency': 'High', 'locks': 'Transaction-level'},
    'SERIALIZABLE': {'concurrency': 'Lowest', 'consistency': 'Highest', 'locks': 'Full serialization'}
}

def get_isolation_level(level_name: str) -> int:
    """
    Get psycopg2 isolation level constant from name.
    
    Args:
        level_name: String like 'READ COMMITTED'
    
    Returns:
        Integer constant for psycopg2
    """
    return ISOLATION_LEVELS.get(level_name.upper(), IsolationLevel.READ_COMMITTED)

def prevents_anomaly(isolation_level: str, anomaly: str) -> bool:
    """
    Check if an isolation level prevents a specific anomaly.
    
    Args:
        isolation_level: 'READ COMMITTED', 'REPEATABLE READ', etc.
        anomaly: 'dirty_read', 'lost_update', etc.
    
    Returns:
        True if anomaly is prevented at this level
    """
    level_upper = isolation_level.upper()
    return ANOMALY_PREVENTION.get(level_upper, {}).get(anomaly, False)

def get_recommended_level(anomaly_type: str) -> str:
    """
    Get recommended isolation level to prevent a specific anomaly.
    
    Args:
        anomaly_type: 'dirty_read', 'lost_update', etc.
    
    Returns:
        Recommended isolation level name
    """
    recommendations = {
        'dirty_read': 'READ COMMITTED',
        'lost_update': 'REPEATABLE READ',  # or use SELECT FOR UPDATE
        'non_repeatable_read': 'REPEATABLE READ',
        'phantom_read': 'REPEATABLE READ',  # PostgreSQL prevents this
        'write_skew': 'SERIALIZABLE',
        'deadlock': 'N/A - Use lock ordering strategy'
    }
    return recommendations.get(anomaly_type, 'SERIALIZABLE')

def get_isolation_info(level_name: str) -> dict:
    """
    Get comprehensive information about an isolation level.
    
    Returns:
        Dict with description, performance, and prevention info
    """
    level_upper = level_name.upper()
    return {
        'name': level_name,
        'description': ISOLATION_DESCRIPTIONS.get(level_upper, 'Unknown'),
        'performance': ISOLATION_PERFORMANCE.get(level_upper, {}),
        'prevents': ANOMALY_PREVENTION.get(level_upper, {}),
        'constant': ISOLATION_LEVELS.get(level_upper)
    }

def print_isolation_matrix():
    """Print a formatted matrix of isolation levels vs anomalies."""
    anomalies = ['dirty_read', 'lost_update', 'non_repeatable_read', 'phantom_read', 'write_skew']
    levels = ['READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE']
    
    print("\n" + "="*80)
    print("TRANSACTION ISOLATION LEVELS - ANOMALY PREVENTION MATRIX")
    print("="*80)
    
    # Header
    print(f"{'Isolation Level':<25}", end='')
    for anomaly in anomalies:
        print(f"{anomaly.replace('_', ' ').title():<20}", end='')
    print()
    print("-"*80)
    
    # Rows
    for level in levels:
        print(f"{level:<25}", end='')
        for anomaly in anomalies:
            prevented = ANOMALY_PREVENTION[level].get(anomaly, False)
            symbol = '✓ Prevented' if prevented else '✗ Possible'
            print(f"{symbol:<20}", end='')
        print()
    
    print("="*80)

def print_simulator_info():
    """Print which isolation level each simulator uses."""
    print("\n" + "="*60)
    print("TXNTUTOR SIMULATORS - ISOLATION LEVEL USAGE")
    print("="*60)
    
    for simulator, level in SIMULATOR_ISOLATION_LEVELS.items():
        anomaly_name = simulator.replace('_', ' ').title()
        print(f"{anomaly_name:<25} → {level}")
    
    print("="*60)

if __name__ == '__main__':
    # Demo output
    print_isolation_matrix()
    print()
    print_simulator_info()
    
    print("\n" + "="*60)
    print("EXAMPLE USAGE")
    print("="*60)
    print("\n# Get isolation level constant:")
    print("level = get_isolation_level('READ COMMITTED')")
    print("conn.set_isolation_level(level)")
    
    print("\n# Check if level prevents anomaly:")
    print("prevents_anomaly('REPEATABLE READ', 'phantom_read')  # True")
    
    print("\n# Get recommendation:")
    print("get_recommended_level('lost_update')  # 'REPEATABLE READ'")
