# TxnTutor - Transaction Lab

A system that simulates database transactions, records execution traces, detects anomalies, and uses LLM to explain what happened.

## 🎯 What is TxnTutor?

TxnTutor is an educational tool for learning about database transaction concurrency issues. It:

1. **Simulates** concurrent transactions (T1, T2) on PostgreSQL
2. **Logs** every operation (BEGIN, READ, WRITE, COMMIT, ROLLBACK)
3. **Detects** concurrency anomalies using rule-based analysis
4. **Explains** what went wrong using AI (Ollama/Gemini/OpenAI)
5. **Visualizes** execution timeline with interactive Plotly charts

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Ollama (for local LLM) or API keys for Gemini/OpenAI

### Installation

1. **Clone or navigate to the project:**
   ```bash
   cd C:\Users\Pc\Desktop\TxnTutor
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or if using the virtual environment:
   ```bash
   c:/Users/Pc/Desktop/TxnTutor/.venv/Scripts/python.exe -m pip install -r requirements.txt
   ```

3. **Configure environment:**
   
   Copy `.env.example` to `.env` and update:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=txntutor
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   LLM_PROVIDER=ollama
   LLM_MODEL=llama2:latest
   OLLAMA_BASE_URL=http://localhost:11434
   ```

4. **Initialize database:**
   ```bash
   python database/init_db.py
   ```

5. **Start Ollama (for local LLM):**
   ```bash
   ollama serve
   ```

6. **Launch TxnTutor:**
   ```bash
   streamlit run app.py
   ```
   
   Or with full path:
   ```bash
   c:/Users/Pc/Desktop/TxnTutor/.venv/Scripts/streamlit.exe run app.py
   ```

7. **Open browser:**
   The app will open at `http://localhost:8501`

## 📖 Usage

### 1. Choose a Simulator

Select from 6 classic concurrency anomalies:

- **Lost Update** - Both transactions update same record, one update is overwritten
- **Dirty Read** - Read uncommitted data that gets rolled back
- **Non-Repeatable Read** - Same query returns different values within transaction
- **Phantom Read** - Different rows appear in repeated query
- **Write Skew** - Overlapping reads with disjoint writes violate constraints
- **Deadlock** - Circular lock dependency between transactions

### 2. Configure Parameters

- **Scenario Name**: Custom name for this run (e.g., `my_test_1`)
- **T1 Amount**: Value for T1 transaction (e.g., `50`)
- **T2 Amount**: Value for T2 transaction (e.g., `-20`)

### 3. Run Simulation

Click **"Start Run"** to execute:
1. Creates scenario and run records
2. Executes T1 and T2 concurrently
3. Logs all trace events
4. Detects anomalies
5. Generates AI explanation

### 4. Analyze Results

View results in 4 tabs:

- **📈 Timeline**: Interactive visualization of execution
- **📋 Trace Events**: Detailed event log with sequence order
- **⚠️ Anomalies**: Detected issues with descriptions
- **🤖 Explanation**: AI-generated educational explanation

## 🏗️ Architecture

```
TxnTutor/
├── app.py                      # Streamlit entry point
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── .env                        # Environment variables
│
├── database/
│   ├── schema.sql             # PostgreSQL schema
│   └── init_db.py             # Database initialization
│
├── src/
│   ├── database.py            # Connection pooling
│   ├── db_operations.py       # CRUD operations
│   ├── isolation_levels.py    # Isolation level reference
│   │
│   ├── simulator/
│   │   └── transaction_simulator.py  # T1/T2 execution
│   │
│   ├── tracer/
│   │   └── trace_collector.py        # Event logging
│   │
│   ├── detector/
│   │   └── anomaly_detector.py       # Rule-based detection
│   │
│   ├── llm/
│   │   └── llm_service.py            # LLM integration
│   │
│   ├── report/
│   │   └── timeline_view.py          # Visualization
│   │
│   └── ui/
│       └── controller.py              # Streamlit UI
│
├── tests/
│   ├── test_simulator.py      # Simulator tests
│   ├── test_detector.py       # Detector tests
│   ├── test_llm.py            # LLM tests
│   ├── test_timeline.py       # Timeline tests
│   └── verify_db.py           # Database verification
│
└── docs/
    └── ISOLATION_LEVELS.md    # Transaction isolation guide
```

## 🔬 Components

### Transaction Simulator
Executes concurrent T1/T2 with proper isolation levels:
- Lost Update (READ COMMITTED)
- Dirty Read (READ UNCOMMITTED)
- Non-Repeatable Read (READ COMMITTED)
- Phantom Read (READ COMMITTED)
- Write Skew (REPEATABLE READ)
- Deadlock (READ COMMITTED)

### Anomaly Detector
Rule-based detection of:
- Concurrent read/write patterns
- Uncommitted data reads
- Non-repeatable reads
- Phantom rows
- Write skew violations
- Deadlock victims

### LLM Service
Multi-provider support:
- **Ollama** (local, private)
- **Gemini** (Google)
- **OpenAI** (GPT-4)

Generates educational explanations:
1. What happened (step-by-step)
2. Why it's a problem
3. How to prevent it

### Timeline View
Interactive Plotly visualization:
- Color-coded events
- Sequence ordering
- Hover tooltips
- Anomaly highlighting

## 🧪 Testing

Run individual test suites:

```bash
# Test database initialization
python database/init_db.py

# Test transaction simulator
python tests/test_simulator.py

# Test anomaly detector
python tests/test_detector.py

# Test LLM service
python tests/test_llm.py

# Test timeline visualization
python tests/test_timeline.py

# Verify database state
python tests/verify_db.py
```

## 📊 Database Schema

**Tables:**
- `scenario` - Test scenario definitions
- `run` - Execution runs
- `tx` - Individual transactions
- `trace_event` - Operation logs (BEGIN/READ/WRITE/COMMIT)
- `anomaly` - Detected concurrency issues
- `explanation` - LLM-generated explanations

## 🎓 Learning Resources

- [Transaction Isolation Levels](docs/ISOLATION_LEVELS.md) - Comprehensive guide
- [PostgreSQL Documentation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [A Critique of ANSI SQL Isolation Levels](https://www.microsoft.com/en-us/research/publication/a-critique-of-ansi-sql-isolation-levels/)

## 🛠️ Configuration

### Database
Edit `.env`:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=txntutor
DB_USER=postgres
DB_PASSWORD=your_password
```

### LLM Provider

**Ollama (Recommended for privacy):**
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama2:latest
OLLAMA_BASE_URL=http://localhost:11434
```

**Gemini:**
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-pro
LLM_API_KEY=your_gemini_api_key
```

**OpenAI:**
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=your_openai_api_key
```

## 🐛 Troubleshooting

### Database Connection Failed
- Check PostgreSQL is running
- Verify credentials in `.env`
- Test connection: `psql -U postgres -d txntutor`

### LLM Service Not Available
- For Ollama: Check `ollama serve` is running
- Verify model is installed: `ollama list`
- Pull model if needed: `ollama pull llama2`

### Streamlit Port Already in Use
- Change port: `streamlit run app.py --server.port 8502`

## 📝 License

MIT License - Feel free to use for educational purposes.

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [Plotly](https://plotly.com/) - Visualization
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Ollama](https://ollama.ai/) - Local LLM
- [psycopg2](https://www.psycopg.org/) - PostgreSQL adapter

## 📧 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the documentation
3. Test individual components with test scripts

---

**Happy Learning! 🎓**
