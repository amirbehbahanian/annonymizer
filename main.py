import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, QTextEdit, QProgressBar,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QGroupBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette

try:
    from llama_cpp import Llama
except ImportError:
    print("llama-cpp-python not installed. Please install with: pip install llama-cpp-python")
    sys.exit(1)

try:
    from docx import Document
except ImportError:
    print("python-docx not installed. Please install with: pip install python-docx")
    sys.exit(1)


class SettingsDialog(QDialog):
    """Dialog for configuring anonymization prompt"""
    
    def __init__(self, current_prompt: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Anonymization Prompt")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "Configure the prompt that will be used to anonymize the text chunks. "
            "The prompt should instruct the AI to remove or replace sensitive information "
            "such as names, addresses, phone numbers, etc."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Prompt text area
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(current_prompt)
        self.prompt_edit.setPlaceholderText(
            "Enter your anonymization prompt here...\n\nExample:\n"
            "Please anonymize the following text by replacing all personal information "
            "such as names, addresses, phone numbers, email addresses, and other "
            "identifying details with generic placeholders like [NAME], [ADDRESS], etc. "
            "Keep the structure and meaning of the text intact."
        )
        layout.addWidget(self.prompt_edit)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                    QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_prompt(self) -> str:
        return self.prompt_edit.toPlainText().strip()


class AnonymizationWorker(QThread):
    """Worker thread for processing text anonymization"""
    
    progress_updated = pyqtSignal(int, int)  # current, total
    chunk_processed = pyqtSignal(str, str)  # original, anonymized
    finished = pyqtSignal(list)  # list of anonymized chunks
    error_occurred = pyqtSignal(str)
    
    def __init__(self, chunks: List[str], prompt: str, model):
        super().__init__()
        self.chunks = chunks
        self.prompt = prompt
        self.model = model
        self.is_cancelled = False
    
    def run(self):
        try:
            anonymized_chunks = []
            total_chunks = len(self.chunks)
            
            for i, chunk in enumerate(self.chunks):
                if self.is_cancelled:
                    return
                
                try:
                    # Create the full prompt with the chunk
                    full_prompt = f"{self.prompt}\n\nText to anonymize:\n{chunk}"
                    
                    # Generate anonymized text
                    response = self.model(full_prompt, max_tokens=2048, temperature=0.1, stop=["</s>"])
                    anonymized_text = response['choices'][0]['text'].strip()
                    
                    anonymized_chunks.append(anonymized_text)
                    self.chunk_processed.emit(chunk, anonymized_text)
                    
                except Exception as e:
                    print(f"Error processing chunk {i+1}: {str(e)}")
                    # If anonymization fails, keep original chunk
                    anonymized_chunks.append(chunk)
                
                self.progress_updated.emit(i + 1, total_chunks)
            
            if not self.is_cancelled:
                self.finished.emit(anonymized_chunks)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True


class TextAnonymizer(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.original_text = ""
        self.anonymized_chunks = []
        self.settings_file = "settings.json"
        self.default_prompt = (
            "Please anonymize the following text by replacing all personal information "
            "such as names, addresses, phone numbers, email addresses, and other "
            "identifying details with generic placeholders like [NAME], [ADDRESS], etc. "
            "Keep the structure and meaning of the text intact. Return only the anonymized text."
        )
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Text Anonymizer - LLM Powered")
        self.setGeometry(100, 100, 900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Text Anonymizer")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 10px 0;")
        layout.addWidget(title)
        
        # Model Selection Group
        model_group = QGroupBox("Model Selection")
        model_layout = QVBoxLayout()
        
        button_layout = QHBoxLayout()
        self.load_model_btn = QPushButton("Browse and Load Model")
        self.load_model_btn.setMinimumHeight(40)
        self.load_model_btn.clicked.connect(self.load_model)
        button_layout.addWidget(self.load_model_btn)
        model_layout.addLayout(button_layout)
        
        self.model_status = QLabel("No model loaded")
        self.model_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        model_layout.addWidget(self.model_status)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # File Upload Group
        upload_group = QGroupBox("Document Upload")
        upload_layout = QVBoxLayout()
        
        file_layout = QHBoxLayout()
        self.upload_btn = QPushButton("Upload Document (.txt or .docx)")
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(self.upload_document)
        file_layout.addWidget(self.upload_btn)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #7f8c8d;")
        file_layout.addWidget(self.file_label)
        
        upload_layout.addLayout(file_layout)
        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)
        
        # Settings Group
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout()
        
        self.settings_btn = QPushButton("Configure Prompt")
        self.settings_btn.setMinimumHeight(35)
        self.settings_btn.clicked.connect(self.open_settings)
        settings_layout.addWidget(self.settings_btn)
        
        self.current_prompt_label = QLabel("Default prompt loaded")
        self.current_prompt_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        settings_layout.addWidget(self.current_prompt_label)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Processing Group
        process_group = QGroupBox("Processing")
        process_layout = QVBoxLayout()
        
        self.process_btn = QPushButton("Start Anonymization")
        self.process_btn.setMinimumHeight(45)
        self.process_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; font-weight: bold; }")
        self.process_btn.clicked.connect(self.start_anonymization)
        self.process_btn.setEnabled(False)
        process_layout.addWidget(self.process_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        process_layout.addWidget(self.progress_label)
        
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        # Results Group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        
        self.download_btn = QPushButton("Download Anonymized Text")
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        self.download_btn.clicked.connect(self.download_results)
        self.download_btn.setEnabled(False)
        results_layout.addWidget(self.download_btn)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.current_prompt = settings.get('prompt', self.default_prompt)
            else:
                self.current_prompt = self.default_prompt
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.current_prompt = self.default_prompt
        
        self.current_prompt_label.setText("Custom prompt loaded" if self.current_prompt != self.default_prompt else "Default prompt loaded")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {'prompt': self.current_prompt}
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_model(self):
        """Browse for and load a model file"""
        # Open file dialog to select model
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            str(Path.home()),
            "GGUF Model files (*.gguf);;All files (*.*)"
        )
        
        if not model_path:
            return  # User cancelled
        
        if not os.path.exists(model_path):
            QMessageBox.warning(self, "Model Not Found", f"Model file not found: {model_path}")
            return
        
        try:
            self.statusBar().showMessage("Loading model...")
            self.load_model_btn.setEnabled(False)
            
            # Clean up previous model
            if self.model:
                del self.model
                self.model = None
            
            # Load new model
            self.model = Llama(
                model_path=model_path,
                n_ctx=4096,  # Context window
                n_threads=4,  # Number of threads
                verbose=False
            )
            
            self.model_status.setText(f"Model loaded: {Path(model_path).name}")
            self.model_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage("Model loaded successfully")
            
            # Enable processing if document is loaded
            if self.original_text:
                self.process_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Model", f"Failed to load model: {str(e)}")
            self.model_status.setText("Error loading model")
            self.model_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.statusBar().showMessage("Error loading model")
        finally:
            self.load_model_btn.setEnabled(True)
    
    def upload_document(self):
        """Upload and process document"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document",
            "",
            "Text files (*.txt);;Word documents (*.docx);;All files (*.*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.docx'):
                    # Read DOCX file
                    doc = Document(file_path)
                    text_content = []
                    for paragraph in doc.paragraphs:
                        text_content.append(paragraph.text)
                    self.original_text = '\n'.join(text_content)
                else:
                    # Read TXT file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.original_text = f.read()
                
                self.file_label.setText(f"Loaded: {Path(file_path).name}")
                self.file_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.statusBar().showMessage(f"Document loaded: {Path(file_path).name}")
                
                # Enable processing if model is loaded
                if self.model:
                    self.process_btn.setEnabled(True)
                
                # Clean up previous results
                self.cleanup_results()
                
            except Exception as e:
                QMessageBox.critical(self, "Error Loading Document", f"Failed to load document: {str(e)}")
                self.statusBar().showMessage("Error loading document")
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks based on # headers"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            if line.strip().startswith('#') and line.strip() != '#':
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append('\n'.join(current_chunk).strip())
                    current_chunk = []
            
            current_chunk.append(line)
        
        # Add the last chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk).strip())
        
        # Filter out empty chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        return chunks
    
    def start_anonymization(self):
        """Start the anonymization process"""
        if not self.model:
            QMessageBox.warning(self, "No Model", "Please load a model first.")
            return
        
        if not self.original_text:
            QMessageBox.warning(self, "No Document", "Please upload a document first.")
            return
        
        # Split text into chunks
        chunks = self.chunk_text(self.original_text)
        
        if not chunks:
            QMessageBox.warning(self, "No Content", "No valid chunks found in the document.")
            return
        
        # Start worker thread
        self.worker = AnonymizationWorker(chunks, self.current_prompt, self.model)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.chunk_processed.connect(self.on_chunk_processed)
        self.worker.finished.connect(self.on_anonymization_finished)
        self.worker.error_occurred.connect(self.on_anonymization_error)
        
        # Update UI
        self.process_btn.setEnabled(False)
        self.process_btn.setText("Processing...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(chunks))
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Processing 0 of {len(chunks)} chunks...")
        
        self.worker.start()
    
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"Processing {current} of {total} chunks...")
        self.statusBar().showMessage(f"Processing chunk {current} of {total}")
    
    def on_chunk_processed(self, original: str, anonymized: str):
        """Handle processed chunk"""
        pass  # Could be used for real-time preview
    
    def on_anonymization_finished(self, anonymized_chunks: List[str]):
        """Handle finished anonymization"""
        self.anonymized_chunks = anonymized_chunks
        
        # Update UI
        self.process_btn.setEnabled(True)
        self.process_btn.setText("Start Anonymization")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.download_btn.setEnabled(True)
        
        self.statusBar().showMessage(f"Anonymization complete! {len(anonymized_chunks)} chunks processed.")
        
        QMessageBox.information(
            self,
            "Anonymization Complete",
            f"Successfully processed {len(anonymized_chunks)} chunks. You can now download the anonymized text."
        )
    
    def on_anonymization_error(self, error_message: str):
        """Handle anonymization error"""
        self.process_btn.setEnabled(True)
        self.process_btn.setText("Start Anonymization")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        QMessageBox.critical(self, "Anonymization Error", f"An error occurred during anonymization: {error_message}")
        self.statusBar().showMessage("Anonymization failed")
    
    def download_results(self):
        """Download anonymized results"""
        if not self.anonymized_chunks:
            QMessageBox.warning(self, "No Results", "No anonymized results to download.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Anonymized Text",
            "anonymized_text.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        
        if file_path:
            try:
                # Combine all chunks
                anonymized_text = '\n\n'.join(self.anonymized_chunks)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(anonymized_text)
                
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"Anonymized text saved to: {file_path}"
                )
                
                # Clean up after download
                self.cleanup_results()
                self.statusBar().showMessage("Results downloaded and cleaned up")
                
            except Exception as e:
                QMessageBox.critical(self, "Download Error", f"Failed to save file: {str(e)}")
    
    def cleanup_results(self):
        """Clean up results and free memory"""
        self.anonymized_chunks = []
        self.download_btn.setEnabled(False)
        
        # Force garbage collection
        import gc
        gc.collect()
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.current_prompt, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_prompt = dialog.get_prompt()
            if new_prompt and new_prompt != self.current_prompt:
                self.current_prompt = new_prompt
                self.current_prompt_label.setText("Custom prompt loaded")
                self.save_settings()
                self.statusBar().showMessage("Settings updated")
    
    def closeEvent(self, event):
        """Handle application close"""
        # Clean up model and results
        if self.model:
            del self.model
            self.model = None
        
        self.cleanup_results()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Text Anonymizer")
    app.setApplicationVersion("1.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = TextAnonymizer()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

