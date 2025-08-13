from __future__ import annotations
from typing import Optional, List, Dict
from PySide6 import QtCore, QtWidgets, QtGui

from ..model.pdfdoc import PDFDoc
from ..config import MIN_SCALE, MAX_SCALE, WINDOW_SIZE, PRELOAD_MARGIN
from .page import PageWidget


class ContinuousPDFView(QtWidgets.QScrollArea):
    """Virtualized, continuous PDF viewer with lazy rendering (no resume logic)."""

    wordClicked = QtCore.Signal(int, int)
    firstVisibleChanged = QtCore.Signal(int)  # keep only for spinner sync

    def __init__(self):
        super().__init__()

        self.doc: Optional[PDFDoc] = None

        self.container = QtWidgets.QWidget()
        self.vbox = QtWidgets.QVBoxLayout(self.container)
        self.vbox.setContentsMargins(20, 20, 20, 20)
        self.vbox.setSpacing(16)
        self.setWidget(self.container)
        self.setWidgetResizable(True)

        self.pages: List[PageWidget] = []
        self.scale: float = 1.2
        self.fit_mode: Optional[str] = "width"
        self.loaded: Dict[int, bool] = {}
        self._last_first_visible: int = 0

        self.viewport().installEventFilter(self)
        self.verticalScrollBar().valueChanged.connect(
            lambda *_: QtCore.QTimer.singleShot(0, self._render_visible)
        )
        self.horizontalScrollBar().valueChanged.connect(
            lambda *_: QtCore.QTimer.singleShot(0, self._render_visible)
        )

    # ---------- Public API ----------
    def set_document(self, doc: PDFDoc):
        self.doc = doc

        for p in self.pages:
            p.deleteLater()
        self.pages.clear()
        self.loaded.clear()

        for i in range(doc.page_count):
            pw = PageWidget(doc, i)
            pw.wordClicked.connect(self.wordClicked)
            self.vbox.addWidget(pw)
            self.pages.append(pw)

        self.vbox.addStretch(1)
        self._refresh_placeholders()
        QtCore.QTimer.singleShot(0, self._render_visible)

    def set_fit_mode(self, mode: Optional[str]):
        self.fit_mode = mode
        self._refresh_placeholders()
        self._render_visible()

    def set_zoom(self, scale: float):
        self.scale = max(MIN_SCALE, min(MAX_SCALE, float(scale)))
        self.fit_mode = None
        self._refresh_placeholders()
        self._render_visible()

    def go_to_page(self, page_no: int):
        if not self.pages:
            return
        page_no = max(1, min(page_no, len(self.pages)))
        w = self.pages[page_no - 1]
        self.verticalScrollBar().setValue(w.pos().y())
        self._render_visible()

    # ---------- Events ----------
    def eventFilter(self, obj, ev):
        if obj is self.viewport() and ev.type() in (
            QtCore.QEvent.Resize,
            QtCore.QEvent.Paint,
            QtCore.QEvent.Wheel,
            QtCore.QEvent.Scroll,
        ):
            QtCore.QTimer.singleShot(0, self._render_visible)
        return super().eventFilter(obj, ev)

    # ---------- Internals ----------
    def _current_scale_for(self, base_pm: QtGui.QPixmap) -> float:
        s = self.scale
        vr = self.viewport().rect()
        if self.fit_mode == "width" and base_pm.width() > 0:
            s = (vr.width() - 60) / base_pm.width()
        elif self.fit_mode == "page" and base_pm.width() > 0 and base_pm.height() > 0:
            s = min((vr.width() - 60) / base_pm.width(),
                    (vr.height() - 60) / base_pm.height())
        return max(MIN_SCALE, min(MAX_SCALE, s))

    def _refresh_placeholders(self):
        if not self.doc or not self.pages:
            return
        base = self.doc.render_page(0, 1.0)
        scale = self._current_scale_for(base)
        for pw in self.pages:
            pw.unload(scale)
            self.loaded[pw.page_index] = False

    def _find_first_visible_index(self) -> int:
        y_top = self.verticalScrollBar().value()
        for i in range(max(0, self._last_first_visible - 5), len(self.pages)):
            w = self.pages[i]
            y = w.pos().y()
            h = w.height() if w.height() > 0 else w.sizeHint().height()
            if y + h >= y_top:
                return i
        return 0

    def _render_visible(self):
        if not self.doc or not self.pages:
            return

        base = self.doc.render_page(0, 1.0)
        scale = self._current_scale_for(base)
        first = self._find_first_visible_index()

        if first != self._last_first_visible:
            self._last_first_visible = first
            self.firstVisibleChanged.emit(first)

        start = max(0, first - PRELOAD_MARGIN)
        end = min(len(self.pages) - 1,
                  start + WINDOW_SIZE - 1 + PRELOAD_MARGIN * 2)

        for i in range(start, end + 1):
            if not self.loaded.get(i):
                pm = self.doc.render_page(i, scale)
                self.pages[i].set_pixmap_scaled(pm, scale)
                self.loaded[i] = True

        for i in list(self.loaded.keys()):
            if self.loaded.get(i) and (i < start or i > end):
                self.pages[i].unload(scale)
                self.loaded[i] = False
