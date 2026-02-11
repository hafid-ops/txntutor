"""Visual explanations for transaction anomalies"""
import plotly.graph_objects as go
from typing import List, Dict


# Anomaly info database
ANOMALY_INFO = {
    'lost_update': {
        'icon': '💥',
        'title': 'Lost Update',
        'problem': 'Two transactions read the same value, then both write — the first write gets overwritten and lost.',
        'solution': 'REPEATABLE READ or SERIALIZABLE',
        'tip': 'Use SELECT ... FOR UPDATE to lock rows before modifying them.',
        'color': '#FF6B6B'
    },
    'dirty_read': {
        'icon': '👻',
        'title': 'Dirty Read',
        'problem': 'A transaction reads data written by another transaction that hasn\'t committed yet. If it rolls back, the read was invalid.',
        'solution': 'READ COMMITTED or higher',
        'tip': 'Never read uncommitted data — use proper isolation levels.',
        'color': '#A55EEA'
    },
    'non_repeatable_read': {
        'icon': '🔄',
        'title': 'Non-Repeatable Read',
        'problem': 'A transaction reads a row twice and gets different values because another transaction modified it in between.',
        'solution': 'REPEATABLE READ or SERIALIZABLE',
        'tip': 'Lock rows on first read so they can\'t change until your transaction ends.',
        'color': '#FD9644'
    },
    'phantom_read': {
        'icon': '👤',
        'title': 'Phantom Read',
        'problem': 'A transaction runs a range query twice and sees new rows the second time, inserted by another transaction.',
        'solution': 'SERIALIZABLE',
        'tip': 'Use range locks or gap locks to prevent new rows from appearing.',
        'color': '#778CA3'
    },
    'write_skew': {
        'icon': '✏️',
        'title': 'Write Skew',
        'problem': 'Two transactions read overlapping data, then make writes that individually look fine but together violate a constraint.',
        'solution': 'SERIALIZABLE',
        'tip': 'Add explicit database constraints or use SELECT FOR UPDATE.',
        'color': '#FC5C65'
    },
    'deadlock': {
        'icon': '🔒',
        'title': 'Deadlock',
        'problem': 'Two transactions each hold a lock the other needs — neither can proceed.',
        'solution': 'Retry with backoff',
        'tip': 'Always lock resources in a consistent order across all transactions.',
        'color': '#4B6584'
    }
}


def get_anomaly_info(anomaly_type: str) -> Dict:
    """Get anomaly info dict"""
    return ANOMALY_INFO.get(anomaly_type, ANOMALY_INFO['lost_update'])


