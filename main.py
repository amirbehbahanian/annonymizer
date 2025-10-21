# main_ollama.py
# PyQt6 anonymizer that talks to a local Ollama server over HTTP (no llama-cpp bindings).
# Start Ollama first: `ollama serve` and ensure your model is pulled, e.g.: `ollama pull mistral:7b-instruct-q8_0`

import sys, os, json
from pathlib import Path
from typing import List, Optional
import threading
import requests

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QMessageBox, QDialog, QDialogButtonBox, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# Optional docx support
try:
    from docx import Document
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False


# ============================== Workers ==============================

class OllamaValidateWorker(QThread):
    """Checks that Ollama is reachable and the model exists; warms it with a tiny non-streamed generate."""
    validated = pyqtSignal(str)   # model name
    error = pyqtSignal(str)

    def __init__(self, base_url: str, model_name: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            # 1) Fast existence check that doesn't force a model load
            try:
                r = requests.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model_name, "verbose": False},
                    timeout=60,
                )
                if r.status_code == 404:
                    raise RuntimeError(
                        f"Model '{self.model_name}' not found on Ollama. Run: `ollama pull {self.model_name}`"
                    )
                r.raise_for_status()
            except Exception:
                # If /api/show isn't available or errors out, continue to generate step anyway
                pass

            if self._cancel.is_set():
                return

            # 2) Tiny non-stream generate to warm the model (allow time for cold load)
            body = {
                "model": self.model_name,
                "prompt": "ping",
                "stream": False,
                "temperature": 0.0,
                "num_predict": 8,
                "keep_alive": "10m",  # keep model resident for subsequent requests
            }
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=body,
                timeout=180,  # first cold start can be slow, especially on Windows
            )
            if r.status_code == 404:
                raise RuntimeError(
                    f"Model '{self.model_name}' not found on Ollama. Run: `ollama pull {self.model_name}`"
                )
            r.raise_for_status()
            _ = r.json()

            if self._cancel.is_set():
                return
            self.validated.emit(self.model_name)
        except Exception as e:
            self.error.emit(str(e))


