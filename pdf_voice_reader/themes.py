from __future__ import annotations
from typing import Dict
from PySide6 import QtCore, QtGui, QtWidgets

# Public API
THEME_NAMES = ["white", "vanilla", "dark", "midnight"]
DEFAULT_THEME = "dark"

def _palette_colors(name: str) -> Dict[str, str]:
    name = (name or "").lower()
    if name == "vanilla":
        return dict(
            window="#F4F1E8", panel="#FFFFFF", text="#1F1F1F",
            base="#FFFFFF", base_alt="#F6F3EA", border="#D8D3C5", accent="#7C6A46",
            highlight_text="#FFFFFF",
        )
    if name == "dark":
        return dict(
            window="#17191D", panel="#1D2026", text="#E8EAED",
            base="#111317", base_alt="#0C0E12", border="#2A2F36", accent="#5E9BFF",
            highlight_text="#0B0E14",
        )
    if name == "midnight":
        return dict(
            window="#0C0F14", panel="#10141B", text="#DDE3EA",
            base="#0A0D12", base_alt="#080B10", border="#1A222C", accent="#2EA3F2",
            highlight_text="#0A0D12",
        )
    # white (default)
    return dict(
        window="#F5F6F8", panel="#FFFFFF", text="#222222",
        base="#FFFFFF", base_alt="#F2F3F5", border="#E6E8EB", accent="#3B7BFF",
        highlight_text="#FFFFFF",
    )

def _build_palette(c: Dict[str, str]) -> QtGui.QPalette:
    pal = QtGui.QPalette()
    # Window / panels
    pal.setColor(QtGui.QPalette.Window, QtGui.QColor(c["window"]))
    pal.setColor(QtGui.QPalette.Base, QtGui.QColor(c["base"]))
    pal.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(c["base_alt"]))
    pal.setColor(QtGui.QPalette.Button, QtGui.QColor(c["panel"]))
    pal.setColor(QtGui.QPalette.Mid, QtGui.QColor(c["border"]))
    # Text
    pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(c["text"]))
    pal.setColor(QtGui.QPalette.Text, QtGui.QColor(c["text"]))
    pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(c["text"]))
    pal.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(c["text"]))
    # Highlights
    pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(c["accent"]))
    pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(c["highlight_text"]))
    return pal

def _style_sheet(c: Dict[str, str]) -> str:
    # Use palette-driven colors; avoid hard-coding light colors
    return f"""
    QMainWindow {{ background: {c['window']}; }}
    QToolBar {{
        background: {c['panel']};
        border: none;
        padding: 6px;
    }}
    QDockWidget {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
    }}
    QDockWidget::title {{
        padding: 6px 8px;
        background: {c['panel']};
    }}
    QListWidget, QPlainTextEdit {{
        background: {c['base']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
    }}
    QLabel, QCheckBox, QRadioButton, QGroupBox, QMenuBar, QMenu, QStatusBar {{
        color: {c['text']};
        background: transparent;
    }}
    QSpinBox, QComboBox, QLineEdit {{
        color: {c['text']};
        background: {c['base']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 2px 6px;
    }}
    QPushButton {{
        color: {c['text']};
        background: {c['panel']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QPushButton:hover {{ border-color: {c['accent']}; }}
    QSlider::groove:horizontal {{
        height: 6px; background: {c['border']}; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        width: 14px; background: {c['accent']}; border-radius: 7px; margin: -5px 0;
    }}
    """

def apply_theme(window: QtWidgets.QMainWindow, name: str) -> None:
    """Apply palette + stylesheet to the whole app."""
    colors = _palette_colors(name)
    pal = _build_palette(colors)
    app = QtWidgets.QApplication.instance()
    if app:
        app.setPalette(pal)
    window.setStyleSheet(_style_sheet(colors))