# SQL code used for each anomaly simulation
ANOMALY_SQL = {
    'lost_update': {
        'T1': """\
-- Transaction 1 (Lost Update)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- T1 reads account A balance
SELECT balance FROM accounts WHERE account_id = 'A';

-- T1 writes new value to A
UPDATE accounts SET balance = {t1}
WHERE account_id = 'A';

COMMIT;  -- This write will be LOST""",

        'T2': """\
-- Transaction 2 (Lost Update)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- T2 also reads account A (same old value)
SELECT balance FROM accounts WHERE account_id = 'A';

-- T2 writes its own value → overwrites T1's update
UPDATE accounts SET balance = {t2}
WHERE account_id = 'A';

COMMIT;  -- T1's update is now lost!"""
    },

    'dirty_read': {
        'T1': """\
-- Transaction 1 (Dirty Read)
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
BEGIN;

SELECT balance FROM accounts WHERE account_id = 'A';

-- T1 writes but does NOT commit
UPDATE accounts SET balance = {t1}
WHERE account_id = 'A';

-- Later T1 rolls back!
ROLLBACK;""",

        'T2': """\
-- Transaction 2 (Dirty Read)
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
BEGIN;

-- T2 reads A BEFORE T1 commits/rollbacks
-- This is the "dirty" read!
SELECT balance FROM accounts WHERE account_id = 'A';
-- Returns {t1} (uncommitted data!)

COMMIT;  -- T2 used data that was rolled back"""
    },

    'non_repeatable_read': {
        'T1': """\
-- Transaction 1 (Non-Repeatable Read)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- First read
SELECT balance FROM accounts WHERE account_id = 'A';
-- Returns 100

-- ... time passes, T2 updates A ...

-- Second read — DIFFERENT value!
SELECT balance FROM accounts WHERE account_id = 'A';
-- Returns {t2} (changed by T2!)

COMMIT;""",

        'T2': """\
-- Transaction 2 (Non-Repeatable Read)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

SELECT balance FROM accounts WHERE account_id = 'A';

-- T2 updates A between T1's two reads
UPDATE accounts SET balance = {t2}
WHERE account_id = 'A';

COMMIT;"""
    },

    'phantom_read': {
        'T1': """\
-- Transaction 1 (Phantom Read)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- First range query
SELECT COUNT(*) FROM accounts
WHERE balance >= 100;
-- Returns N rows

-- ... T2 inserts a new row ...

-- Second range query — new "phantom" row!
SELECT COUNT(*) FROM accounts
WHERE balance >= 100;
-- Returns N+1 rows!

COMMIT;""",

        'T2': """\
-- Transaction 2 (Phantom Read)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- T2 inserts a new account between T1's queries
INSERT INTO accounts
VALUES ('D', {t2}, NOW());

COMMIT;  -- This creates the "phantom" row"""
    },

    'write_skew': {
        'T1': """\
-- Transaction 1 (Write Skew)
-- Constraint: total(A + B) must stay >= 100
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;

-- T1 reads total balance
SELECT SUM(balance) FROM accounts
WHERE account_id IN ('A', 'B');

-- Looks safe → updates A
SELECT balance FROM accounts WHERE account_id = 'A';
UPDATE accounts SET balance = {t1}
WHERE account_id = 'A';

COMMIT;""",

        'T2': """\
-- Transaction 2 (Write Skew)
-- Also checks the SAME constraint
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;

-- T2 reads total (sees old snapshot)
SELECT SUM(balance) FROM accounts
WHERE account_id IN ('A', 'B');

-- Looks safe → updates B
SELECT balance FROM accounts WHERE account_id = 'B';
UPDATE accounts SET balance = {t2}
WHERE account_id = 'B';

COMMIT;  -- Both committed, but constraint may be violated!"""
    },

    'deadlock': {
        'T1': """\
-- Transaction 1 (Deadlock)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- T1 locks account A first
SELECT balance FROM accounts
WHERE account_id = 'A' FOR UPDATE;

-- Then tries to lock B... but T2 holds it!
SELECT balance FROM accounts
WHERE account_id = 'B' FOR UPDATE;  -- ⏳ BLOCKED!

UPDATE accounts SET balance = {t1}
WHERE account_id = 'A';
UPDATE accounts SET balance = {t1}
WHERE account_id = 'B';

COMMIT;  -- or ROLLBACK if deadlock victim""",

        'T2': """\
-- Transaction 2 (Deadlock)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;

-- T2 locks account B first (opposite order!)
SELECT balance FROM accounts
WHERE account_id = 'B' FOR UPDATE;

-- Then tries to lock A... but T1 holds it!
SELECT balance FROM accounts
WHERE account_id = 'A' FOR UPDATE;  -- 💀 DEADLOCK!

UPDATE accounts SET balance = {t2}
WHERE account_id = 'A';
UPDATE accounts SET balance = {t2}
WHERE account_id = 'B';

COMMIT;  -- or ROLLBACK if deadlock victim"""
    }
}


def get_anomaly_sql(anomaly_type: str, t1_amount: int = 50, t2_amount: int = 200) -> Dict[str, str]:
    """Get formatted SQL for an anomaly type with the user's configured amounts."""
    templates = ANOMALY_SQL.get(anomaly_type, ANOMALY_SQL['lost_update'])
    return {
        tx: sql.format(t1=t1_amount, t2=t2_amount)
        for tx, sql in templates.items()
    }