class OllamaAnonymizationWorker(QThread):
    """Streams chunk-by-chunk anonymization via Ollama /api/generate."""
    progress_updated = pyqtSignal(int, int)
    chunk_processed = pyqtSignal(str, str)
    finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, base_url: str, model_name: str, prompt: str, chunks: List[str]):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.prompt = prompt
        self.chunks = list(chunks)
        self._stop = threading.Event()

    def cancel(self):
        self._stop.set()

    def _stream_ollama(self, full_prompt: str, timeout: int = 300) -> str:
        """Stream /api/generate and collect 'response' pieces."""
        url = f"{self.base_url}/api/generate"
        body = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": True,
            "num_predict": 1000,  # max_tokens
            "temperature": 0.5,
            "top_p": 0.5,
            "repeat_penalty": 1.2,
            "keep_alive": "30m",  # prevent model from being unloaded between chunks
        }
        parts: List[str] = []
        with requests.post(url, json=body, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if self._stop.is_set():
                    break
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                piece = data.get("response", "")
                if piece:
                    parts.append(piece)
                if data.get("done"):
                    break
        return "".join(parts).strip()

    def run(self):
        try:
            out = []
            total = len(self.chunks)
            for i, chunk in enumerate(self.chunks, start=1):
                if self._stop.is_set():
                    break
                # Construct few-shot prompt
                full_prompt = (
                    "Replace all names, places, dates, and ages in the following text with ***. "
                    "Respond only with the modified text, no explanations.\n\n"
                    + self.prompt +
                    f"Original: {chunk}\nDe-identified: "
                )
                try:
                    text = self._stream_ollama(full_prompt)
                except Exception as e:
                    text = chunk  # fallback to original if a chunk fails
                    self.error_occurred.emit(f"Chunk {i} error: {e}")

                out.append(text or chunk)
                self.chunk_processed.emit(chunk, text or chunk)
                self.progress_updated.emit(i, total)

            self.finished.emit(out)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================== UI ==============================

class SettingsDialog(QDialog):
    def __init__(self, current_examples: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Few-Shot Examples")
        self.setModal(True)
        self.resize(700, 500)

        layout = QVBoxLayout()
        instructions = QLabel(
            "Configure the few-shot examples for anonymization. Each example should show "
            "an original text and its de-identified version with *** replacements."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color:#666; margin-bottom:8px;")
        layout.addWidget(instructions)

        examples_label = QLabel("Few-Shot Examples:")
        examples_label.setStyleSheet("font-weight:bold; margin-top:10px;")
        layout.addWidget(examples_label)

        self.examples_edit = QTextEdit()
        self.examples_edit.setPlainText(current_examples)
        self.examples_edit.setPlaceholderText(
            "Original: Sarah and John visited New York on July 4th, 2021. Sarah was 25.\n"
            "De-identified: *** and *** visited *** on ***, ***. *** was ***.\n\n"
            "Original: Dr. Ahmed treated Emily in Boston when she was 30, back in 2015.\n"
            "De-identified: *** treated *** in *** when she was ***, back in ***."
        )
        layout.addWidget(self.examples_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_examples(self) -> str:
        return self.examples_edit.toPlainText().strip()


class TextAnonymizer(QMainWindow):
    def __init__(self):
        super().__init__()
        # configurable Ollama endpoint + model name
        self.ollama_url = "http://127.0.0.1:11434"
        # Default to the user's tag; user can change in the UI
        self.model_name = "mistral:7b-instruct-q8_0"

        self.model_worker: Optional[OllamaValidateWorker] = None
        self.proc_worker: Optional[OllamaAnonymizationWorker] = None

        self.original_text = ""
        self.anonymized_chunks: List[str] = []

        self.settings_file = "settings.json"
        self.default_examples = (
            "Original: Sarah and John visited New York on July 4th, 2021. Sarah was 25.\n"
            "De-identified: *** and *** visited *** on ***, ***. *** was ***.\n\n"
            "Original: Dr. Ahmed treated Emily in Boston when she was 30, back in 2015.\n"
            "De-identified: *** treated *** in *** when she was ***, back in ***.\n\n"
            "Original: Michael and Anna celebrated in Paris in June 2020, Michael turned 40.\n"
            "De-identified: *** and *** celebrated in *** in ***, *** turned ***.\n\n"
        )
        self.current_examples = self.default_examples

        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        self.setWindowTitle("Text Anonymizer - Ollama")
        self.setGeometry(100, 100, 900, 700)

        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Text Anonymizer (Ollama)")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#2c3e50; margin:10px 0;")
        layout.addWidget(title)

        # Backend settings
        backend_group = QGroupBox("Ollama Settings")
        bg_layout = QVBoxLayout()

        row0 = QHBoxLayout()
        row0.addWidget(QLabel("Base URL:"))
        self.url_edit = QLineEdit(self.ollama_url)
        self.url_edit.setPlaceholderText("http://127.0.0.1:11434")
        row0.addWidget(self.url_edit)
        bg_layout.addLayout(row0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Model:"))
        self.model_edit = QLineEdit(self.model_name)
        self.model_edit.setPlaceholderText("mistral, mistral:7b-instruct-q8_0, llama3.1, qwen2, etc.")
        row1.addWidget(self.model_edit)

        self.validate_btn = QPushButton("Validate Model")
        self.validate_btn.clicked.connect(self._validate_model)
        row1.addWidget(self.validate_btn)
        bg_layout.addLayout(row1)

        self.model_status = QLabel("No model validated")
        self.model_status.setStyleSheet("color:#e74c3c; font-weight:bold;")
        bg_layout.addWidget(self.model_status)
        backend_group.setLayout(bg_layout)
        layout.addWidget(backend_group)

        # Document upload
        ug = QGroupBox("Document Upload")
        ug_l = QVBoxLayout()
        row2 = QHBoxLayout()
        self.upload_btn = QPushButton("Upload Document (.txt{} )".format(" or .docx" if HAS_DOCX else ""))
        self.upload_btn.setMinimumHeight(38)
        self.upload_btn.clicked.connect(self._upload_document)
        row2.addWidget(self.upload_btn)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color:#7f8c8d;")
        row2.addWidget(self.file_label)
        ug_l.addLayout(row2)
        ug.setLayout(ug_l)
        layout.addWidget(ug)

        # Settings
        sg = QGroupBox("Settings")
        sg_l = QHBoxLayout()
        self.settings_btn = QPushButton("Configure Examples")
        self.settings_btn.setMinimumHeight(34)
        self.settings_btn.clicked.connect(self._open_settings)
        sg_l.addWidget(self.settings_btn)
        self.current_examples_label = QLabel("Default examples loaded")
        self.current_examples_label.setStyleSheet("color:#7f8c8d; font-style:italic;")
        sg_l.addWidget(self.current_examples_label)
        sg.setLayout(sg_l)
        layout.addWidget(sg)

        # Processing
        pg = QGroupBox("Processing")
        pg_l = QVBoxLayout()
        row3 = QHBoxLayout()
        self.process_btn = QPushButton("Start Anonymization")
        self.process_btn.setMinimumHeight(42)
        self.process_btn.setStyleSheet("QPushButton { background:#3498db; color:#fff; font-weight:bold; }")
        self.process_btn.clicked.connect(self._start_anonymization)
        self.process_btn.setEnabled(False)
        row3.addWidget(self.process_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(42)
        self.cancel_btn.setStyleSheet("QPushButton { background:#e74c3c; color:#fff; font-weight:bold; }")
        self.cancel_btn.clicked.connect(self._cancel_processing)
        self.cancel_btn.setVisible(False)
        row3.addWidget(self.cancel_btn)
        pg_l.addLayout(row3)

        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False); pg_l.addWidget(self.progress_bar)
        self.progress_label = QLabel(""); self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter); pg_l.addWidget(self.progress_label)
        pg.setLayout(pg_l)
        layout.addWidget(pg)

        # Results
        rg = QGroupBox("Results")
        rg_l = QVBoxLayout()
        self.download_btn = QPushButton("Download Anonymized Text")
        self.download_btn.setMinimumHeight(38)
        self.download_btn.setStyleSheet("QPushButton { background:#27ae60; color:#fff; font-weight:bold; }")
        self.download_btn.clicked.connect(self._download_results)
        self.download_btn.setEnabled(False)
        rg_l.addWidget(self.download_btn)
        rg.setLayout(rg_l)
        layout.addWidget(rg)

        self.statusBar().showMessage("Ready")

    # ---------------- Settings file ----------------

    def _load_settings(self):
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    s = json.load(f)
                    self.current_examples = s.get("examples", self.default_examples)
        except Exception as e:
            print("Error loading settings:", e)
            self.current_examples = self.default_examples
        self.current_examples_label.setText(
            "Custom examples loaded" if self.current_examples != self.default_examples else "Default examples loaded"
        )

    def _save_settings(self):
        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump({"examples": self.current_examples}, f, indent=2)
        except Exception as e:
            print("Error saving settings:", e)

    # ---------------- UI Actions ----------------

    def _validate_model(self):
        # stop any ongoing validation
        if self.model_worker and self.model_worker.isRunning():
            self.model_worker.cancel()
            self.model_worker.wait()

        self.ollama_url = self.url_edit.text().strip() or self.ollama_url
        self.model_name = self.model_edit.text().strip() or self.model_name

        self.statusBar().showMessage("Validating model on Ollama...")
        self.validate_btn.setEnabled(False)
        self.model_status.setText("Validating model...")
        self.model_status.setStyleSheet("color:#f39c12; font-weight:bold;")

        self.model_worker = OllamaValidateWorker(self.ollama_url, self.model_name)
        self.model_worker.validated.connect(self._on_model_validated)
        self.model_worker.error.connect(self._on_model_error)
        self.model_worker.finished.connect(self._on_model_done)
        self.model_worker.start()

    def _on_model_validated(self, model_name: str):
        self.model_status.setText(f"✓ {model_name} (validated)")
        self.model_status.setStyleSheet("color:#27ae60; font-weight:bold;")
        self.statusBar().showMessage("Model validated successfully")
        if self.original_text:
            self.process_btn.setEnabled(True)
        else:
            # Allow user to start after uploading a doc
            self.process_btn.setEnabled(True)

    def _on_model_error(self, msg: str):
        QMessageBox.critical(
            self,
            "Model Validation Error",
            "Could not validate model on Ollama.\n\n"
            f"Details:\n{msg}\n\n"
            "Tips:\n"
            "- Ensure `ollama serve` is running\n"
            f"- Run: `ollama pull {self.model_name}` if needed\n"
            "- First load can be slow; we increased the timeout. You can also warm it up once:\n"
            f"  ollama run {self.model_name} \"ping\""
        )
        self.model_status.setText("✗ Validation failed")
        self.model_status.setStyleSheet("color:#e74c3c; font-weight:bold;")
        self.statusBar().showMessage("Validation failed")

    def _on_model_done(self):
        self.validate_btn.setEnabled(True)

    def _upload_document(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "",
            "Text files (*.txt);;Word documents (*.docx);;All files (*.*)"
        )
        if not file_path:
            return
        try:
            if file_path.endswith(".docx"):
                if not HAS_DOCX:
                    raise RuntimeError("python-docx not installed (pip install python-docx)")
                doc = Document(file_path)
                self.original_text = "\n".join(p.text for p in doc.paragraphs)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.original_text = f.read()

            self.file_label.setText(f"Loaded: {Path(file_path).name}")
            self.file_label.setStyleSheet("color:#27ae60; font-weight:bold;")
            self.statusBar().showMessage(f"Document loaded: {Path(file_path).name}")

            if "validated" in self.model_status.text().lower():
                self.process_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Document", f"Failed to load document: {e}")
            self.statusBar().showMessage("Error loading document")

    def _open_settings(self):
        dlg = SettingsDialog(self.current_examples, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_examples = dlg.get_examples()
            if new_examples and new_examples != self.current_examples:
                self.current_examples = new_examples
                self.current_examples_label.setText("Custom examples loaded")
                self._save_settings()
                self.statusBar().showMessage("Settings updated")

    def _chunk_text(self, text: str) -> List[str]:
        """Simple chunker: split by '#'-headers; if none, returns the whole text as one chunk."""
        lines = text.split("\n")
        chunks, cur = [], []
        found_header = False
        for line in lines:
            if line.strip().startswith("#") and line.strip() != "#":
                found_header = True
                if cur:
                    chunks.append("\n".join(cur).strip())
                    cur = []
            cur.append(line)
        if cur:
            chunks.append("\n".join(cur).strip())
        chunks = [c for c in chunks if c.strip()]
        return chunks if found_header else [text.strip()] if text.strip() else []

    def _start_anonymization(self):
        if not self.process_btn.isEnabled():
            return
        if not self.current_examples.strip():
            QMessageBox.warning(self, "No Examples", "Please configure the few-shot examples first.")
            return
        if not self.original_text.strip():
            QMessageBox.warning(self, "No Document", "Please upload a document first.")
            return

        chunks = self._chunk_text(self.original_text)
        if not chunks:
            QMessageBox.warning(self, "No Content", "No valid chunks found in the document.")
            return

        if self.proc_worker and self.proc_worker.isRunning():
            reply = QMessageBox.question(
                self, "Processing in Progress",
                "A processing job is already running. Cancel it and start a new one?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.proc_worker.cancel()
                self.proc_worker.wait()
            else:
                return

        self.process_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(chunks))
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Processing 0 of {len(chunks)} chunks...")

        # (Re)read URL/model from fields
        self.ollama_url = self.url_edit.text().strip() or self.ollama_url
        self.model_name = self.model_edit.text().strip() or self.model_name

        self.proc_worker = OllamaAnonymizationWorker(
            base_url=self.ollama_url,
            model_name=self.model_name,
            prompt=self.current_examples,
            chunks=chunks
        )
        self.proc_worker.progress_updated.connect(self._on_progress)
        self.proc_worker.chunk_processed.connect(self._on_chunk_processed)
        self.proc_worker.finished.connect(self._on_finished)
        self.proc_worker.error_occurred.connect(self._on_error)
        self.proc_worker.start()

    def _cancel_processing(self):
        if self.proc_worker and self.proc_worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Processing",
                "Are you sure you want to cancel the current processing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.statusBar().showMessage("Cancelling processing...")
                self.proc_worker.cancel()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Processing {current} of {total} chunks...")
        self.statusBar().showMessage(f"Processing chunk {current} of {total}")

    def _on_chunk_processed(self, original: str, anonymized: str):
        # Hook for live preview if you want to show per-chunk results
        pass

    def _on_finished(self, anonymized_chunks: List[str]):
        self.anonymized_chunks = anonymized_chunks
        self.process_btn.setVisible(True)
        self.process_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.download_btn.setEnabled(True)

        self.statusBar().showMessage(f"Anonymization complete! {len(anonymized_chunks)} chunks processed.")
        QMessageBox.information(
            self, "Anonymization Complete",
            f"Successfully processed {len(anonymized_chunks)} chunks. You can now download the anonymized text."
        )

    def _on_error(self, message: str):
        # Non-fatal per-chunk errors will also appear here
        print("Worker error:", message)

    def _download_results(self):
        if not self.anonymized_chunks:
            QMessageBox.warning(self, "No Results", "No anonymized results to download.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Anonymized Text", "anonymized_text.txt", "Text files (*.txt);;All files (*.*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(self.anonymized_chunks))
            QMessageBox.information(self, "Download Complete", f"Anonymized text saved to: {file_path}")
            self.anonymized_chunks = []
            self.download_btn.setEnabled(False)
            self.statusBar().showMessage("Results downloaded and cleaned up")
        except Exception as e:
            QMessageBox.critical(self, "Download Error", f"Failed to save file: {e}")

    def closeEvent(self, event):
        if self.model_worker and self.model_worker.isRunning():
            self.model_worker.cancel()
            self.model_worker.wait()
        if self.proc_worker and self.proc_worker.isRunning():
            self.proc_worker.cancel()
            self.proc_worker.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Text Anonymizer - Ollama")
    app.setApplicationVersion("1.1")
    app.setStyle('Fusion')

    win = TextAnonymizer()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
