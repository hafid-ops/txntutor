# Streamlit main entry point
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main controller
from src.ui.controller import main_controller

if __name__ == "__main__":
    main_controller()
