from __future__ import annotations
import os
from pathlib import Path

APP_NAME   = "PDF Voice Reader"
STATE_FILE = Path.home() / ".pdf_voice_gui_state.json"
DEFAULT_LIB = Path(os.environ.get("PDF_LIBRARY", "./library")).expanduser()
CACHE_DIR   = Path.home() / ".cache" / "pdf_voice_reader" / "thumbs"
VOICE_DIRS  = [
    os.path.expanduser("~/.local/share/piper/voices"),
    "/usr/share/piper/voices",
    "/usr/local/share/piper/voices",
]

# Virtualization
WINDOW_SIZE    = 10   # pages rendered at once
PRELOAD_MARGIN = 2    # buffer around window
MIN_SCALE      = 0.6
MAX_SCALE      = 3.0


THEMES = {
    "white": {
        "palette": "light",
        "stylesheet": """
            QToolBar { background: #ffffff; border: none; padding: 6px; }
            QMainWindow { background: #f5f6f8; }
            QListWidget, QDockWidget, QPlainTextEdit {
                background: #ffffff; border: 1px solid #e6e8eb; border-radius: 8px;
            }
            QLabel, QCheckBox, QRadioButton, QSpinBox, QComboBox, QSlider, QPushButton { color: #222; }
            QPushButton { background: #ffffff; border: 1px solid #dfe3e6; border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { background: #f0f3f6; }
        """,
    },
    "vanilla": {
        "palette": "light",
        "stylesheet": """
            QToolBar { background: #f7f3e8; border: none; padding: 6px; }
            QMainWindow { background: #f3efe4; }
            QListWidget, QDockWidget, QPlainTextEdit {
                background: #fffaf0; border: 1px solid #e3daca; border-radius: 8px;
            }
            QLabel, QCheckBox, QRadioButton, QSpinBox, QComboBox, QSlider, QPushButton { color: #3a2e1f; }
            QPushButton { background: #fffaf0; border: 1px solid #e3daca; border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { background: #f1e8d7; }
        """,
    },
    "dark": {
        "palette": "dark",
        "stylesheet": """
            QToolBar { background: #2a2e32; border: none; padding: 6px; }
            QMainWindow { background: #1f2327; }
            QListWidget, QDockWidget, QPlainTextEdit {
                background: #2a2e32; border: 1px solid #394148; border-radius: 8px;
            }
            QLabel, QCheckBox, QRadioButton, QSpinBox, QComboBox, QSlider, QPushButton { color: #e6e6e6; }
            QPushButton { background: #2a2e32; border: 1px solid #394148; border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { background: #33393f; }
        """,
    },
    "midnight": {
        "palette": "dark",
        "stylesheet": """
            QToolBar { background: #0f1316; border: none; padding: 6px; }
            QMainWindow { background: #0b0e10; }
            QListWidget, QDockWidget, QPlainTextEdit {
                background: #11161a; border: 1px solid #1d252b; border-radius: 8px;
            }
            QLabel, QCheckBox, QRadioButton, QSpinBox, QComboBox, QSlider, QPushButton { color: #d8dde1; }
            QPushButton { background: #11161a; border: 1px solid #1d252b; border-radius: 8px; padding: 6px 10px; }
            QPushButton:hover { background: #161c21; }
        """,
    },
}
DEFAULT_THEME = "white"
