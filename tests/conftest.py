import sys
from pathlib import Path
import pytest

# 1. Force the root directory into sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 2. Mock environment variables for testing
import os
os.environ["DATABASE_URL"] = "postgresql://actionflow:dev123@localhost:5432/actionflow_test"
os.environ["HOTEL_API_KEY"] = "test_key"
os.environ["HOTEL_API_HOST"] = "test.p.rapidapi.com"

# 3. Now imports will work across all test files
try:
    from app.core.database import Base, get_sync_engine
except ImportError:
    print("Could not import database. Check if database.py is in the root.")