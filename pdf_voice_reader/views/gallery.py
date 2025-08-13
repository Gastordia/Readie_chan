from __future__ import annotations
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from ..model.pdfdoc import PDFDoc

class GalleryView(QtWidgets.QWidget):
    opened = QtCore.Signal(Path)
    changed_dir = QtCore.Signal(Path)

    def __init__(self, lib_dir: Path):
        super().__init__()
        self.lib_dir = lib_dir
        self._build()
        self.reload()

    def _build(self):
        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(12,12,12,12); v.setSpacing(10)
        top = QtWidgets.QHBoxLayout(); v.addLayout(top)
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText("Search… title or path")
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search, 1)
        self.btn_open = QtWidgets.QPushButton("Choose Library…")
        self.btn_open.clicked.connect(self.choose_library)
        top.addWidget(self.btn_open)

        self.grid = QtWidgets.QListWidget(); v.addWidget(self.grid, 1)
        self.grid.setViewMode(QtWidgets.QListView.IconMode)
        self.grid.setResizeMode(QtWidgets.QListView.Adjust)
        self.grid.setMovement(QtWidgets.QListView.Static)
        self.grid.setIconSize(QtCore.QSize(160, 210))
        self.grid.setGridSize(QtCore.QSize(180, 250))
        self.grid.setSpacing(12)
        self.grid.setUniformItemSizes(True)
        self.grid.itemActivated.connect(self._open)
        self.grid.itemDoubleClicked.connect(self._open)

    def choose_library(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose PDF Library", str(self.lib_dir))
        if d:
            self.lib_dir = Path(d)
            self.changed_dir.emit(self.lib_dir)
            self.reload()

    def reload(self):
        self.grid.clear()
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        pdfs = sorted(self.lib_dir.rglob("*.pdf"))
        for p in pdfs:
            doc = PDFDoc(p)
            icon = doc.cover_thumb()
            it = QtWidgets.QListWidgetItem(icon, p.stem)
            it.setData(QtCore.Qt.UserRole, str(p))
            self.grid.addItem(it)

    def _filter(self, text: str):
        text = text.lower().strip()
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            show = text in it.text().lower() or text in Path(it.data(QtCore.Qt.UserRole)).name.lower()
            it.setHidden(not show)

    def _open(self, it: QtWidgets.QListWidgetItem):
        self.opened.emit(Path(it.data(QtCore.Qt.UserRole)))