def create_anomaly_diagram(trace_events: List[Dict], anomaly_type: str) -> go.Figure:
    """
    Create a clean Gantt-style diagram showing T1 and T2 operations side by side.
    """
    # Include BEGIN events too
    events = []
    for i, event in enumerate(trace_events):
        etype = event.get('event_type')
        if etype in ('BEGIN', 'READ', 'WRITE', 'COMMIT', 'ROLLBACK'):
            events.append({
                'step': len(events) + 1,
                'tx': event.get('tx_name', 'T?'),
                'action': etype,
                'value': event.get('new_value') or event.get('old_value', ''),
                'key': event.get('record_key', ''),
            })

    if not events:
        fig = go.Figure()
        fig.update_layout(height=120, margin=dict(l=0, r=0, t=0, b=0))
        fig.add_annotation(text="No events to display", showarrow=False)
        return fig

    transactions = sorted(set(e['tx'] for e in events))
    tx_colors = {'T1': '#FF6B6B', 'T2': '#4ECDC4', 'T3': '#45B7D1'}

    action_symbols = {
        'BEGIN':    ('triangle-up',  16),
        'READ':     ('circle',       18),
        'WRITE':    ('square',       20),
        'COMMIT':   ('diamond',      18),
        'ROLLBACK': ('x',           18),
    }

    total_steps = len(events)

    # Position T1 and T2 close together centered
    # Use x positions like 1 and 2 (close together) instead of 0 and 1 (spread apart)
    num_tx = len(transactions)
    spacing = 1.0
    tx_x = {}
    start = -(num_tx - 1) * spacing / 2
    for i, tx in enumerate(transactions):
        tx_x[tx] = start + i * spacing

    fig = go.Figure()

    # Draw vertical connecting lines per transaction
    for tx in transactions:
        tx_events = [e for e in events if e['tx'] == tx]
        xpos = tx_x[tx]
        fig.add_trace(go.Scatter(
            x=[xpos] * len(tx_events),
            y=[-(e['step']) for e in tx_events],
            mode='lines',
            line=dict(color=tx_colors.get(tx, '#888'), width=3, dash='dot'),
            showlegend=False,
            hoverinfo='skip',
        ))

    # Draw markers with labels
    for tx in transactions:
        tx_events = [e for e in events if e['tx'] == tx]
        xpos = tx_x[tx]
        # Labels go left for T1, right for T2
        tx_idx = transactions.index(tx)
        text_side = 'middle left' if tx_idx == 0 else 'middle right'

        for ev in tx_events:
            sym, sz = action_symbols.get(ev['action'], ('circle', 14))
            color = tx_colors.get(tx, '#888')
            if ev['action'] == 'COMMIT':
                color = '#2ECC71'
            elif ev['action'] == 'ROLLBACK':
                color = '#E74C3C'

            # Build label: always show action + value
            if ev['action'] == 'BEGIN':
                label = '  BEGIN  '
            elif ev['action'] in ('COMMIT', 'ROLLBACK'):
                label = f"  {ev['action']}  "
            elif ev['value']:
                label = f"  {ev['action']}({ev['key']}) = {ev['value']}  "
            else:
                label = f"  {ev['action']}({ev['key']})  "

            fig.add_trace(go.Scatter(
                x=[xpos],
                y=[-(ev['step'])],
                mode='markers+text',
                marker=dict(size=sz, color=color, symbol=sym,
                            line=dict(width=2, color='rgba(255,255,255,0.7)')),
                text=label,
                textposition=text_side,
                textfont=dict(size=12, color='#eee', family='monospace'),
                hovertemplate=(
                    f"<b>{tx}</b> Step {ev['step']}<br>"
                    f"{ev['action']} [{ev['key']}] = {ev['value']}<extra></extra>"
                ),
                showlegend=False,
            ))

    # Legend entries
    for tx in transactions:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers+lines',
            marker=dict(size=10, color=tx_colors.get(tx, '#888')),
            line=dict(color=tx_colors.get(tx, '#888'), width=2),
            name=tx,
        ))

    # Calculate height based on events
    chart_height = max(300, total_steps * 50 + 100)

    # X-axis range: centered with padding
    x_min = min(tx_x.values()) - 1.5
    x_max = max(tx_x.values()) + 1.5

    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=50, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        xaxis=dict(
            ticktext=transactions,
            tickvals=[tx_x[tx] for tx in transactions],
            tickfont=dict(size=14, color='#fff'),
            showgrid=False, zeroline=False,
            side='top',
            range=[x_min, x_max],
            fixedrange=True,
        ),
        yaxis=dict(
            ticktext=[f"Step {i+1}" for i in range(total_steps)],
            tickvals=[-(i+1) for i in range(total_steps)],
            tickfont=dict(size=10),
            showgrid=True,
            gridcolor='rgba(128,128,128,0.12)',
            zeroline=False,
            fixedrange=True,
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.06, xanchor='center', x=0.5),
        hovermode='closest',
        dragmode=False,
    )

    return fig


def render_problem_solution(st_module, anomaly_type: str):
    """
    Render the problem/solution card using native Streamlit components.
    Call this with `import streamlit as st` and pass `st` as st_module.
    """
    info = get_anomaly_info(anomaly_type)

    # Problem row
    col_icon, col_text = st_module.columns([1, 8])
    with col_icon:
        st_module.markdown(f"<span style='font-size:48px'>{info['icon']}</span>", unsafe_allow_html=True)
    with col_text:
        st_module.markdown(f"**{info['title']}**")
        st_module.error(f"⚠️ **Problem:** {info['problem']}")

    # Solution row
    col1, col2 = st_module.columns(2)
    with col1:
        st_module.success(f"✅ **Fix:** Use **{info['solution']}** isolation level")
    with col2:
        st_module.info(f"💡 **Tip:** {info['tip']}")
