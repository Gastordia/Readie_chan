from __future__ import annotations
from typing import List, Optional
from PySide6 import QtCore
from .tts import PiperEngine

class AppController(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.voice_model: Optional[str] = None
        self.wpm: int = 170
        self.engine = PiperEngine()

    def connect(self, window: 'MainWindow'):
        window.gallery.opened.connect(lambda p: window.open_path(p))
        window.gallery.changed_dir.connect(lambda d: window.on_library_changed(d))
        window.pdf_view.wordClicked.connect(window.on_word_clicked)

    def start_queue(self, chunks: List[str]):
        if not chunks:
            return
        self.engine.set_queue(chunks)
        if self.voice_model:
            self.engine.set_model(self.voice_model)
        self.engine.set_wpm(self.wpm)
        self.engine._stop_flag = False
        self.engine._pause_flag = False
        self.engine.start()

    def pause(self):
        self.engine.pause()

    def resume(self):
        self.engine.resume()

    def stop(self):
        self.engine.stop()
