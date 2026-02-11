# Configuration settings for TxnTutor
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'txntutor')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')
    
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')  # ollama, gemini, openai
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama2:latest')  # Default to llama2 (lower memory requirements)
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')  # For Gemini/OpenAI
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # Transaction Simulator Settings
    DEFAULT_ISOLATION_LEVEL = 'READ COMMITTED'
    TRANSACTION_TIMEOUT_SECONDS = 30
    
    # Available Simulators
    SIMULATORS = {
        'lost_update': 'Lost Update - Both transactions update same record',
        'dirty_read': 'Dirty Read - T1 reads uncommitted data from T2',
        'non_repeatable_read': 'Non-Repeatable Read - T1 reads twice, gets different values',
        'phantom_read': 'Phantom Read - T1 sees different rows in repeated query',
        'write_skew': 'Write Skew - Overlapping reads, disjoint writes',
        'deadlock': 'Deadlock - Mutual wait for locks'
    }
    
    # UI Settings
    APP_TITLE = 'TxnTutor - Transaction Lab'
    PAGE_ICON = '🔬'
    
config = Config()
