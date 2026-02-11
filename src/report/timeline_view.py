# Report / Timeline View
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime

def create_timeline_figure(trace_events: List[Dict], anomalies: List[Dict] = None) -> go.Figure:
    """
    Create an interactive timeline visualization of transaction execution.
    
    Args:
        trace_events: List of trace event dicts from get_trace_events()
        anomalies: Optional list of detected anomalies
    
    Returns:
        Plotly Figure object
    """
    if not trace_events:
        # Empty figure
        fig = go.Figure()
        fig.add_annotation(
            text="No trace events to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    # Prepare data for timeline
    timeline_data = []
    
    # Group events by transaction
    tx_names = sorted(list(set(e['tx_name'] for e in trace_events)))
    
    # Assign row for each transaction
    tx_rows = {tx: i for i, tx in enumerate(tx_names)}
    
    # Color mapping for event types
    event_colors = {
        'BEGIN': '#2ecc71',      # Green
        'READ': '#3498db',       # Blue
        'WRITE': '#e74c3c',      # Red
        'COMMIT': '#27ae60',     # Dark green
        'ROLLBACK': '#c0392b'    # Dark red
    }
    
    # Create timeline entries
    for i, event in enumerate(trace_events):
        tx_name = event['tx_name']
        event_type = event['event_type']
        sequence = event['sequence_order']
        
        # Build description
        if event_type in ['BEGIN', 'COMMIT', 'ROLLBACK']:
            desc = event_type
        elif event_type == 'READ':
            desc = f"READ {event.get('record_key', '')} = {event.get('old_value', '')}"
        elif event_type == 'WRITE':
            desc = f"WRITE {event.get('record_key', '')} = {event.get('new_value', '')} (was {event.get('old_value', '')})"
        else:
            desc = event_type
        
        # Add notes if present
        notes = event.get('notes', '')
        if notes:
            desc += f"<br><i>{notes}</i>"
        
        timeline_data.append({
            'tx_name': tx_name,
            'event_type': event_type,
            'sequence': sequence,
            'description': desc,
            'color': event_colors.get(event_type, '#95a5a6'),
            'row': tx_rows[tx_name],
            'event_id': event['event_id']
        })
    
    # Create figure
    fig = go.Figure()
    
    # Add timeline bars for each event
    for i, data in enumerate(timeline_data):
        # Create a horizontal bar representing the event
        fig.add_trace(go.Bar(
            name=data['event_type'],
            x=[1],  # Width of bar
            y=[data['tx_name']],
            orientation='h',
            marker=dict(
                color=data['color'],
                line=dict(color='white', width=2)
            ),
            text=f"<b>{data['sequence']}: {data['event_type']}</b>",
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate=(
                f"<b>{data['tx_name']}</b><br>" +
                f"Sequence: {data['sequence']}<br>" +
                f"{data['description']}<br>" +
                "<extra></extra>"
            ),
            showlegend=False,
            base=data['sequence'] - 1  # Position based on sequence
        ))
    
    # Highlight anomalies if provided
    if anomalies:
        anomaly_shapes = []
        for anomaly in anomalies:
            event_ids = anomaly.get('event_sequence', [])
            if event_ids:
                # Find sequences for these events
                sequences = [d['sequence'] for d in timeline_data if d['event_id'] in event_ids]
                if sequences:
                    min_seq = min(sequences)
                    max_seq = max(sequences)
                    
                    # Add a background rectangle highlighting the anomaly
                    anomaly_shapes.append(dict(
                        type="rect",
                        xref="x",
                        yref="paper",
                        x0=min_seq - 1.5,
                        x1=max_seq - 0.5,
                        y0=0,
                        y1=1,
                        fillcolor="rgba(255, 0, 0, 0.1)",
                        line=dict(color="red", width=2, dash="dash"),
                        layer="below"
                    ))
        
        fig.update_layout(shapes=anomaly_shapes)
    
    # Update layout
    fig.update_layout(
        title={
            'text': "Transaction Execution Timeline",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c3e50'}
        },
        xaxis=dict(
            title="Sequence Order →",
            showgrid=True,
            gridcolor='lightgray',
            zeroline=False,
            dtick=1
        ),
        yaxis=dict(
            title="Transaction",
            showgrid=True,
            gridcolor='lightgray',
            categoryorder='array',
            categoryarray=tx_names
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=max(400, len(tx_names) * 150),
        barmode='overlay',
        bargap=0.3,
        hovermode='closest',
        margin=dict(l=100, r=50, t=80, b=80)
    )
    
    return fig


def create_event_table(trace_events: List[Dict]) -> pd.DataFrame:
    """
    Create a formatted DataFrame table of trace events.
    
    Args:
        trace_events: List of trace event dicts
    
    Returns:
        pandas DataFrame
    """
    if not trace_events:
        return pd.DataFrame()
    
    table_data = []
    
    for event in trace_events:
        row = {
            'Seq': event['sequence_order'],
            'Tx': event['tx_name'],
            'Event': event['event_type'],
            'Table': event.get('table_name', ''),
            'Key': event.get('record_key', ''),
            'Old Value': event.get('old_value', ''),
            'New Value': event.get('new_value', ''),
            'Notes': event.get('notes', '')
        }
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    return df


def create_anomaly_summary(anomalies: List[Dict]) -> str:
    """
    Create a formatted text summary of detected anomalies.
    
    Args:
        anomalies: List of detected anomaly dicts
    
    Returns:
        Formatted markdown string
    """
    if not anomalies:
        return "✅ **No anomalies detected!** The transactions executed correctly."
    
    summary = f"⚠️ **{len(anomalies)} Anomal{'y' if len(anomalies) == 1 else 'ies'} Detected:**\n\n"
    
    severity_emoji = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🔴',
        'critical': '🔥'
    }
    
    for i, anomaly in enumerate(anomalies, 1):
        severity = anomaly.get('severity', 'medium')
        emoji = severity_emoji.get(severity, '⚠️')
        
        summary += f"### {emoji} {i}. {anomaly['type'].replace('_', ' ').title()}\n\n"
        summary += f"**Severity:** {severity.upper()}\n\n"
        summary += f"**Affected Transactions:** {', '.join(anomaly.get('affected_transactions', []))}\n\n"
        summary += f"**Description:**\n\n{anomaly['description']}\n\n"
        summary += "---\n\n"
    
    return summary


def create_statistics_summary(trace_events: List[Dict], anomalies: List[Dict]) -> Dict:
    """
    Calculate execution statistics.
    
    Args:
        trace_events: List of trace events
        anomalies: List of detected anomalies
    
    Returns:
        Dict with statistics
    """
    if not trace_events:
        return {}
    
    # Count transactions
    tx_names = set(e['tx_name'] for e in trace_events)
    
    # Count event types
    event_types = {}
    for event in trace_events:
        event_type = event['event_type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    # Count commits vs rollbacks
    commits = sum(1 for e in trace_events if e['event_type'] == 'COMMIT')
    rollbacks = sum(1 for e in trace_events if e['event_type'] == 'ROLLBACK')
    
    # Anomaly breakdown
    anomaly_types = {}
    for anomaly in anomalies:
        anom_type = anomaly['type']
        anomaly_types[anom_type] = anomaly_types.get(anom_type, 0) + 1
    
    return {
        'total_events': len(trace_events),
        'transactions': len(tx_names),
        'commits': commits,
        'rollbacks': rollbacks,
        'reads': event_types.get('READ', 0),
        'writes': event_types.get('WRITE', 0),
        'anomalies': len(anomalies),
        'anomaly_types': anomaly_types
    }


def format_statistics(stats: Dict) -> str:
    """
    Format statistics as markdown.
    
    Args:
        stats: Statistics dict from create_statistics_summary()
    
    Returns:
        Formatted markdown string
    """
    if not stats:
        return ""
    
    md = "### 📊 Execution Statistics\n\n"
    
    md += f"- **Total Events:** {stats['total_events']}\n"
    md += f"- **Transactions:** {stats['transactions']}\n"
    md += f"- **Reads:** {stats['reads']}\n"
    md += f"- **Writes:** {stats['writes']}\n"
    md += f"- **Commits:** {stats['commits']}\n"
    md += f"- **Rollbacks:** {stats['rollbacks']}\n"
    md += f"- **Anomalies:** {stats['anomalies']}\n"
    
    if stats['anomaly_types']:
        md += "\n**Anomaly Breakdown:**\n"
        for anom_type, count in stats['anomaly_types'].items():
            md += f"  - {anom_type.replace('_', ' ').title()}: {count}\n"
    
    return md
