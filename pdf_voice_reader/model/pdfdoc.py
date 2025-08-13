from __future__ import annotations
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from PySide6 import QtCore, QtGui
import fitz
from ..config import CACHE_DIR
from ..util import slugify

class PDFDoc(QtCore.QObject):
    """Model: PDF file access, rendering cache, word hit-testing."""
    pageRendered = QtCore.Signal(int)

    def __init__(self, path: Path):
        super().__init__()
        self.path = Path(path)
        self.doc: Optional[fitz.Document] = None
        self.page_count = 0
        self._words_cache: Dict[int, List[Tuple[float,float,float,float, str]]] = {}
        self._pix_cache: Dict[tuple, QtGui.QPixmap] = {}
        self._page_sizes: Dict[int, Tuple[float,float]] = {}

    def open(self):
        if self.doc:
            return
        self.doc = fitz.open(self.path)
        self.page_count = len(self.doc)
        for i in range(self.page_count):
            r = self.doc.load_page(i).rect
            self._page_sizes[i] = (float(r.width), float(r.height))

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
            self.page_count = 0
            self._words_cache.clear()
            self._pix_cache.clear()
            self._page_sizes.clear()

    def page_text(self, i: int) -> str:
        self.open()
        return self.doc.load_page(i).get_text("text").strip()

    def page_words(self, i: int) -> List[Tuple[float,float,float,float,str]]:
        self.open()
        if i in self._words_cache:
            return self._words_cache[i]
        page = self.doc.load_page(i)
        words = page.get_text("words")
        out = [(w[0], w[1], w[2], w[3], w[4]) for w in words]
        self._words_cache[i] = out
        return out

    def page_size(self, i: int) -> Tuple[float,float]:
        self.open()
        return self._page_sizes[i]

    def render_page(self, i: int, scale: float) -> QtGui.QPixmap:
        self.open()
        key = (i, round(scale, 2))
        if key in self._pix_cache:
            return self._pix_cache[key]
        page = self.doc.load_page(i)
        pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        fmt = QtGui.QImage.Format_RGBA8888 if pm.alpha else QtGui.QImage.Format_RGB888
        img = QtGui.QImage(pm.samples, pm.width, pm.height, pm.stride, fmt)
        pix = QtGui.QPixmap.fromImage(img)
        self._pix_cache[key] = pix
        self.pageRendered.emit(i)
        return pix

    def cover_thumb(self, max_w=200) -> QtGui.QIcon:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            out = CACHE_DIR / (slugify(str(self.path)) + f"_{max_w}.png")
            if out.exists():
                return QtGui.QIcon(str(out))
            self.open()
            pm = self.doc.load_page(0).get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            ratio = max_w / pm.width
            pm = self.doc.load_page(0).get_pixmap(matrix=fitz.Matrix(ratio, ratio))
            img = QtGui.QImage(pm.samples, pm.width, pm.height, pm.stride,
                               QtGui.QImage.Format_RGBA8888 if pm.alpha else QtGui.QImage.Format_RGB888)
            img.save(str(out))
            return QtGui.QIcon(str(out))
        except Exception:
            return QtGui.QIcon()
