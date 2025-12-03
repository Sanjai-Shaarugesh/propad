from pathlib import Path
import sys

# Detect if running in Flatpak
if Path("/app/share/ProPad").exists():
    APP_DIR = Path("/app/share/ProPad")
    UI_DIR = APP_DIR / "ui"
    DATA_DIR = APP_DIR / "data"
else:
    # Development mode
    APP_DIR = Path(__file__).parent.parent
    UI_DIR = APP_DIR / "ui"
    DATA_DIR = APP_DIR / "data"

APP_ID = "io.github.sanjai.ProPad"
