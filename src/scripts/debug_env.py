from pathlib import Path
from dotenv import load_dotenv
import os
import sys

# Simulate the structure in llm_kg_extractor.py
# It is in src/ingestion/, so parent.parent from there is src/
# BUT wait. llm_kg_extractor.py is in src/ingestion/llm_kg_extractor.py
# Path(__file__).resolve() -> /abs/path/to/src/ingestion/llm_kg_extractor.py
# .parent -> /abs/path/to/src/ingestion
# .parent -> /abs/path/to/src
# .parent / ".env" -> /abs/path/to/src/.env

print(f"Current working directory: {os.getcwd()}")

# Replicate code from llm_kg_extractor.py (adjusted for this script's location)
# This script is in src/scripts/debug_env.py
# So parent.parent is src/
script_path = Path(__file__).resolve()
print(f"Script path: {script_path}")

target_env = script_path.parent.parent / ".env"
print(f"Target .env path: {target_env}")
print(f"Target .env exists: {target_env.exists()}")
print(f"Contents of {script_path.parent.parent}:")
try:
    print(list(script_path.parent.parent.iterdir()))
except Exception as e:
    print(e)

# Try loading
load_dotenv(target_env)
print(f"GEMINI_API_KEY in env: {os.environ.get('GEMINI_API_KEY')}")

# Also check if just 'load_dotenv()' finds it if we don't specify path?
# Typically load_dotenv() looks in CWD or parents. CWD is root. root doesn't have .env (it is in src/.env)
