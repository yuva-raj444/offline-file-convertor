# PyQt5 UI will be inserted here
import os
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QMessageBox, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from app.file_selector import FileSelector
from utils.format_detector import detect_format, get_supported_target_formats, get_all_supported_source_formats
from converters.document_converter import DocumentConverter
from converters.spreadsheet_converter import SpreadsheetConverter
from converters.presentation_converter import PresentationConverter
from converters.pdf_converter import PdfConverter
from converters.image_converter import ImageConverter
from converters.cross_converter import CrossConverter

# Thread for conversion to prevent UI freeze
class ConversionThread(QThread):
    conversionFinished = pyqtSignal(bool, str) # success, message
    updateProgress = pyqtSignal(str) # message for progress dialog

    def __init__(self, input_path, target_extension):
        super().__init__()
        self.input_path = input_path
        self.target_extension = target_extension

    def run(self):
        self.updateProgress.emit("Starting conversion...")
        source_ext = detect_format(self.input_path)
        
        if not source_ext:
            self.conversionFinished.emit(False, "Could not detect source file format.")
            return

        success = False
        output_file = ""
        message = ""
        
        try:
            # Determine which converter to use
            converter = None
            if source_ext in ['doc', 'docx', 'odt', 'rtf', 'txt']:
                converter = DocumentConverter()
            elif source_ext in ['xls', 'xlsx', 'ods', 'csv']:
                converter = SpreadsheetConverter()
            elif source_ext in ['ppt', 'pptx', 'odp']:
                converter = PresentationConverter()
            elif source_ext == 'pdf':
                converter = PdfConverter()
            elif source_ext in ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'tif', 'svg', 'webp', 'ico', 'heic']:
                converter = ImageConverter()

            if converter:
                self.updateProgress.emit(f"Converting from .{source_ext} to .{self.target_extension}...")
                success, output_file = converter.convert(self.input_path, self.target_extension)
                if not success and output_file is None: # This means it might need cross-conversion
                    cross_converter = CrossConverter()
                    self.updateProgress.emit(f"Attempting cross-category conversion...")
                    success, output_file = cross_converter.convert(self.input_path, source_ext, self.target_extension)
            
            if not success:
                # Fallback to cross-converter if initial specific converter failed or returned None
                if not isinstance(converter, CrossConverter): # Avoid double-trying if already CrossConverter
                    cross_converter = CrossConverter()
                    self.updateProgress.emit(f"Attempting cross-category conversion (fallback)...")
                    success, output_file = cross_converter.convert(self.input_path, source_ext, self.target_extension)

            if success:
                message = f"Conversion successful! Output: {output_file}"
            else:
                message = "Conversion failed or is not supported."

        except Exception as e:
            success = False
            message = f"An error occurred during conversion: {e}"
            print(f"Conversion error: {e}")
        
        self.conversionFinished.emit(success, message)


class ConverterUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Converter App")
        self.setGeometry(100, 100, 600, 300) # (x, y, width, height)
        
        self.file_selector = FileSelector(self)
        self.conversion_thread = None # To hold the QThread instance
        self.progress_dialog = None

        self._setup_ui()
        self._connect_signals()
        self._populate_source_formats() # Populate source formats initially

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Input File Section
        input_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Select a file to convert...")
        self.file_path_input.setReadOnly(True) # User shouldn't type here
        self.browse_button = QPushButton("Browse")
        input_layout.addWidget(self.file_path_input)
        input_layout.addWidget(self.browse_button)
        main_layout.addLayout(input_layout)

        # Format Selection Section
        format_layout = QHBoxLayout()
        
        # Source Format
        source_format_label = QLabel("Source Format:")
        self.source_format_combo = QComboBox()
        self.source_format_combo.setPlaceholderText("Auto-detected")
        self.source_format_combo.setEditable(False) # Not editable, just display
        self.source_format_combo.setEnabled(False) # Initially disabled, updates when file selected

        # Target Format
        target_format_label = QLabel("Target Format:")
        self.target_format_combo = QComboBox()
        self.target_format_combo.setPlaceholderText("Select target...")
        self.target_format_combo.setEnabled(False) # Initially disabled

        format_layout.addWidget(source_format_label)
        format_layout.addWidget(self.source_format_combo)
        format_layout.addSpacing(20)
        format_layout.addWidget(target_format_label)
        format_layout.addWidget(self.target_format_combo)
        main_layout.addLayout(format_layout)

        # Convert Button
        self.convert_button = QPushButton("Convert")
        self.convert_button.setFixedHeight(40)
        self.convert_button.setEnabled(False) # Disabled until file and formats selected
        main_layout.addWidget(self.convert_button)

        # Status Label
        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        main_layout.addWidget(self.status_label)

    def _connect_signals(self):
        self.browse_button.clicked.connect(self.file_selector.open_file_dialog)
        self.file_selector.fileSelected.connect(self._on_file_selected)
        self.file_selector.targetFormatsUpdated.connect(self._on_target_formats_updated)
        self.convert_button.clicked.connect(self._start_conversion)
        self.target_format_combo.currentIndexChanged.connect(self._update_convert_button_state)

    def _populate_source_formats(self):
        """Populates the source format combo box with all supported extensions."""
        all_source_formats = sorted(get_all_supported_source_formats())
        self.source_format_combo.addItem("Auto-detected") # Default option
        self.source_format_combo.addItems(all_source_formats)

    def _on_file_selected(self, file_path):
        """Updates UI when a file is selected."""
        self.file_path_input.setText(file_path)
        if file_path:
            source_ext = detect_format(file_path)
            self.source_format_combo.setCurrentText(source_ext if source_ext else "Auto-detected")
            self.source_format_combo.setEnabled(True)
            self.target_format_combo.setEnabled(True)
            self._update_convert_button_state()
            self.status_label.setText("File selected. Choose target format.")
        else:
            self.source_format_combo.setCurrentIndex(0) # Reset to auto-detected
            self.source_format_combo.setEnabled(False)
            self.target_format_combo.clear()
            self.target_format_combo.setPlaceholderText("Select target...")
            self.target_format_combo.setEnabled(False)
            self.convert_button.setEnabled(False)
            self.status_label.setText("Ready.")

    def _on_target_formats_updated(self, target_formats):
        """Updates the target format combo box based on the detected source format."""
        self.target_format_combo.clear()
        if target_formats:
            self.target_format_combo.addItems(sorted(target_formats))
            self.target_format_combo.setPlaceholderText("Select target...")
            self.target_format_combo.setEnabled(True)
        else:
            self.target_format_combo.setPlaceholderText("No supported conversions")
            self.target_format_combo.setEnabled(False)
        self._update_convert_button_state()

    def _update_convert_button_state(self):
        """Enables/disables the convert button based on selection."""
        file_selected = bool(self.file_path_input.text())
        target_format_selected = self.target_format_combo.currentText() not in ["", "No supported conversions", "Select target..."]
        self.convert_button.setEnabled(file_selected and target_format_selected)

    def _start_conversion(self):
        """Initiates the file conversion process in a separate thread."""
        input_path = self.file_path_input.text()
        target_extension = self.target_format_combo.currentText()

        if not input_path:
            QMessageBox.warning(self, "Input Error", "Please select an input file.")
            return
        if not target_extension:
            QMessageBox.warning(self, "Input Error", "Please select a target format.")
            return

        self.status_label.setText("Conversion in progress...")
        self.convert_button.setEnabled(False) # Disable convert button during conversion

        # Setup progress dialog
        self.progress_dialog = QProgressDialog("Converting...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setCancelButton(None) # No cancel button for simplicity
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setWindowTitle("Converting File")
        self.progress_dialog.show()

        # Start conversion in a new thread
        self.conversion_thread = ConversionThread(input_path, target_extension)
        self.conversion_thread.conversionFinished.connect(self._on_conversion_finished)
        self.conversion_thread.updateProgress.connect(self.progress_dialog.setLabelText)
        self.conversion_thread.start()

    def _on_conversion_finished(self, success, message):
        """Handles the result of the conversion thread."""
        self.convert_button.setEnabled(True) # Re-enable convert button
        self.progress_dialog.close() # Close progress dialog

        if success:
            self.status_label.setText("Conversion Complete!")
            QMessageBox.information(self, "Conversion Result", message)
        else:
            self.status_label.setText("Conversion Failed.")
            QMessageBox.critical(self, "Conversion Result", message)
            
        # Clean up the thread
        if self.conversion_thread:
            self.conversion_thread.quit()
            self.conversion_thread.wait()
            self.conversion_thread = None

