"""Entry point for the SEGYRecover application."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import QFile, QTextStream
from .ui.main_window import SegyRecover

def main():
    """Run the SEGYRecover application."""
    app = QApplication(sys.argv)


    
    # Load and apply stylesheet
    style_file = QFile(os.path.join(os.path.dirname(__file__), "ui", "theme.qss"))
    if style_file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(style_file)
        app.setStyleSheet(stream.readAll())
        style_file.close()
    else:
        print("Warning: Could not load stylesheet")
        app.setStyle("windowsvista")
        app.setFont(QFont("Segoe UI", 10))

    window = SegyRecover()
    window.setWindowTitle('SEGYRecover')
    screen = QApplication.primaryScreen().geometry()
    screen_width = min(screen.width(), 1920)
    screen_height = min(screen.height(), 1080)
    pos_x = int(screen_width * 0.05)
    pos_y = int(screen_height * 0.05)
    window_width= int(screen_width * 0.3)
    window_height = int(screen_height * 0.9)
    window.setGeometry(pos_x, pos_y, window_width, window_height)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
