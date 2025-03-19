"""Custom widgets for the SEGYRecover application."""

from PySide6.QtWidgets import QStyle, QPushButton, QApplication, QStatusBar, QProgressBar, QLabel, QHBoxLayout, QWidget


class ProgressStatusBar(QStatusBar):
    """Status bar with integrated progress bar."""

    def __init__(self, parent=None):
        """Initialize the progress status bar."""
        super().__init__(parent)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(200)
        
        # Create cancel button
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel)
        
        # Add widgets to status bar
        self.addPermanentWidget(self.progress_bar)
        self.addPermanentWidget(self.cancel_button)
        
        self._canceled = False
        
    def start(self, title, maximum):
        self._canceled = False
        self.showMessage(title)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        QApplication.processEvents()
        
    def update(self, value, message=None):
        if message:
            self.showMessage(message)
        self.progress_bar.setValue(value)
        QApplication.processEvents()
        
    def finish(self):
        self.clearMessage()
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
    
    def wasCanceled(self):
        """Check if the operation was canceled."""
        return self._canceled
    
    def cancel(self):
        """Cancel the current operation."""
        self._canceled = True