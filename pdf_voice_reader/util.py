from __future__ import annotations
import shutil, hashlib, json
from pathlib import Path
from typing import List
from .config import DEFAULT_LIB, VOICE_DIRS
from PySide6 import QtGui, QtWidgets
from .config import THEMES

def ensure_cmd(cmd: str) -> None:
    import shutil
    if shutil.which(cmd) is None:
        raise RuntimeError(f"'{cmd}' not found in PATH. Please install it.")


def map_wpm_to_length_scale(wpm: int, baseline: int = 170) -> float:
    if wpm <= 0:
        return 1.0
    scale = baseline / float(wpm)
    return max(0.6, min(2.0, scale))


def human_path(p: Path) -> str:
    try:
        return str(p.relative_to(DEFAULT_LIB))
    except Exception:
        return str(p)


def slugify(s: str) -> str:
    h = hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:10]
    base = "".join(c for c in s if c.isalnum() or c in ("-","_"," ")).strip().replace(" ", "_")
    return f"{base[:50]}_{h}" if base else h


def chunk_text(text: str, target_len: int = 420) -> List[str]:
    """Small chunks (~2–5s) so pause/stop feel instant and resume is sane."""
    text = text.strip()
    if not text:
        return []
    out: List[str] = []
    parts: List[str] = []
    buf: List[str] = []
    for tok in text.replace("\b", " ").split(" "):
        buf.append(tok)
        if tok.endswith(('.', '!', '?')):
            parts.append(" ".join(buf))
            buf = []
    if buf:
        parts.append(" ".join(buf))
    cur: List[str] = []
    n = 0
    for p in parts:
        if n + len(p) <= target_len or not cur:
            cur.append(p)
            n += len(p) + 1
        else:
            out.append(" ".join(cur))
            cur = [p]
            n = len(p)
    if cur:
        out.append(" ".join(cur))
    return out


def validate_piper_model(onnx_path: str) -> None:
    onnx = Path(onnx_path).expanduser()
    if not onnx.exists():
        raise FileNotFoundError(f"Missing Piper model: {onnx}")
    cfg = onnx.with_suffix(onnx.suffix + ".json")
    if not cfg.exists():
        raise FileNotFoundError(f"Missing Piper config JSON next to model: {cfg}")
    try:
        json.load(open(cfg, "r", encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Invalid Piper JSON: {cfg}Tip: re-download with curl -L and ?download=true.{e}")


def scan_voice_models() -> List[str]:
    voices = []
    for d in VOICE_DIRS:
        p = Path(d)
        if not p.exists():
            continue
        for onnx in p.glob("*.onnx"):
            if (onnx.parent / (onnx.name + ".json")).exists():
                voices.append(str(onnx))
    return sorted(set(voices))

def _apply_palette(app: QtWidgets.QApplication, mode: str):
    """Set a sane base palette for the whole app."""
    if mode == "dark":
        pal = QtGui.QPalette()
        # Window surfaces
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor("#181c20"))
        pal.setColor(QtGui.QPalette.Base,   QtGui.QColor("#14181c"))
        pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#1b2025"))
        # Text
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#e6e6e6"))
        pal.setColor(QtGui.QPalette.Text,       QtGui.QColor("#e6e6e6"))
        pal.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor("#9aa4ad"))
        # Buttons/links/highlight
        pal.setColor(QtGui.QPalette.Button,     QtGui.QColor("#2a2e32"))
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#e6e6e6"))
        pal.setColor(QtGui.QPalette.Link,       QtGui.QColor("#4aa3ff"))
        pal.setColor(QtGui.QPalette.Highlight,        QtGui.QColor("#4a90e2"))
        pal.setColor(QtGui.QPalette.HighlightedText,  QtGui.QColor("#ffffff"))
        app.setPalette(pal)
    else:
        # ← This fully resets after a dark theme
        app.setPalette(app.style().standardPalette())

def _set_dark_palette(app: QtWidgets.QApplication):
    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.Window,            QtGui.QColor("#181c20"))
    pal.setColor(QtGui.QPalette.Base,              QtGui.QColor("#14181c"))
    pal.setColor(QtGui.QPalette.AlternateBase,     QtGui.QColor("#1b2025"))
    pal.setColor(QtGui.QPalette.WindowText,        QtGui.QColor("#e6e6e6"))
    pal.setColor(QtGui.QPalette.Text,              QtGui.QColor("#e6e6e6"))
    pal.setColor(QtGui.QPalette.PlaceholderText,   QtGui.QColor("#9aa4ad"))
    pal.setColor(QtGui.QPalette.Button,            QtGui.QColor("#2a2e32"))
    pal.setColor(QtGui.QPalette.ButtonText,        QtGui.QColor("#e6e6e6"))
    pal.setColor(QtGui.QPalette.Link,              QtGui.QColor("#4aa3ff"))
    pal.setColor(QtGui.QPalette.Highlight,         QtGui.QColor("#4a90e2"))
    pal.setColor(QtGui.QPalette.HighlightedText,   QtGui.QColor("#ffffff"))
    app.setPalette(pal)

def apply_theme(window: QtWidgets.QWidget, theme_name: str):
    """
    Reset palette & stylesheets first, then apply requested theme.
    This avoids 'dark colors sticking' when returning to light themes.
    """
    app = QtWidgets.QApplication.instance()

    # 1) FULL RESET
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("")
    window.setStyleSheet("")

    # 2) APPLY THEME
    cfg = THEMES.get(theme_name, THEMES["white"])
    if cfg.get("palette", "light") == "dark":
        _set_dark_palette(app)           # palette for dark mode
    else:
        app.setPalette(app.style().standardPalette())  # ensure light palette

    # Stylesheet at the *application* level so menus/tooltips/docks follow
    app.setStyleSheet(cfg.get("stylesheet", ""))
