"""Entry point for the SEGYRecover application."""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from .ui.main_window import SegyRecover

if sys.platform.startswith("win"):
    if "-platform" not in sys.argv:
        sys.argv += ["-platform", "windows:darkmode=0"]

def load_stylesheet(app):
    """Load and apply the stylesheet to the application."""
    stylesheet_path = os.path.join(os.path.dirname(__file__), "ui", "theme.qss")
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        return True
    return False

def main():
    """Run the SEGYRecover application."""
    app = QApplication(sys.argv)
    
    if not load_stylesheet(app):
        app.setStyle("Fusion")

        
    app.setFont(QFont("Segoe UI", 10))

    window = SegyRecover()
    window.setWindowTitle('SEGYRecover')
    
    screen = QApplication.primaryScreen().geometry()
    screen_width = min(screen.width(), 1920)
    screen_height = min(screen.height(), 1080)    
    pos_x = int(screen_width * 0.05)
    pos_y = int(screen_height * 0.05)
    window_width = int(screen_width * 0.9)
    window_height = int(screen_height * 0.85)
    
    window.setGeometry(pos_x, pos_y, window_width, window_height)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()