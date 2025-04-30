"""Entry point for the SEGYRecover application."""

import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QStyleFactory
from PySide6.QtCore import QTimer

from .ui.main_window import SegyRecover

if sys.platform.startswith("win"):
    if "-platform" not in sys.argv:
        sys.argv += ["-platform", "windows:darkmode=0"]

# Global variables to track stylesheet information
_stylesheet_path = ""
_last_modified_time = 0

def load_stylesheet(app):
    """Load and apply the stylesheet to the application."""
    global _stylesheet_path, _last_modified_time
    
    _stylesheet_path = os.path.join(os.path.dirname(__file__), "ui", "theme.qss")
    if os.path.exists(_stylesheet_path):
        _last_modified_time = os.path.getmtime(_stylesheet_path)
        with open(_stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        return True
    return False

def check_stylesheet_changes(app):
    """Check if the stylesheet has changed and reload if necessary."""
    global _stylesheet_path, _last_modified_time
    
    if not _stylesheet_path or not os.path.exists(_stylesheet_path):
        return
    
    current_mtime = os.path.getmtime(_stylesheet_path)
    if current_mtime > _last_modified_time:
        print(f"Stylesheet changed, reloading...")
        _last_modified_time = current_mtime
        with open(_stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

def main():
    """Run the SEGYRecover application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    # Load and apply the global stylesheet
    load_stylesheet(app)

    # Set up a timer to check for stylesheet changes
    stylesheet_timer = QTimer()
    stylesheet_timer.timeout.connect(lambda: check_stylesheet_changes(app))
    stylesheet_timer.start(1000)  # Check every 1000ms (1 second)

    window = SegyRecover()
    window.setWindowTitle('SEGYRecover')

    #print(QStyleFactory.keys())
    
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