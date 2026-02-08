from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
QUESTIONS_ROOT = REPO_ROOT / "questions"
LOG_DIR = BACKEND_ROOT / "logs"
LOG_FILE = LOG_DIR / "activity.log"
SNAPSHOTS_DIR = LOG_DIR / "snapshots"

# Execution settings
DOCKER_IMAGE = "python:3.10-slim"
CPU_LIMIT = "1"
MEMORY_LIMIT = "512m"
PIDS_LIMIT = "64"
TIMEOUT_SECONDS = 10
TMPFS_SIZE = "64m"

# Session defaults
DEFAULT_DURATION_MINUTES = 60
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 120
