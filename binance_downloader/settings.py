import os
from pathlib import Path

from dotenv import load_dotenv

# Get path of current file using pathlib
path = Path(__file__).parent.parent.resolve()
print(path)

load_dotenv(path)

# API keys
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
