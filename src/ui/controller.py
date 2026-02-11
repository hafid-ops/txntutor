# Web UI / Controller (Streamlit)
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import config
from src.simulator import TransactionSimulator
from src.detector import detect_anomalies
from src.llm import get_llm_service
from src.report import (
    create_timeline_figure,
    create_event_table,
    create_anomaly_summary,
    create_statistics_summary,
    format_statistics
)
from src.report.visual_explainer import (
    create_anomaly_diagram,
    render_problem_solution,
    get_anomaly_sql
)
from src.db_operations import (
    get_or_create_scenario,
    get_all_scenarios,
    create_run,
    complete_run,
    get_trace_events,
    get_run_details,
    get_recent_runs,
    insert_anomaly,
    insert_explanation
)
from src.database import test_connection
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def show_header():
    """Display application header"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🔬 TxnTutor")
        st.caption("Learn database concurrency by simulating real anomalies")
    
    with col2:
        # Quick stats
        db_ok, _ = test_connection()
        llm = get_llm_service()
        llm_ok, _ = llm.test_connection()
        
        st.metric("Status", "🟢 Ready" if db_ok else "🔴 Error", 
                 delta="Online" if db_ok and llm_ok else "Limited")


def show_connection_status():
    """Check and display database and LLM connection status"""
    db_ok, db_msg = test_connection()
    llm = get_llm_service()
    llm_ok, llm_msg = llm.test_connection()
    
    return db_ok, llm_ok


def show_simulator_config():
    """Display simulator configuration in sidebar"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Simulator type selection with descriptions
        simulator_options = {
            "lost_update": "💥 Lost Update",
            "dirty_read": "👻 Dirty Read",
            "non_repeatable_read": "🔄 Non-Repeatable Read",
            "phantom_read": "👤 Phantom Read",
            "write_skew": "✏️ Write Skew",
            "deadlock": "🔒 Deadlock"
        }
        
        simulator_type = st.selectbox(
            "Choose Anomaly",
            options=list(simulator_options.keys()),
            format_func=lambda x: simulator_options[x],
            help="Select which concurrency anomaly to demonstrate"
        )
        
        # Show description
        with st.expander("ℹ️ About This Anomaly", expanded=False):
            st.caption(config.SIMULATORS[simulator_type])
        
        st.divider()
        
        # Transaction amounts
        st.subheader("Transaction Amounts")
        
        t1_amount = st.number_input(
            "T1 Amount",
            min_value=1,
            max_value=10000,
            value=50,
            step=10,
            help="Value that Transaction 1 will write"
        )
        
        t2_amount = st.number_input(
            "T2 Amount",
            min_value=1,
            max_value=10000,
            value=200,
            step=10,
            help="Value that Transaction 2 will write"
        )
        
        st.divider()
        
        # Scenario name
        scenario_name = st.text_input(
            "Run Name (optional)",
            value="",
            placeholder="my_test_run",
            help="Custom name for this simulation"
        )
        
        if not scenario_name:
            scenario_name = f"{simulator_type}_{int(time.time())}"
        
        # LLM toggle
        llm = get_llm_service()
        llm_ok, _ = llm.test_connection()
        generate_explanation = st.toggle(
            "🤖 AI Explanation",
            value=llm_ok,
            help="Generate AI-powered explanation of results"
        )
        
        st.divider()
        
        # Big run button
        run_button = st.button(
            "▶️ Run Simulation",
            type="primary",
            use_container_width=True
        )
    
    return scenario_name, simulator_type, t1_amount, t2_amount, generate_explanation, run_button


