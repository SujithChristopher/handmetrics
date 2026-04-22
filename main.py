import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import HandAnnotationWithMeasurements

def main():
    app = QApplication(sys.argv)
    gui = HandAnnotationWithMeasurements()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
