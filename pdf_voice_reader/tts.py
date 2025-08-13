from __future__ import annotations
import os, subprocess, time
from typing import Optional, List
from PySide6 import QtCore
from .util import ensure_cmd, map_wpm_to_length_scale, validate_piper_model

class PiperEngine(QtCore.QObject):
    progress = QtCore.Signal(int)
    finished = QtCore.Signal()
    error    = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_path: Optional[str] = None
        self.wpm: int = 170
        self._chunks: List[str] = []
        self._i = 0
        self._thread = QtCore.QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._loop)
        self._stop_flag = False
        self._pause_flag = False
        self._proc_piper: Optional[subprocess.Popen] = None
        self._proc_aplay: Optional[subprocess.Popen] = None

    @QtCore.Slot()
    def start(self):
        if not self._thread.isRunning():
            self._thread.start()

    @QtCore.Slot()
    def stop(self):
        self._stop_flag = True
        self._kill_procs()

    @QtCore.Slot()
    def pause(self):
        self._pause_flag = True
        self._kill_procs()

    @QtCore.Slot()
    def resume(self):
        self._pause_flag = False
        if not self._thread.isRunning():
            self._thread.start()

    def set_queue(self, chunks: List[str], start_index: int = 0):
        self._chunks = chunks
        self._i = max(0, min(start_index, len(chunks)))

    def set_model(self, model: str):
        validate_piper_model(model)
        self.model_path = model

    def set_wpm(self, wpm: int):
        self.wpm = int(wpm)

    def _kill_procs(self):
        for proc in (self._proc_aplay, self._proc_piper):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    t0 = time.time()
                    while proc.poll() is None and time.time() - t0 < 0.25:
                        time.sleep(0.01)
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    pass
        self._proc_aplay = None
        self._proc_piper = None

    @QtCore.Slot()
    def _loop(self):
        try:
            ensure_cmd("piper"); ensure_cmd("aplay")
            while not self._stop_flag and self._i < len(self._chunks):
                if self._pause_flag:
                    time.sleep(0.05); continue
                text = self._chunks[self._i]
                if not self.model_path:
                    self.error.emit("No Piper model selected"); break
                length_scale = f"{map_wpm_to_length_scale(self.wpm):.3f}"
                self._proc_piper = subprocess.Popen(
                    ["piper", "-m", os.path.expanduser(self.model_path), "--length_scale", length_scale, "-f", "-"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                self._proc_aplay = subprocess.Popen(
                    ["aplay", "-q", "-t", "wav", "-"],
                    stdin=self._proc_piper.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                try:
                    assert self._proc_piper.stdin is not None
                    self._proc_piper.stdin.write(text.encode("utf-8"))
                    self._proc_piper.stdin.close()
                except Exception:
                    pass
                while True:
                    if self._stop_flag or self._pause_flag:
                        self._kill_procs(); break
                    code = self._proc_aplay.poll()
                    if code is not None:
                        if code != 0:
                            err = (self._proc_aplay.stderr.read().decode(errors="ignore") if self._proc_aplay.stderr else "")
                            self.error.emit(err or "aplay failed"); self._kill_procs(); return
                        break
                    time.sleep(0.01)
                if self._stop_flag or self._pause_flag:
                    continue
                self._i += 1
                self.progress.emit(self._i)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._kill_procs()
            self._thread.quit()
