# Anomaly Detection Module (rule-based)
import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Rule-based anomaly detector for transaction concurrency issues"""
    
    def __init__(self, trace_events: List[Dict]):
        """
        Initialize detector with trace events
        
        Args:
            trace_events: List of trace event dicts from get_trace_events()
        """
        self.events = trace_events
        self.events_by_tx = self._group_by_transaction()
        self.anomalies = []
    
    def _group_by_transaction(self) -> Dict[str, List[Dict]]:
        """Group events by transaction name"""
        grouped = defaultdict(list)
        for event in self.events:
            grouped[event['tx_name']].append(event)
        return grouped
    
    def detect_all(self) -> List[Dict]:
        """
        Run all anomaly detection rules
        
        Returns:
            List of detected anomalies with details
        """
        self.anomalies = []
        
        # Run each detector
        self._detect_lost_update()
        self._detect_dirty_read()
        self._detect_non_repeatable_read()
        self._detect_phantom_read()
        self._detect_write_skew()
        self._detect_deadlock()
        
        return self.anomalies
    
    def _add_anomaly(self, anomaly_type: str, description: str, 
                     severity: str = 'medium', affected_txs: List[str] = None,
                     event_ids: List[int] = None):
        """Add an anomaly to the results"""
        self.anomalies.append({
            'type': anomaly_type,
            'description': description,
            'severity': severity,
            'affected_transactions': affected_txs or [],
            'event_sequence': event_ids or []
        })
    
    # ==================== LOST UPDATE ====================
    
    def _detect_lost_update(self):
        """
        Detect lost update: Both transactions read same value, 
        both write, second write overwrites first.
        
        Pattern:
        - T1 READ(X)
        - T2 READ(X) - same value
        - T1 WRITE(X)
        - T1 COMMIT
        - T2 WRITE(X) - overwrites T1's update
        - T2 COMMIT
        """
        reads = {}  # key -> [(tx_name, value, event_id), ...]
        writes = {}  # key -> [(tx_name, old_val, new_val, event_id, committed), ...]
        commits = set()  # Set of committed tx names
        
        for event in self.events:
            tx_name = event['tx_name']
            event_type = event['event_type']
            record_key = event.get('record_key')
            
            if event_type == 'READ' and record_key:
                if record_key not in reads:
                    reads[record_key] = []
                reads[record_key].append((tx_name, event.get('old_value'), event['event_id']))
            
            elif event_type == 'WRITE' and record_key:
                if record_key not in writes:
                    writes[record_key] = []
                writes[record_key].append({
                    'tx': tx_name,
                    'old': event.get('old_value'),
                    'new': event.get('new_value'),
                    'event_id': event['event_id'],
                    'committed': False
                })
            
            elif event_type == 'COMMIT':
                commits.add(tx_name)
                # Mark all writes by this tx as committed
                for key_writes in writes.values():
                    for write in key_writes:
                        if write['tx'] == tx_name:
                            write['committed'] = True
        
        # Check for lost updates
        for key, key_reads in reads.items():
            if len(key_reads) >= 2 and key in writes:
                key_writes = writes[key]
                
                # Check if multiple transactions read the same initial value
                initial_values = {}
                for tx, value, _ in key_reads:
                    if tx not in initial_values:
                        initial_values[tx] = value
                
                # Find transactions that wrote after reading same value
                same_value_txs = defaultdict(list)
                for tx, value, event_id in key_reads:
                    same_value_txs[value].append(tx)
                
                for value, txs in same_value_txs.items():
                    if len(txs) >= 2:
                        # Multiple transactions read same value
                        # Check if both committed writes
                        committed_writers = [w for w in key_writes 
                                           if w['tx'] in txs and w['committed']]
                        
                        if len(committed_writers) >= 2:
                            # Lost update detected!
                            event_ids = [w['event_id'] for w in committed_writers]
                            affected = [w['tx'] for w in committed_writers]
                            
                            # Determine which update was lost (the earlier one)
                            first_writer = committed_writers[0]
                            last_writer = committed_writers[-1]
                            
                            self._add_anomaly(
                                'lost_update',
                                f"Lost Update detected on {key}: {first_writer['tx']} wrote "
                                f"{first_writer['new']} (from {value}), but {last_writer['tx']} "
                                f"overwrote it with {last_writer['new']} (also from {value}). "
                                f"{first_writer['tx']}'s update was lost.",
                                severity='high',
                                affected_txs=affected,
                                event_ids=event_ids
                            )
    
    # ==================== DIRTY READ ====================
    
    def _detect_dirty_read(self):
        """
        Detect dirty read: Transaction reads uncommitted data that is later rolled back.
        
        Pattern:
        - T1 WRITE(X)
        - T2 READ(X) - reads T1's uncommitted value
        - T1 ROLLBACK
        """
        uncommitted_writes = {}  # key -> {tx: value, event_id}
        rolled_back_txs = set()
        
        for event in self.events:
            tx_name = event['tx_name']
            event_type = event['event_type']
            record_key = event.get('record_key')
            
            if event_type == 'WRITE' and record_key:
                uncommitted_writes[record_key] = {
                    'tx': tx_name,
                    'value': event.get('new_value'),
                    'event_id': event['event_id']
                }
            
            elif event_type == 'COMMIT':
                # Remove committed writes
                uncommitted_writes = {k: v for k, v in uncommitted_writes.items() 
                                    if v['tx'] != tx_name}
            
            elif event_type == 'ROLLBACK':
                rolled_back_txs.add(tx_name)
                
                # Check if any transaction read data from this rolled-back transaction
                for other_event in self.events:
                    if (other_event['tx_name'] != tx_name and
                        other_event['event_type'] == 'READ' and
                        'DIRTY READ' in str(other_event.get('notes', '')) or
                        'uncommitted' in str(other_event.get('notes', '')).lower()):
                        
                        self._add_anomaly(
                            'dirty_read',
                            f"Dirty Read detected: {other_event['tx_name']} read uncommitted "
                            f"data from {tx_name} on {other_event.get('record_key')}, "
                            f"then {tx_name} rolled back.",
                            severity='high',
                            affected_txs=[tx_name, other_event['tx_name']],
                            event_ids=[event['event_id'], other_event['event_id']]
                        )
    
    # ==================== NON-REPEATABLE READ ====================
    
    def _detect_non_repeatable_read(self):
        """
        Detect non-repeatable read: Transaction reads same key twice, gets different values.
        
        Pattern:
        - T1 READ(X) = a
        - T2 WRITE(X) = b
        - T2 COMMIT
        - T1 READ(X) = b (different from first read)
        """
        for tx_name, tx_events in self.events_by_tx.items():
            reads_by_key = defaultdict(list)
            
            for event in tx_events:
                if event['event_type'] == 'READ':
                    record_key = event.get('record_key')
                    if record_key and record_key != 'COUNT(*)' and record_key != 'SUM(A,B)':
                        reads_by_key[record_key].append({
                            'value': event.get('old_value'),
                            'event_id': event['event_id'],
                            'notes': event.get('notes', '')
                        })
            
            # Check for multiple reads of same key with different values
            for key, reads in reads_by_key.items():
                if len(reads) >= 2:
                    first_read = reads[0]
                    for subsequent_read in reads[1:]:
                        if (first_read['value'] != subsequent_read['value'] and
                            'NON-REPEATABLE' in subsequent_read['notes']):
                            
                            self._add_anomaly(
                                'non_repeatable_read',
                                f"Non-Repeatable Read detected: {tx_name} read {key} "
                                f"twice and got different values: first={first_read['value']}, "
                                f"second={subsequent_read['value']}.",
                                severity='medium',
                                affected_txs=[tx_name],
                                event_ids=[first_read['event_id'], subsequent_read['event_id']]
                            )
    
    # ==================== PHANTOM READ ====================
    
    def _detect_phantom_read(self):
        """
        Detect phantom read: Transaction executes same query twice, sees different rows.
        
        Pattern:
        - T1 COUNT(*) = n
        - T2 INSERT(...)
        - T2 COMMIT
        - T1 COUNT(*) = n+1 (phantom row appeared)
        """
        for tx_name, tx_events in self.events_by_tx.items():
            count_reads = []
            
            for event in tx_events:
                if event['event_type'] == 'READ':
                    record_key = event.get('record_key')
                    if 'COUNT' in str(record_key):
                        count_reads.append({
                            'count': event.get('old_value'),
                            'event_id': event['event_id'],
                            'notes': event.get('notes', '')
                        })
            
            # Check for different counts
            if len(count_reads) >= 2:
                first_count = count_reads[0]
                for subsequent_count in count_reads[1:]:
                    if (first_count['count'] != subsequent_count['count'] and
                        'PHANTOM' in subsequent_count['notes']):
                        
                        self._add_anomaly(
                            'phantom_read',
                            f"Phantom Read detected: {tx_name} executed the same query "
                            f"twice and saw different row counts: first={first_count['count']}, "
                            f"second={subsequent_count['count']}. Phantom rows appeared.",
                            severity='medium',
                            affected_txs=[tx_name],
                            event_ids=[first_count['event_id'], subsequent_count['event_id']]
                        )
    
    # ==================== WRITE SKEW ====================
    
    def _detect_write_skew(self):
        """
        Detect write skew: Transactions read overlapping data, make disjoint writes
        that violate constraints.
        
        Pattern:
        - T1 READ SUM(A,B) 
        - T2 READ SUM(A,B) (same value)
        - T1 WRITE(A)
        - T1 COMMIT
        - T2 WRITE(B) (different key)
        - T2 COMMIT
        - Final sum violates constraint
        """
        # Look for transactions that read aggregates and write to different keys
        aggregate_reads = defaultdict(list)  # tx -> [reads]
        writes_by_tx = defaultdict(set)  # tx -> {keys written}
        
        for event in self.events:
            tx_name = event['tx_name']
            event_type = event['event_type']
            record_key = event.get('record_key', '')
            
            if event_type == 'READ' and ('SUM' in record_key or 'total' in str(event.get('notes', '')).lower()):
                aggregate_reads[tx_name].append({
                    'value': event.get('old_value'),
                    'event_id': event['event_id']
                })
            
            elif event_type == 'WRITE':
                writes_by_tx[tx_name].add(record_key)
        
        # Check if multiple txs read same aggregate and wrote to different keys
        if len(aggregate_reads) >= 2:
            tx_names = list(aggregate_reads.keys())
            if len(tx_names) >= 2:
                t1, t2 = tx_names[0], tx_names[1]
                
                # Check if they wrote to different keys (disjoint writes)
                t1_keys = writes_by_tx.get(t1, set())
                t2_keys = writes_by_tx.get(t2, set())
                
                if t1_keys and t2_keys and not (t1_keys & t2_keys):
                    # Disjoint writes detected
                    event_ids = ([r['event_id'] for r in aggregate_reads[t1]] +
                                [r['event_id'] for r in aggregate_reads[t2]])
                    
                    self._add_anomaly(
                        'write_skew',
                        f"Write Skew detected: {t1} and {t2} both read overlapping data "
                        f"(aggregate values) but made disjoint writes to different records. "
                        f"This can violate integrity constraints even at REPEATABLE READ.",
                        severity='high',
                        affected_txs=[t1, t2],
                        event_ids=event_ids
                    )
    
    # ==================== DEADLOCK ====================
    
    def _detect_deadlock(self):
        """
        Detect deadlock: Transactions rolled back due to deadlock detection.
        
        Pattern:
        - T1 or T2 has ROLLBACK with 'DEADLOCK' in notes
        """
        for event in self.events:
            if event['event_type'] == 'ROLLBACK':
                notes = event.get('notes', '')
                if 'DEADLOCK' in notes.upper():
                    # Extract victim transaction
                    tx_name = event['tx_name']
                    
                    # Find the other transaction involved
                    other_txs = [tx for tx in self.events_by_tx.keys() if tx != tx_name]
                    
                    self._add_anomaly(
                        'deadlock',
                        f"Deadlock detected: {tx_name} was chosen as deadlock victim and "
                        f"rolled back. Circular lock dependency occurred between transactions.",
                        severity='high',
                        affected_txs=[tx_name] + other_txs,
                        event_ids=[event['event_id']]
                    )


def detect_anomalies(trace_events: List[Dict]) -> List[Dict]:
    """
    Convenience function to detect all anomalies from trace events.
    
    Args:
        trace_events: List of trace event dicts
    
    Returns:
        List of detected anomalies
    """
    detector = AnomalyDetector(trace_events)
    return detector.detect_all()
