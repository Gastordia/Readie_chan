from __future__ import annotations
import sys
from PySide6 import QtCore, QtWidgets
from .views.main_window import MainWindow
from .config import APP_NAME

def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.setWindowTitle(APP_NAME)
    w.showMaximized()
    sys.exit(app.exec())
