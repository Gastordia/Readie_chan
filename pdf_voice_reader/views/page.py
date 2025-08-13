from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ..model.pdfdoc import PDFDoc


class _OverlayLabel(QtWidgets.QLabel):
    """Label that paints a selection overlay over the page pixmap."""
    def __init__(self, owner: "PageWidget"):
        super().__init__(owner)
        self._owner = owner
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
        super().paintEvent(ev)
        self._owner._paint_selection_overlay(self)


class PageWidget(QtWidgets.QFrame):
    wordClicked   = QtCore.Signal(int, int)   # page_index, word_index
    selectionMade = QtCore.Signal(int, str)   # page_index, selected text

    def __init__(self, doc: PDFDoc, page_index: int):
        super().__init__()
        self.doc = doc
        self.page_index = page_index

        self.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.setAutoFillBackground(True)
        self._sync_card_background()

        # Shadow for modern card look
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QtGui.QColor(0, 0, 0, 60))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        self.setStyleSheet("QFrame { border: 1px solid rgba(0,0,0,35); border-radius: 10px; }")

        # Pixmap holder + overlay
        self.lbl = _OverlayLabel(self)
        self.lbl.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.lbl)

        # Current scale used to render this page (for word boxes)
        self.scale_for_words: float = 1.0

        # Selection state
        self._selection_enabled = False
        self._dragging = False
        self._press_pos: QtCore.QPointF | None = None
        self._sel_start_idx: int | None = None
        self._sel_end_idx: int | None = None
        self._last_selection_range: tuple[int, int] | None = None

    # ----- public API called by scroller -----
    def placeholder_size(self, scale: float) -> QtCore.QSize:
        w, h = self.doc.page_size(self.page_index)
        return QtCore.QSize(int(w * scale), int(h * scale))

    def unload(self, scale: float):
        sz = self.placeholder_size(scale)
        self.lbl.clear()
        self.setMinimumHeight(sz.height())
        self.setMaximumHeight(sz.height())
        self.scale_for_words = scale
        self._clear_selection()

    def set_pixmap_scaled(self, pm: QtGui.QPixmap, scale_used: float):
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.lbl.setPixmap(pm)
        self.scale_for_words = scale_used

    def setSelectionEnabled(self, enabled: bool):
        self._selection_enabled = bool(enabled)
        self.setCursor(QtCore.Qt.IBeamCursor if enabled else QtCore.Qt.ArrowCursor)
        if not enabled:
            self._clear_selection()
        self.update()

    # ----- geometry helpers -----
    def _pixmap_offset_x(self) -> float:
        pm = self.lbl.pixmap()
        if not pm:
            return 0.0
        return max(0.0, (self.lbl.width() - pm.width()) * 0.5)

    def _nearest_word_index(self, pos: QtCore.QPointF) -> int:
        words = self.doc.page_words(self.page_index)
        if not words:
            return -1
        x = pos.x() - self._pixmap_offset_x()
        y = pos.y()
        hit = -1
        best_d = 1e12
        s = self.scale_for_words
        for idx, (x0, y0, x1, y1, _w) in enumerate(words):
            rx0, ry0, rx1, ry1 = x0 * s, y0 * s, x1 * s, y1 * s
            if rx0 <= x <= rx1 and ry0 <= y <= ry1:
                return idx
            cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < best_d:
                best_d = d
                hit = idx
        return hit

    # ----- mouse handling (parent frame) -----
    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._selection_enabled and e.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._press_pos = e.position()
            self._sel_start_idx = self._nearest_word_index(self._press_pos)
            self._sel_end_idx = self._sel_start_idx
            self.lbl.update()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._selection_enabled and self._dragging:
            self._sel_end_idx = self._nearest_word_index(e.position())
            self.lbl.update()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._selection_enabled and e.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            s = self._sel_start_idx if self._sel_start_idx is not None else -1
            t = self._sel_end_idx if self._sel_end_idx is not None else -1
            if s >= 0 and t >= 0:
                i0, i1 = (s, t) if s <= t else (t, s)
                self._last_selection_range = (i0, i1)
                words = self.doc.page_words(self.page_index)
                text = " ".join(w for *_, w in words[i0 : i1 + 1]).strip()
                if text:
                    self.selectionMade.emit(self.page_index, text)
            self.lbl.update()
        else:
            super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        words = self.doc.page_words(self.page_index)
        if not words:
            return
        hit = self._nearest_word_index(e.position())
        self.wordClicked.emit(self.page_index, hit)

    # ----- overlay painting -----
    def _paint_selection_overlay(self, target: QtWidgets.QWidget) -> None:
        rng = None
        if (self._selection_enabled and self._dragging and
            self._sel_start_idx is not None and self._sel_end_idx is not None):
            s, t = self._sel_start_idx, self._sel_end_idx
            rng = (s, t) if s <= t else (t, s)
        elif self._last_selection_range:
            rng = self._last_selection_range

        if rng is None:
            return

        words = self.doc.page_words(self.page_index)
        i0, i1 = rng
        s = self.scale_for_words
        dx = self._pixmap_offset_x()

        # Theme-aware colors
        pal = self.palette()
        hi = pal.highlight().color()
        # soft translucent fill + stronger border from highlight color
        fill = QtGui.QColor(hi); fill.setAlpha(80)
        pen_col = QtGui.QColor(hi); pen_col.setAlpha(180)

        painter = QtGui.QPainter(target)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtGui.QPen(pen_col, 2))
        painter.setBrush(QtGui.QBrush(fill))

        for idx in range(max(0, i0), min(len(words) - 1, i1) + 1):
            x0, y0, x1, y1, _ = words[idx]
            r = QtCore.QRectF(
                dx + x0 * s,
                y0 * s,
                (x1 - x0) * s,
                (y1 - y0) * s,
            )
            painter.drawRoundedRect(r, 3, 3)

        painter.end()

    # ----- helpers -----
    def _clear_selection(self):
        self._dragging = False
        self._sel_start_idx = None
        self._sel_end_idx = None
        self._last_selection_range = None

    def _sync_card_background(self):
        pal = self.palette()
        # Use Base for card bg so it flips nicely in dark themes
        bg = pal.base().color()
        pal.setColor(QtGui.QPalette.Window, bg)
        self.setPalette(pal)
