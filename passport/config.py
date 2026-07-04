"""Central config. Loads from .env and decides Cloud vs local (OSS) mode.

Everything that touches Cognee reads from here, so switching between
Cognee Cloud and self-hosted OSS is a single env var (COGNEE_MODE).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env by ABSOLUTE path (project root), so the MCP server works no matter
# which directory an IDE launches it from.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

# "cloud" (primary, uses Cognee Cloud) or "local" (self-hosted OSS fallback)
COGNEE_MODE = os.getenv("COGNEE_MODE", "cloud").lower()

# Cognee Cloud credentials (from platform.cognee.ai -> API Keys)
COGNEE_API_KEY = os.getenv("COGNEE_API_KEY", "")
COGNEE_CLOUD_URL = os.getenv("COGNEE_CLOUD_URL", "")

# Local/OSS only
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Passport server
PASSPORT_API_KEY = os.getenv("PASSPORT_API_KEY", "dev-local-passport-key")
PASSPORT_HOST = os.getenv("PASSPORT_HOST", "127.0.0.1")
PASSPORT_PORT = int(os.getenv("PASSPORT_PORT", "8000"))


def is_cloud() -> bool:
    return COGNEE_MODE == "cloud"


def validate() -> None:
    """Fail fast with a clear message if required config is missing."""
    if is_cloud():
        missing = [
            name
            for name, val in (
                ("COGNEE_API_KEY", COGNEE_API_KEY),
                ("COGNEE_CLOUD_URL", COGNEE_CLOUD_URL),
            )
            if not val or val.startswith("paste-") or "your-tenant" in val
        ]
        if missing:
            raise RuntimeError(
                "Cloud mode is on but these are not set in .env: "
                + ", ".join(missing)
                + ". Get them from platform.cognee.ai -> API Keys."
            )
