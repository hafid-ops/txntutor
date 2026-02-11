# 🚀 TxnTutor Quick Start Guide

## Running the Application

### Option 1: Using Streamlit Command

```bash
streamlit run app.py
```

### Option 2: Using Full Python Path (Windows)

```bash
c:/Users/Pc/Desktop/TxnTutor/.venv/Scripts/streamlit.exe run app.py
```

### Option 3: Using Python Module

```bash
python -m streamlit run app.py
```

## What to Expect

When you run the command, Streamlit will:

1. **Start the server** on port 8501
2. **Open your browser** automatically to `http://localhost:8501`
3. **Display the TxnTutor interface**

You'll see:
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

## Using TxnTutor

### Step 1: Check Connections
- ✅ Database status should show "Connected to PostgreSQL"
- ✅ LLM Service should show "Connected to Ollama"

If not connected:
- **Database**: Check PostgreSQL is running and `.env` has correct credentials
- **LLM**: Check `ollama serve` is running

### Step 2: Configure Simulation
1. **Scenario Name**: Enter a custom name (e.g., `my_test_1`)
2. **Simulator Type**: Choose from dropdown:
   - Lost Update
   - Dirty Read
   - Non-Repeatable Read
   - Phantom Read
   - Write Skew
   - Deadlock
3. **T1 Amount**: Enter value (e.g., `50`)
4. **T2 Amount**: Enter value (e.g., `-20`)
5. **Generate AI Explanation**: Check if you want LLM explanation

### Step 3: Run Simulation
Click **"▶️ Start Run"** button

The app will:
1. Create scenario and run records
2. Execute T1 and T2 concurrently
3. Log trace events
4. Detect anomalies
5. Generate explanation (if enabled)

### Step 4: View Results

**📈 Timeline Tab:**
- Interactive Plotly chart showing execution sequence
- Color-coded events (green=BEGIN/COMMIT, blue=READ, red=WRITE)
- Statistics summary

**📋 Trace Events Tab:**
- Table of all events with sequence order
- Download CSV option

**⚠️ Anomalies Tab:**
- Detected anomalies with descriptions
- Severity levels
- Affected transactions

**🤖 Explanation Tab:**
- AI-generated educational explanation
- What happened, why it's a problem, how to prevent

## Keyboard Shortcuts

- `R` - Rerun the app
- `Ctrl+R` or `Cmd+R` - Rerun
- `Ctrl+K` or `Cmd+K` - Clear cache

## Tips

1. **Try different amounts**: See how transaction values affect outcomes
2. **Compare simulators**: Run multiple scenarios to understand differences
3. **Read explanations**: Learn prevention strategies from AI
4. **Download traces**: Export CSV for analysis

## Troubleshooting

### Port Already in Use
```bash
streamlit run app.py --server.port 8502
```

### Page Not Loading
- Clear browser cache
- Try incognito/private window
- Check firewall settings

### Database Errors
```bash
# Verify database
python tests/verify_db.py

# Reinitialize if needed
python database/init_db.py
```

### LLM Not Working
```bash
# Check Ollama
ollama list

# Test LLM service
python tests/test_llm.py
```

## Stop the Application

Press `Ctrl+C` in the terminal to stop Streamlit

## Next Steps

- Review [README.md](README.md) for full documentation
- Check [ISOLATION_LEVELS.md](docs/ISOLATION_LEVELS.md) for theory
- Run test scripts in `tests/` folder
- Experiment with different scenarios!

---

**Need Help?** Check the README or run test scripts to verify components.
