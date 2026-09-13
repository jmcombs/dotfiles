from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = PACKAGE_ROOT / "tasks"
CACHE_DIR = Path.home() / ".cache" / "pi-vulcan"
RESULTS_DIR = CACHE_DIR / "results"
SANDBOX_DIR = CACHE_DIR / "sandboxes"
