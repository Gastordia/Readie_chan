from __future__ import annotations
from pathlib import Path
from typing import Optional, List
import json

from PySide6 import QtCore, QtGui, QtWidgets
from ..config import APP_NAME, STATE_FILE, DEFAULT_LIB, MIN_SCALE, MAX_SCALE
from ..util import scan_voice_models, chunk_text
from ..controller import AppController
from ..model.pdfdoc import PDFDoc
import json

from .gallery import GalleryView
from .pdfview import ContinuousPDFView

from ..themes import apply_theme, THEME_NAMES, DEFAULT_THEME


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        QtWidgets.QApplication.setApplicationName(APP_NAME)
        self.resize(1480, 940)

        self.state = self._load_state()
        self.lib_dir = Path(self.state.get("lib_dir", str(DEFAULT_LIB))).expanduser()

        self.controller = AppController()
        self.controller.voice_model = self.state.get("voice_model")
        self.controller.wpm = int(self.state.get("wpm", 170))

        self.current_doc: Optional[PDFDoc] = None
        self._last_selection: str = ""
        self.current_theme = self.state.get("theme", DEFAULT_THEME)

        # central stack
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)

        # gallery
        self.gallery = GalleryView(self.lib_dir)
        self.stack.addWidget(self.gallery)

        # reader page
        self.reader = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(self.reader)
        rl.setContentsMargins(0, 0, 0, 0)
        self.stack.addWidget(self.reader)

        # toolbar
        self.tb = QtWidgets.QToolBar()
        self.tb.setMovable(False)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.tb)
        self._build_toolbar()

        # pdf view
        self.pdf_view = ContinuousPDFView()
        rl.addWidget(self.pdf_view, 1)

        # signals (selection + “first visible”)
        if hasattr(self.pdf_view, "textSelected"):
            self.pdf_view.textSelected.connect(self.on_text_selected)
        if hasattr(self.pdf_view, "firstVisibleChanged"):
            self.pdf_view.firstVisibleChanged.connect(self.on_first_visible_changed)
        if hasattr(self.pdf_view, "wordClicked"):
            self.pdf_view.wordClicked.connect(self.on_word_clicked)

        # docks
        self._build_docks()

        
                # ----- View menu & focus escape -----
        self._build_menu()

        # Floating "Exit Focus" button (visible only in focus mode)
        self.exit_focus_btn = QtWidgets.QPushButton("Exit Focus (Esc)", self)
        self.exit_focus_btn.setVisible(False)
        self.exit_focus_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.exit_focus_btn.clicked.connect(self.leave_focus)
        self.exit_focus_btn.setStyleSheet(
            "QPushButton { background:#222; color:#fff; border-radius:10px; padding:6px 10px; }"
            "QPushButton:hover { background:#333; }"
        )

        # Keyboard shortcuts: F11 toggles focus, Esc exits focus
        QtGui.QShortcut(QtGui.QKeySequence("F11"), self, activated=self._toggle_focus_action)
        QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self.leave_focus)


        # status + shortcuts
        self.status = self.statusBar()
        self.status.showMessage("Ready")
        QtGui.QShortcut(QtGui.QKeySequence("Space"), self, activated=self.toggle_pause)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self, activated=self.show_gallery)

        # keyboard zoom (Ctrl +/- / 0)
        for seq in ("Ctrl++", "Ctrl+=", "Ctrl+Plus"):
            QtGui.QShortcut(QtGui.QKeySequence(seq), self, activated=lambda f=1.10: self.zoom_step(f))
        for seq in ("Ctrl+-", "Ctrl+_", "Ctrl+Minus"):
            QtGui.QShortcut(QtGui.QKeySequence(seq), self, activated=lambda f=1 / 1.10: self.zoom_step(f))
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, activated=lambda: self.set_fit("width"))

        # apply theme
        apply_theme(self, self.current_theme)

        # wire controller
        self.controller.connect(self)

        # start in gallery
        self.show_gallery()
        self._sync_zoom_label()

    # ---------------- UI ----------------
    def _build_toolbar(self):
        self.act_home = QtGui.QAction("🏠 Library", self)
        self.act_home.triggered.connect(self.show_gallery)
        self.tb.addAction(self.act_home)

        self.act_focus = QtGui.QAction("Focus", self)
        self.act_focus.setCheckable(True)
        self.act_focus.triggered.connect(self.toggle_focus)
        self.tb.addAction(self.act_focus)

        self.tb.addSeparator()

        self.act_prev = QtGui.QAction("◀ Prev", self)
        self.act_prev.triggered.connect(lambda: self.change_page(-1))
        self.act_next = QtGui.QAction("Next ▶", self)
        self.act_next.triggered.connect(lambda: self.change_page(+1))
        self.tb.addAction(self.act_prev)
        self.tb.addAction(self.act_next)

        self.tb.addWidget(QtWidgets.QLabel("Page:"))
        self.spin_page = QtWidgets.QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.valueChanged.connect(self.on_page_spin)
        self.tb.addWidget(self.spin_page)

        self.tb.addSeparator()

        self.act_read_page = QtGui.QAction("Read page", self)
        self.act_read_page.triggered.connect(lambda: self.start_read("page"))
        self.act_read_from_here = QtGui.QAction("Read from here → end", self)
        self.act_read_from_here.triggered.connect(lambda: self.start_read("from_here"))
        self.act_read_selection = QtGui.QAction("Read selection", self)
        self.act_read_selection.triggered.connect(lambda: self.start_read("selection"))
        self.act_read_from_click = QtGui.QAction("Read from click", self)
        self.act_read_from_click.setCheckable(True)

        self.tb.addAction(self.act_read_page)
        self.tb.addAction(self.act_read_from_here)
        self.tb.addAction(self.act_read_selection)
        self.tb.addAction(self.act_read_from_click)

        self.act_select = QtGui.QAction("Select", self)
        self.act_select.setCheckable(True)
        self.act_select.toggled.connect(self.on_select_toggled)
        self.tb.addAction(self.act_select)

        self.tb.addSeparator()

        self.act_play = QtGui.QAction("▶ Play", self)
        self.act_play.triggered.connect(self.resume_read)
        self.act_pause = QtGui.QAction("⏸ Pause", self)
        self.act_pause.triggered.connect(self.pause_read)
        self.act_stop = QtGui.QAction("⏹ Stop", self)
        self.act_stop.triggered.connect(self.stop_read)
        self.tb.addAction(self.act_play)
        self.tb.addAction(self.act_pause)
        self.tb.addAction(self.act_stop)

        self.tb.addSeparator()

        self.tb.addWidget(QtWidgets.QLabel("Zoom:"))
        self.zoom_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom_slider.setRange(int(MIN_SCALE * 100), int(MAX_SCALE * 100))
        self.zoom_slider.setFixedWidth(180)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.tb.addWidget(self.zoom_slider)
        self.lbl_zoom = QtWidgets.QLabel("100%")
        self.tb.addWidget(self.lbl_zoom)

        self.act_fit_w = QtGui.QAction("Fit width", self)
        self.act_fit_w.setCheckable(True)
        self.act_fit_w.setChecked(True)
        self.act_fit_w.triggered.connect(lambda: self.set_fit("width"))
        self.act_fit_p = QtGui.QAction("Fit page", self)
        self.act_fit_p.setCheckable(True)
        self.act_fit_p.triggered.connect(lambda: self.set_fit("page"))
        self.tb.addAction(self.act_fit_w)
        self.tb.addAction(self.act_fit_p)

        # Settings
        self.act_settings = QtGui.QAction("⚙ Settings", self)
        self.act_settings.setCheckable(True)
        self.act_settings.setChecked(True)
        self.act_settings.triggered.connect(self.toggle_settings)
        self.tb.addAction(self.act_settings)

        # Theme toggle (shows Appearance dock)
        self.act_theme = QtGui.QAction("🎨 Theme", self)
        self.act_theme.setCheckable(True)
        self.act_theme.triggered.connect(
            lambda: self.appearance_dock.setVisible(self.act_theme.isChecked())
        )
        self.tb.addAction(self.act_theme)

    def _build_docks(self):


        # Appearance dock (themes)
        self.appearance_dock = QtWidgets.QDockWidget("Appearance", self)
        self.appearance_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.appearance_dock)

        panel = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(panel)

                # settings
        self.settings_dock = QtWidgets.QDockWidget("Settings", self)
        self.settings_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)
        self.settings_dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.settings_dock)
        self.settings_panel = self._build_settings_panel()
        self.settings_dock.setWidget(self.settings_panel)

        # extracted text
        self.text_dock = QtWidgets.QDockWidget("Extracted Text", self)
        self.text_dock.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.text_dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetClosable
            | QtWidgets.QDockWidget.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFloatable
        )
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(False)
        self.text_dock.setWidget(self.text_edit)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.text_dock)
        self.text_dock.setVisible(False)

        

        self.cmb_theme = QtWidgets.QComboBox()
        self.cmb_theme.addItems(THEME_NAMES)
        self.cmb_theme.setCurrentText(self.current_theme)
        self.cmb_theme.currentTextChanged.connect(self.on_theme_changed)
        form.addRow("Theme", self.cmb_theme)

        self.appearance_dock.setWidget(panel)
        self.appearance_dock.setVisible(False)

    def _build_settings_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        g = QtWidgets.QFormLayout(w)

        self.cmb_voice = QtWidgets.QComboBox()
        self.cmb_voice.setMinimumWidth(460)
        self.btn_add_voice = QtWidgets.QPushButton("Add .onnx…")
        self.btn_add_voice.clicked.connect(self.add_voice)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.cmb_voice, 1)
        row.addWidget(self.btn_add_voice)
        g.addRow("Voice Model", row)

        self.slider_wpm = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_wpm.setRange(100, 260)
        self.slider_wpm.setValue(self.controller.wpm)
        self.lbl_wpm = QtWidgets.QLabel(str(self.controller.wpm))
        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(self.slider_wpm, 1)
        row2.addWidget(self.lbl_wpm)
        g.addRow("Speed (WPM)", row2)


        self.slider_wpm.valueChanged.connect(self.on_wpm_changed)
        self.cmb_voice.currentTextChanged.connect(self.on_voice_changed)
        self.reload_voices()
        return w

    # ------------- gallery & file open -------------
    def show_gallery(self):
        self.gallery.lib_dir = self.lib_dir
        self.gallery.reload()
        self.stack.setCurrentWidget(self.gallery)
        self.setWindowTitle(APP_NAME + " — Library")
    
    def on_select_toggled(self, enabled: bool):
        """Enable/disable text selection on the PDF view (if supported)."""
        if hasattr(self, "pdf_view") and hasattr(self.pdf_view, "set_select_mode"):
            self.pdf_view.set_select_mode(bool(enabled))



    def on_library_changed(self, d: Path):
        self.lib_dir = d
        self._save_state()

    def show_reader(self):
        self.stack.setCurrentWidget(self.reader)
        self.setWindowTitle(APP_NAME)

    def open_path(self, path: Path):
        try:
            self.current_doc = PDFDoc(path)
            self.current_doc.open()
            self.pdf_view.set_document(self.current_doc)
            self.spin_page.setMaximum(self.current_doc.page_count)
            self.spin_page.setValue(1)
            self.text_edit.setPlainText(self.current_doc.page_text(0))
            self.state["last_file"] = str(path)
            self._save_state()
            self.show_reader()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(e))

    # ------------- page / zoom -------------
    def change_page(self, delta: int):
        if not self.current_doc:
            return
        val = max(1, min(self.spin_page.maximum(), self.spin_page.value() + delta))
        self.spin_page.setValue(val)
        self.pdf_view.go_to_page(val)
        self.text_edit.setPlainText(self.current_doc.page_text(val - 1))

    def on_page_spin(self, val: int):
        if not self.current_doc:
            return
        self.pdf_view.go_to_page(val)
        self.text_edit.setPlainText(self.current_doc.page_text(val - 1))

    def set_fit(self, mode: str):
        self.act_fit_w.setChecked(mode == "width")
        self.act_fit_p.setChecked(mode == "page")
        self.pdf_view.set_fit_mode(mode)
        self._sync_zoom_label()

    def on_zoom_changed(self, value: int):
        self.act_fit_w.setChecked(False)
        self.act_fit_p.setChecked(False)
        new_scale = value / 100.0
        if hasattr(self.pdf_view, "smooth_zoom_to"):
            self.pdf_view.smooth_zoom_to(new_scale)
        else:
            self.pdf_view.set_zoom(new_scale)
        self._sync_zoom_label()

    def zoom_step(self, factor: float):
        self.act_fit_w.setChecked(False)
        self.act_fit_p.setChecked(False)
        cur = self._current_zoom()
        new_scale = cur * factor
        if hasattr(self.pdf_view, "smooth_zoom_to"):
            self.pdf_view.smooth_zoom_to(new_scale)
        else:
            self.pdf_view.set_zoom(new_scale)
        self._sync_zoom_label()

    def _sync_zoom_label(self):
        z = int(round(self._current_zoom() * 100))
        self.lbl_zoom.setText(f"{z}%")
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(z)
        self.zoom_slider.blockSignals(False)

    def _current_zoom(self) -> float:
        try:
            if hasattr(self.pdf_view, "_get_zoom"):
                return float(self.pdf_view._get_zoom())
            if hasattr(self.pdf_view, "scale"):
                return float(self.pdf_view.scale)
        except Exception:
            pass
        return 1.0

    # ------------- settings -------------
    def toggle_settings(self):
        vis = not self.settings_dock.isVisible()
        self.settings_dock.setVisible(vis)
        self.act_settings.setChecked(vis)

    def toggle_focus(self):
        focus = self.act_focus.isChecked()
        self.tb.setVisible(not focus)
        if focus:
            self.settings_dock.setVisible(False)

    def add_voice(self):
        from .config import VOICE_DIRS
        from .util import validate_piper_model

        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose Piper .onnx model", VOICE_DIRS[0], "Piper Model (*.onnx)"
        )
        if not fn:
            return
        try:
            validate_piper_model(fn)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Invalid Voice", str(e))
            return
        self.controller.voice_model = fn
        self.reload_voices(select=fn)
        self._save_state()

    def reload_voices(self, select: str | None = None):
        voices = scan_voice_models()
        self.cmb_voice.blockSignals(True)
        self.cmb_voice.clear()
        for v in voices:
            self.cmb_voice.addItem(v)
        if select and select in voices:
            self.cmb_voice.setCurrentText(select)
        elif self.controller.voice_model and self.controller.voice_model in voices:
            self.cmb_voice.setCurrentText(self.controller.voice_model)
        elif voices:
            self.cmb_voice.setCurrentIndex(0)
            self.controller.voice_model = voices[0]
        else:
            self.cmb_voice.addItem("<No voices found — add .onnx>")
        self.cmb_voice.blockSignals(False)

    def on_voice_changed(self, text: str):
        if text and text.startswith("/"):
            self.controller.voice_model = text
            self._save_state()

    def on_wpm_changed(self, val: int):
        self.controller.wpm = int(val)
        self.lbl_wpm.setText(str(self.controller.wpm))
        self._save_state()

    # ------------- selection & TTS -------------
    def on_text_selected(self, page_index: int, text: str):
        if hasattr(self, "text_dock"):
            self.text_dock.setVisible(False)
        self._last_selection = text or ""
        if hasattr(self, "text_edit"):
            self.text_edit.setPlainText(self._last_selection)
            cur = self.text_edit.textCursor()
            cur.select(QtGui.QTextCursor.Document)
            self.text_edit.setTextCursor(cur)

    def start_read(self, mode: str):
        if not self.current_doc or not self.controller.voice_model:
            QtWidgets.QMessageBox.information(
                self, "Missing", "Open a PDF and choose a voice model."
            )
            return

        chunks: List[str] = []
        if mode == "page":
            text = self.current_doc.page_text(self.spin_page.value() - 1)
            chunks = chunk_text(text)

        elif mode == "from_here":
            start = self.spin_page.value() - 1
            for i in range(start, self.current_doc.page_count):
                chunks.extend(chunk_text(self.current_doc.page_text(i)))

        elif mode == "selection":
            sel = (self._last_selection or "").strip()
            if not sel:
                sel = self.text_edit.textCursor().selectedText().strip()
            if not sel:
                QtWidgets.QMessageBox.information(
                    self,
                    "No selection",
                    "Toggle Select and drag on the page, or select text in the Extracted Text panel.",
                )
                return
            chunks = chunk_text(sel)

        if not chunks:
            QtWidgets.QMessageBox.information(self, "Empty", "No text to read.")
            return

        self.controller.start_queue(chunks)
        self.status.showMessage("Speaking…")

    def on_word_clicked(self, page_index: int, word_index: int):
        if not getattr(self, "act_read_from_click", None) or not self.act_read_from_click.isChecked():
            return
        if not self.current_doc:
            return
        words = self.current_doc.page_words(page_index)
        if word_index < 0 or word_index >= len(words):
            return
        after = " ".join(w for *_, w in words[max(0, word_index):])
        chunks = chunk_text(after)
        for i in range(page_index + 1, self.current_doc.page_count):
            chunks.extend(chunk_text(self.current_doc.page_text(i)))
        if not chunks:
            return
        self.controller.start_queue(chunks)
        self.status.showMessage(f"Speaking from page {page_index + 1}…")

    def resume_read(self):
        self.controller.resume()
        self.status.showMessage("Playing")

    def pause_read(self):
        self.controller.pause()
        self.status.showMessage("Paused")

    def toggle_pause(self):
        if getattr(self.controller.engine, "_pause_flag", False):
            self.resume_read()
        else:
            self.pause_read()

    def stop_read(self):
        self.controller.stop()
        self.status.showMessage("Stopped")

    # keep spinner & bottom text synced with scrolling
    def on_first_visible_changed(self, first_index: int):
        if not self.current_doc:
            return
        self.spin_page.blockSignals(True)
        self.spin_page.setValue(first_index + 1)
        self.spin_page.blockSignals(False)
        try:
            self.text_edit.setPlainText(self.current_doc.page_text(first_index))
        except Exception:
            pass

    # ------------- theme -------------
    def on_theme_changed(self, name: str):
        self.current_theme = name
        apply_theme(self, name)
        self._save_state()

    # ------------- state -------------
    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save_state(self):
        self.state = getattr(self, "state", {})
        self.state["lib_dir"] = str(self.lib_dir)
        self.state["voice_model"] = self.controller.voice_model
        self.state["wpm"] = self.controller.wpm
        self.state["theme"] = getattr(self, "current_theme", DEFAULT_THEME)
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def _toggle_focus_action(self):
        # keep the QAction’s checked state in sync when pressing F11
        self.act_focus.toggle()


    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "exit_focus_btn") and self.exit_focus_btn.isVisible():
            # place it with a margin from the top-right corner
            m = 16
            x = self.width() - self.exit_focus_btn.width() - m
            y = m
            self.exit_focus_btn.move(max(0, x), max(0, y))


    def _build_menu(self):
        menubar = self.menuBar()
        view = menubar.addMenu("&View")

        # Focus mode in the menu (same QAction as toolbar)
        self.act_focus.setShortcut("F11")
        view.addAction(self.act_focus)

        view.addSeparator()

        # Dock toggle actions automatically manage visibility & check state
        self.act_view_settings = self.settings_dock.toggleViewAction()
        self.act_view_settings.setText("Settings")
        view.addAction(self.act_view_settings)

        self.act_view_text = self.text_dock.toggleViewAction()
        self.act_view_text.setText("Extracted Text")
        view.addAction(self.act_view_text)


    def toggle_focus(self):
        focus = self.act_focus.isChecked()
        if focus:
            # Save current visibility to restore later
            self._pre_focus = {
                "tb": self.tb.isVisible(),
                "settings": self.settings_dock.isVisible(),
                "text": self.text_dock.isVisible(),
            }
            self.tb.setVisible(False)
            self.settings_dock.hide()
            self.text_dock.hide()

            # Show floating exit button
            self.exit_focus_btn.setVisible(True)
            self.exit_focus_btn.adjustSize()
            self.resizeEvent(QtGui.QResizeEvent(self.size(), self.size()))
        else:
            # Restore previous visibilities
            if hasattr(self, "_pre_focus"):
                self.tb.setVisible(self._pre_focus.get("tb", True))
                self.settings_dock.setVisible(self._pre_focus.get("settings", False))
                self.text_dock.setVisible(self._pre_focus.get("text", False))
            else:
                self.tb.setVisible(True)

            self.exit_focus_btn.setVisible(False)

    def leave_focus(self):
        if self.act_focus.isChecked():
            self.act_focus.setChecked(False)
            self.toggle_focus()

    