def run_simulation(scenario_name, simulator_type, t1_amount, t2_amount, generate_explanation=True):
    """
    Execute the complete simulation workflow
    
    Returns:
        Dict with run_id, results, trace_events, anomalies, explanation
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Create scenario and run
        status_text.text("📝 Creating scenario and run...")
        progress_bar.progress(10)
        
        scenario_id = get_or_create_scenario(
            name=scenario_name,
            description=f"Custom scenario: {simulator_type}",
            isolation_level=config.DEFAULT_ISOLATION_LEVEL
        )
        
        run_id = create_run(
            scenario_id=scenario_id,
            notes=f"Simulator: {simulator_type}, T1={t1_amount}, T2={t2_amount}"
        )
        
        # Step 2: Run simulator
        status_text.text("🔄 Executing concurrent transactions T1 and T2...")
        progress_bar.progress(30)
        
        simulator = TransactionSimulator(run_id)
        results = simulator.run_simulator(simulator_type, t1_amount, t2_amount)
        
        # Step 3: Get trace events
        status_text.text("📋 Retrieving trace events...")
        progress_bar.progress(50)
        
        trace_events = get_trace_events(run_id)
        
        # Step 4: Detect anomalies
        status_text.text("🔍 Analyzing trace for anomalies...")
        progress_bar.progress(60)
        
        anomalies = detect_anomalies(trace_events)
        
        # Insert anomalies into database
        anomaly_ids = []
        for anomaly in anomalies:
            anomaly_id = insert_anomaly(
                run_id=run_id,
                anomaly_type=anomaly['type'],
                description=anomaly['description'],
                severity=anomaly['severity'],
                affected_transactions=anomaly['affected_transactions'],
                event_sequence=anomaly['event_sequence']
            )
            anomaly_ids.append(anomaly_id)
        
        # Step 5: Generate LLM explanation (if anomalies detected and LLM available)
        explanation = None
        if anomalies and generate_explanation:
            status_text.text("🤖 Generating AI explanation...")
            progress_bar.progress(80)
            
            llm = get_llm_service()
            
            # Generate explanation for the first anomaly
            first_anomaly = anomalies[0]
            run_details = get_run_details(run_id)
            
            llm_result = llm.generate_explanation(
                anomaly_type=first_anomaly['type'],
                trace_events=trace_events,
                anomaly_description=first_anomaly['description'],
                context={'isolation_level': run_details.get('isolation_level')}
            )
            
            explanation = llm_result['explanation']
            
            # Insert explanation into database
            if anomaly_ids:
                insert_explanation(
                    anomaly_id=anomaly_ids[0],
                    llm_model=llm_result['model'],
                    explanation_text=explanation,
                    tokens_used=llm_result.get('tokens_used'),
                    generation_time_ms=llm_result.get('generation_time_ms')
                )
        
        # Step 6: Complete run
        status_text.text("✅ Completing run...")
        progress_bar.progress(100)
        
        complete_run(run_id, 'completed')
        
        status_text.text("✅ Simulation complete!")
        time.sleep(0.5)
        
        progress_bar.empty()
        status_text.empty()
        
        return {
            'run_id': run_id,
            'results': results,
            'trace_events': trace_events,
            'anomalies': anomalies,
            'explanation': explanation,
            'simulator_type': simulator_type,
            't1_amount': t1_amount,
            't2_amount': t2_amount,
        }
    
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Simulation failed: {str(e)}")
        logger.error(f"Simulation error: {e}", exc_info=True)
        return None


def display_results(run_data):
    """Display simulation results"""
    if not run_data:
        return
    
    run_id = run_data['run_id']
    results = run_data['results']
    trace_events = run_data['trace_events']
    anomalies = run_data['anomalies']
    explanation = run_data['explanation']
    
    # Quick summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Run ID", f"#{run_id}", delta="Completed")
    
    with col2:
        st.metric("Events", len(trace_events), delta=f"{len([e for e in trace_events if e.get('event_type') == 'WRITE'])} writes")
    
    with col3:
        anomaly_count = len(anomalies)
        st.metric("Anomalies", anomaly_count, 
                 delta="Detected" if anomaly_count > 0 else "Clean",
                 delta_color="inverse" if anomaly_count > 0 else "normal")
    
    with col4:
        if results and 'final_balance' in results:
            st.metric("Final Balance", results['final_balance'])
        elif results:
            st.metric("Status", list(results.values())[0])
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Timeline View", "⚠️ Anomalies", "🤖 AI Explanation"])
    
    with tab1:
        # Create and display timeline
        fig = create_timeline_figure(trace_events, anomalies)
        st.plotly_chart(fig, use_container_width=True)
        
        # Collapsible sections for details
        with st.expander("📋 View Detailed Trace Events", expanded=False):
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                event_filter = st.multiselect(
                    "Filter by Event Type",
                    options=['BEGIN', 'READ', 'WRITE', 'COMMIT', 'ROLLBACK'],
                    default=['BEGIN', 'READ', 'WRITE', 'COMMIT', 'ROLLBACK']
                )
            
            with col2:
                tx_filter = st.multiselect(
                    "Filter by Transaction",
                    options=list(set([e.get('tx_name', 'T?') for e in trace_events])),
                    default=list(set([e.get('tx_name', 'T?') for e in trace_events]))
                )
            
            # Filter events
            filtered_events = [
                e for e in trace_events 
                if e.get('event_type') in event_filter and e.get('tx_name', 'T?') in tx_filter
            ]
            
            df = create_event_table(filtered_events)
            st.dataframe(df, use_container_width=True, hide_index=True, height=300)
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"trace_run_{run_id}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with st.expander("📊 Statistics", expanded=False):
            stats = create_statistics_summary(trace_events, anomalies)
            st.markdown(format_statistics(stats))
    
    with tab2:
        if anomalies:
            first_anomaly = anomalies[0]
            
            # Highlighted anomaly card
            st.error(f"🚨 {first_anomaly['type'].replace('_', ' ').title()} Detected")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**What Happened:**")
                st.info(first_anomaly['description'])
            
            with col2:
                st.markdown(f"**Severity**")
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                st.markdown(f"### {severity_emoji.get(first_anomaly['severity'], '⚪')} {first_anomaly['severity'].upper()}")
                
                st.markdown(f"**Affected:**")
                st.caption(', '.join(first_anomaly['affected_transactions']))
            
            # Additional anomaly details
            if len(anomalies) > 1:
                with st.expander(f"View {len(anomalies)-1} more anomalies", expanded=False):
                    for anomaly in anomalies[1:]:
                        st.markdown(f"- **{anomaly['type']}**: {anomaly['description']}")
        else:
            st.success("🎉 No anomalies detected! The transactions executed correctly.")
    
    with tab3:
        if anomalies:
            first_anomaly = anomalies[0]
            
            # Problem / Solution using native Streamlit
            render_problem_solution(st, first_anomaly['type'])
            
            st.divider()
            
            # Visual diagram of the transaction flow — centered in a narrower column
            _, col_chart, _ = st.columns([1, 3, 1])
            with col_chart:
                fig = create_anomaly_diagram(trace_events, first_anomaly['type'])
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            # SQL Code used for this anomaly
            anomaly_type = first_anomaly['type']
            t1_val = run_data.get('t1_amount', 50)
            t2_val = run_data.get('t2_amount', 200)
            sql_code = get_anomaly_sql(anomaly_type, t1_val, t2_val)
            
            with st.expander("🗄️ SQL Code Used", expanded=True):
                sql_col1, sql_col2 = st.columns(2)
                with sql_col1:
                    st.markdown("**Transaction 1**")
                    st.code(sql_code['T1'], language='sql')
                with sql_col2:
                    st.markdown("**Transaction 2**")
                    st.code(sql_code['T2'], language='sql')
            
            st.divider()
            
            # AI Explanation
            if explanation:
                with st.expander("🤖 AI Explanation", expanded=True):
                    st.markdown(explanation)
            else:
                if st.button("🤖 Generate AI Explanation", type="primary"):
                    with st.spinner("Generating..."):
                        llm = get_llm_service()
                        run_details = get_run_details(run_id)
                        
                        llm_result = llm.generate_explanation(
                            anomaly_type=first_anomaly['type'],
                            trace_events=trace_events,
                            anomaly_description=first_anomaly['description'],
                            context={'isolation_level': run_details.get('isolation_level')}
                        )
                        
                        st.session_state['last_run']['explanation'] = llm_result['explanation']
                        st.rerun()
        else:
            st.success("✨ No anomalies detected! Transactions executed correctly.")


def show_recent_runs():
    """Display recent simulation runs with interactive cards"""
    with st.expander("📜 Recent Runs", expanded=False):
        recent = get_recent_runs(limit=5)
        
        if recent:
            for run in recent:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**#{run['run_id']}**")
                    
                    with col2:
                        st.text(run['scenario_name'][:30])
                    
                    with col3:
                        status_emoji = "✅" if run['status'] == 'completed' else "⏳"
                        st.text(f"{status_emoji} {run['status']}")
                    
                    with col4:
                        if run['duration_ms']:
                            st.text(f"{run['duration_ms']:.0f}ms")
                    
                    with col5:
                        if st.button("🔄", key=f"reload_{run['run_id']}", help="Load this run"):
                            # Load this run's data
                            st.toast(f"Loading run #{run['run_id']}...", icon="⏳")
                    
                    st.divider()
        else:
            st.info("No previous runs found. Start your first simulation!")


def show_help():
    """Display help information in sidebar"""
    with st.sidebar:
        with st.expander("❓ Quick Help", expanded=False):
            st.markdown("""
            **How It Works:**
            1. Select an anomaly type
            2. Adjust transaction amounts
            3. Click Run Simulation
            4. Explore results in tabs
            
            **Anomaly Types:**
            - 💥 **Lost Update**: Concurrent writes overwrite each other
            - 👻 **Dirty Read**: Reading uncommitted data
            - 🔄 **Non-Repeatable Read**: Same query, different results
            - 👤 **Phantom Read**: New rows appear in repeated queries
            - ✏️ **Write Skew**: Overlapping reads, disjoint writes
            - 🔒 **Deadlock**: Circular lock dependency
            """)
        
        # System info
        with st.expander("⚙️ System Info", expanded=False):
            st.caption(f"**Database:** {config.DB_NAME}")
            st.caption(f"**LLM Model:** {config.LLM_MODEL}")
            st.caption(f"**Provider:** {config.LLM_PROVIDER}")


def main_controller():
    """Main Streamlit controller function"""
    
    # Page config
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header
    show_header()
    
    # Check connections silently
    db_ok, llm_ok = show_connection_status()
    
    if not db_ok:
        st.error("⚠️ Cannot connect to database. Please check your configuration in .env file.")
        with st.expander("Configuration Help"):
            st.code(f"""
