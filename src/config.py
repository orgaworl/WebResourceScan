"""
Configuration loader — priority: env vars > .env file > defaults.

Supported env vars / .env keys:
  INPUT_FILE  — Path to URL list file (default: urls.txt)
"""

import os
from dotenv import load_dotenv

load_dotenv(override=False)

INPUT_FILE: str = os.environ.get("INPUT_FILE", "urls.txt")
