import os
from PyQt5.QtWidgets import QFileDialog, QApplication, QWidget, QComboBox
from PyQt5.QtCore import pyqtSignal, QObject
from utils.format_detector import get_supported_target_formats, get_all_supported_source_formats, detect_format, get_file_category

class FileSelector(QObject):
    """
    Handles file dialog operations and manages the dropdowns for file formats.
    Emits signals when a file is selected or source format changes.
    """
    fileSelected = pyqtSignal(str) # Emits the selected file path
    targetFormatsUpdated = pyqtSignal(list) # Emits a list of supported target formats

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_source_file = ""

    def open_file_dialog(self):
        """
        Opens a file dialog for the user to select a single file.
        Detects the file format and emits signals for the selected file and
        its supported target formats.
        """
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog # Use this for consistent styling
        
        # Filter for all supported source formats
        all_exts = get_all_supported_source_formats()
        # Create a filter string like "All Supported Files (*.docx *.pdf ...);;All Files (*)"
        filter_str_parts = [f"*.{ext}" for ext in all_exts]
        filter_str = f"All Supported Files ({' '.join(filter_str_parts)})"

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select File to Convert",
            "",
            f"{filter_str};;All Files (*)",
            options=options
        )
        
        if file_path:
            self.current_source_file = file_path
            self.fileSelected.emit(file_path)
            
            source_ext = detect_format(file_path)
            if source_ext:
                target_formats = get_supported_target_formats(source_ext)
                self.targetFormatsUpdated.emit(target_formats)
            else:
                self.targetFormatsUpdated.emit([]) # No target formats if no extension
        else:
            self.current_source_file = ""
            self.fileSelected.emit("")
            self.targetFormatsUpdated.emit([])

    def update_target_formats_from_source_ext(self, source_extension):
        """
        Updates the list of target formats based on the selected source extension
        (e.g., from a source format dropdown).
        """
        if source_extension:
            target_formats = get_supported_target_formats(source_extension)
            self.targetFormatsUpdated.emit(target_formats)
        else:
            self.targetFormatsUpdated.emit([])

