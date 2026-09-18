from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


LIVE_INTERFACE = os.getenv(
    "NIDS_LIVE_INTERFACE",
    "",
).strip()

LIVE_FLOW_TIMEOUT = float(
    os.getenv(
        "NIDS_LIVE_FLOW_TIMEOUT",
        "5",
    )
)