import sys
from PyQt5.QtWidgets import QApplication
from app.main import ConverterUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Converter")
    window = ConverterUI()
    window.show()
    sys.exit(app.exec_())
