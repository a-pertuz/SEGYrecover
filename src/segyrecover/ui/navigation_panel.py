"""Navigation panel for SEGYRecover application."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, 
    QFrame, QSizePolicy, QStyle
)

class NavButton(QPushButton):
    """Custom navigation button for sidebar."""
    
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFlat(True)
        
        # Set object name based on text for CSS targeting
        self.setObjectName(f"nav_button_{text.lower().replace(' ', '_')}")
        
        self.setProperty("nav_button", True)
        
        # Set icon if provided
        if (icon_name):
            self.setIcon(self.style().standardIcon(icon_name))
        
        # Configure button for smaller screens
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(36)  # Ensure minimum touchable height
        
        # Set text alignment and word wrapping for better display
        self.setStyleSheet("text-align: left; padding: 4px 8px;")
        
class NavigationPanel(QWidget):
    """Side navigation panel with workflow steps."""
    
    # Signal emitted when a navigation item is selected
    navigationChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set size policy for the navigation panel
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setMinimumWidth(180)  # Reduced minimum width
        self.setMaximumWidth(250)
        
        # Create UI elements
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Application title/logo
        title_container = QFrame()
        title_container.setObjectName("nav_header")
        title_container.setFrameShape(QFrame.NoFrame)
        title_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_layout = QVBoxLayout(title_container)
        
        title_label = QLabel("SEGYRecover")
        title_layout.addWidget(title_label)
        
        layout.addWidget(title_container)
        
        # Container for nav buttons (without scroll area)
        nav_container = QFrame()
        nav_container.setObjectName("nav_container")
        nav_container.setFrameShape(QFrame.NoFrame)
        nav_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(4, 8, 4, 8)  # Reduced margins
        nav_layout.setSpacing(2)  # Reduced spacing
        
        # Create navigation buttons
        self.nav_buttons = {}
        
        # Define the navigation items with display names and internal identifiers
        nav_items = [
            ("Welcome", "welcome"),
            ("Image Loading", "image_loading"),
            ("Parameters", "parameters"),
            ("ROI Selection", "roi_selection"),
            ("Digitization", "digitization"),
            ("Results", "results")
        ]
        
        # Add navigation buttons
        for display_name, identifier in nav_items:
            btn = NavButton(display_name)
            btn.setObjectName(f"nav_{identifier}")
            btn.clicked.connect(lambda checked, id=identifier: self._handle_navigation(id))
            nav_layout.addWidget(btn)
            self.nav_buttons[identifier] = btn
        
        # Add spacer at the bottom
        nav_layout.addStretch()
        
        # Version label at bottom
        try:
            from .. import __version__  # Import from package
        except ImportError:
            __version__ = "1.1.3"  # Fallback version
            
        version_label = QLabel(f"v{__version__}")
        version_label.setObjectName("nav_version")
        version_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(version_label)
        
        # Add the nav container to the main layout
        layout.addWidget(nav_container)
        
        # Set default active tab
        self.set_active("welcome")
    
    def _handle_navigation(self, identifier):
        """Handle navigation button click."""
        self.set_active(identifier)
        self.navigationChanged.emit(identifier)
    
    def set_active(self, identifier):
        """Set the active navigation button."""
        for button_id, button in self.nav_buttons.items():
            button.setChecked(button_id == identifier)

    def enable_tab(self, identifier, enabled=True):
        """Enable or disable a specific tab button."""
        if identifier in self.nav_buttons:
            self.nav_buttons[identifier].setEnabled(enabled)
            
    def enable_tabs_until(self, identifier):
        """Enable all tabs up to and including identifier, disable those after."""
        found = False
        for i, (button_id, button) in enumerate(self.nav_buttons.items()):
            if button_id == identifier:
                found = True
            button.setEnabled(not found or button_id == identifier or button_id in ["welcome"])
