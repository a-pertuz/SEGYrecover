"""Welcome tab for SEGYRecover application."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QHBoxLayout, QSpacerItem, QSizePolicy,
    QToolButton, QGridLayout
)
from .help_dialogs import AboutDialog, HelpDialog

# Fix the import path for version
try:
    from .. import __version__
except ImportError:
    __version__ = "1.1.3"  # Fallback version

class WelcomeTab(QWidget):
    """Welcome tab with application information and start button."""
    
    # Signal emitted when the New Line button is clicked
    newLineRequested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("welcome_tab")
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section with logo placeholder and buttons
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        
        # Logo placeholder - replace this with your actual logo
        logo_label = QLabel()
        logo_label.setObjectName("logo_label")
        # Create a placeholder logo
        logo_pixmap = QPixmap(120, 120)
        logo_pixmap.fill(Qt.transparent)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Title and version in center
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(2)
        
        header = QLabel("SEGYRecover")
        header.setObjectName("header_label")
        header.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(header)
        
        version = QLabel(f"Version {__version__}")
        version.setObjectName("version_label")
        version.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(version)
        
        header_layout.addWidget(title_container, 1)  # 1 = stretch factor
        
        # Info button section
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Help button
        help_button = QPushButton("Help")
        help_button.setObjectName("help_button")
        help_button.setFixedSize(100, 32)
        help_button.clicked.connect(self._show_help)
        info_layout.addWidget(help_button)
        
        # About button
        about_button = QPushButton("About")
        about_button.setObjectName("about_button")
        about_button.setFixedSize(100, 32)
        about_button.clicked.connect(self._show_about)
        info_layout.addWidget(about_button)
        
        header_layout.addWidget(info_container)
        layout.addWidget(header_container)
        
        # Description section
        description = QLabel(
            "SEGYRecover digitizes scanned seismic sections into standard "
            "SEGY format for use in modern interpretation software."
        )
        description.setObjectName("description_label")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setContentsMargins(0, 10, 0, 10)
        layout.addWidget(description)
        
        # Features section with grid layout for better organization
        features_frame = QFrame()
        features_frame.setObjectName("features_frame")
        features_layout = QVBoxLayout(features_frame)
        
        features_title = QLabel("Key Features:")
        features_title.setObjectName("section_label")
        features_layout.addWidget(features_title)
        
        features_label = QLabel(
            "• Import scanned seismic images (TIFF, JPEG, PNG)\n"
            "• Interactive region selection with automatic rectification\n"
            "• Automatic trace line and timeline detection\n"
            "• Frequency filtering and amplitude extraction\n"
            "• Output to standard SEGY format for interpretation software)")
        features_label.setObjectName("features_label")        
        features_layout.addWidget(features_label)

        layout.addWidget(features_frame)
        
        # Quick start and workflow hints
        workflow_container = QFrame()
        workflow_container.setObjectName("workflow_container")
        workflow_layout = QVBoxLayout(workflow_container)

        workflow_title = QLabel("Quick Start:")
        workflow_title.setObjectName("section_label")
        workflow_layout.addWidget(workflow_title)
        
        workflow_text = QLabel(
            "1. Start a new line using the button below\n"
            "2. Load your seismic image (from IMAGES folder)\n"
            "3. Configure parameters or use saved ones\n"
            "4. Select your region of interest\n"
            "5. Run the digitization process\n"
            "6. Export and use your SEGY file"
        )
        workflow_text.setObjectName("workflow_steps")
        workflow_layout.addWidget(workflow_text)
        
        layout.addWidget(workflow_container)
        
        # Start button section
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 5, 0, 5)
        
        # Add spacer to push button to center
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # New Line button
        start_button = QPushButton("Start New Line")
        start_button.setObjectName("start_new_button")
        start_button.setMinimumWidth(200)
        start_button.setMinimumHeight(50)
        start_button.clicked.connect(self.newLineRequested.emit)
        button_layout.addWidget(start_button)
        
        # Add spacer to push button to center
        button_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        layout.addWidget(button_container)
        
        # Add spacer at the bottom
        layout.addStretch()
    
    def _show_help(self):
        """Show the help dialog."""
        help_dialog = HelpDialog(self)
        help_dialog.exec()
    
    def _show_about(self):
        """Show the about dialog."""
        about_dialog = AboutDialog(self)
        about_dialog.exec()