DB_HOST={config.DB_HOST}
DB_PORT={config.DB_PORT}
DB_NAME={config.DB_NAME}
DB_USER={config.DB_USER}
            """)
        st.stop()
    
    # Sidebar configuration
    scenario_name, simulator_type, t1_amount, t2_amount, generate_explanation, run_button = show_simulator_config()
    
    # Help in sidebar
    show_help()
    
    # Execute simulation when button clicked
    if run_button:
        with st.spinner("🚀 Running simulation..."):
            run_data = run_simulation(
                scenario_name=scenario_name,
                simulator_type=simulator_type,
                t1_amount=t1_amount,
                t2_amount=t2_amount,
                generate_explanation=generate_explanation
            )
            
            if run_data:
                # Store in session state for persistence
                st.session_state['last_run'] = run_data
                st.success("✅ Simulation completed!")
    
    # Display results (from current run or session state)
    if 'last_run' in st.session_state:
        st.divider()
        display_results(st.session_state['last_run'])
    else:
        # Welcome message when no simulation has run yet
        st.info("👋 Welcome! Configure your simulation in the sidebar and click 'Run Simulation' to begin.")
        
        # Show example scenarios
        with st.expander("🎯 Example Scenarios to Try", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                **💥 Lost Update**
                - T1 Amount: +50
                - T2 Amount: -20
                - Result: One update gets lost
                """)
            
            with col2:
                st.markdown("""
                **👻 Dirty Read**
                - T1 Amount: +100
                - T2 Amount: -50
                - Result: Read uncommitted data
                """)
            
            with col3:
                st.markdown("""
                **🔒 Deadlock**
                - T1 Amount: +30
                - T2 Amount: +30
                - Result: Circular lock wait
                """)
    
    # Recent runs at bottom
    st.divider()
    show_recent_runs()


if __name__ == "__main__":
    main_controller()
