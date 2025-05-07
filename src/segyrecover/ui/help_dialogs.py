import os
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QRadioButton, QButtonGroup, QFileDialog,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QPushButton, QGroupBox, QScrollArea, QWidget, QDialog, QDialogButtonBox,
    QFrame
)

from .. import __version__


class AboutDialog(QDialog):
    """Dialog displaying information about the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About SEGYRecover")
        
        # Fix window sizing and positioning
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        window_width = int(screen_width * 0.3)
        window_height = int(screen_height * 0.4)  # Smaller height
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        self.setGeometry(pos_x, pos_y, window_width, window_height)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # App logo placeholder
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Title with better styling
        title = QLabel("SEGYRecover")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(title)
        
        # Version and copyright info with better styling
        version_label = QLabel(f"Version {__version__}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        copyright = QLabel("© 2025 Alejandro Pertuz")
        copyright.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Description text with better styling
        description = QLabel(
            "A Python tool for digitizing scanned seismic sections\n"
            "and converting them to standard SEGY format."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # License info with styled frame
        license_frame = QFrame()
        license_layout = QVBoxLayout(license_frame)
        
        license_info = QLabel("Released under the GPL-3.0 License")
        license_info.setAlignment(Qt.AlignCenter)
        license_layout.addWidget(license_info)
        
        layout.addWidget(license_frame)
        layout.addStretch()
        
        # Button styling
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class HelpDialog(QDialog):
    """Help dialog with information about the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("How to Use SEGYRecover")    
        
        # Fix window sizing and positioning
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        window_width = int(screen_width * 0.4)  # Slightly wider for better readability
        window_height = int(screen_height * 0.75)  # Not too tall
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        self.setGeometry(pos_x, pos_y, window_width, window_height)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("SEGYRecover Help Guide")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        header_layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        
        main_layout.addWidget(header_container)
        main_layout.addWidget(separator)
        
        # Create scroll area with custom styling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Content widget with styled sections
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(5, 10, 15, 10)  # Adjusted for scrollbar
        
        # Introduction section
        intro_frame = self._create_section_frame()
        intro_layout = QVBoxLayout(intro_frame)
        
        intro_title = QLabel("Introduction")
        intro_title.setFont(QFont("Arial", 14, QFont.Bold))
        intro_layout.addWidget(intro_title)
        
        intro_text = QLabel(
            "<p><b>SEGYRecover</b> is a comprehensive tool designed to digitize seismic images into SEGY format. "
            "This guide will help you use the application effectively.</p>"
        )
        intro_text.setTextFormat(Qt.RichText)
        intro_text.setWordWrap(True)
        intro_layout.addWidget(intro_text)
        
        content_layout.addWidget(intro_frame)
        
        # Navigation section
        nav_frame = self._create_section_frame()
        nav_layout = QVBoxLayout(nav_frame)
        
        nav_title = QLabel("Visualization Controls")
        nav_title.setFont(QFont("Arial", 14, QFont.Bold))
        nav_layout.addWidget(nav_title)
        
        nav_text = QLabel(
            "<p>The application provides a set of tools to navigate and interact with the seismic image:</p>"
            "<h4 style='margin-top: 10px; margin-bottom: 6px;'>Navigation Toolbar</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>🏠 <b>Home:</b> Reset view to original display</li>"
            "<li>⬅️ <b>Back:</b> Previous view</li>"
            "<li>➡️ <b>Forward:</b> Next view</li>"
            "<li>✋ <b>Pan:</b> Left click and drag to move around</li>"
            "<li>🔍 <b>Zoom:</b> Left click and drag to zoom into a rectangular region</li>"
            "<li>⚙️ <b>Configure:</b> Configure plot settings</li>"
            "<li>💾 <b>Save:</b> Save the figure</li>"
            "</ul>"
        )
        nav_text.setTextFormat(Qt.RichText)
        nav_text.setWordWrap(True)
        nav_layout.addWidget(nav_text)
        
        content_layout.addWidget(nav_frame)
        
        # Workflow section
        workflow_frame = self._create_section_frame()
        workflow_layout = QVBoxLayout(workflow_frame)
        
        workflow_title = QLabel("SEGYRecover Workflow")
        workflow_title.setFont(QFont("Arial", 14, QFont.Bold))
        workflow_layout.addWidget(workflow_title)
        
        workflow_text = QLabel(
            "<p>The application follows a step-by-step process through a series of tabs to digitize and rectify seismic images:</p>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>Welcome Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>View basic information about SEGYRecover</li>"
            "<li>Click the \"Start New Line\" button to begin the digitization process</li>"
            "</ul>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>1. Load Image Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>Click \"Load Image\" to select an image (TIF, JPEG, PNG)</li>"
            "<li>Images should be in binary format (black and white pixels only)</li>"
            "<li>The corresponding geometry file in the GEOMETRY folder will be automatically loaded and displayed</li>"
            "<li>Click \"Next\" to move to the Parameters tab</li>"
            "</ul>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>2. Parameters Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li><b>ROI Points</b>: Set trace number and TWT values for the 3 corner points</li>"
            "<li><b>Acquisition Parameters</b>:"
            "<ul>"
            "<li>Sample Rate (DT): Time interval in milliseconds</li>"
            "<li>Frequency Band (F1-F4): Filter corners in Hz</li>"
            "</ul>"
            "</li>"
            "<li><b>Detection Parameters</b>:"
            "<ul>"
            "<li>TLT: Thickness in pixels of vertical trace lines</li>"
            "<li>HLT: Thickness in pixels of horizontal time lines</li>"
            "<li>HE: Erosion size for horizontal features</li>"
            "<li><b>Advanced parameters:</b></li>"
            "<li>BDB: Beginning of baseline detection range in pixels from the top</li>"
            "<li>BDE: End of baseline detection range in pixels from the top</li>"
            "<li>BFT: Baseline filter threshold</li>"
            "</ul>"
            "</li>"
            "<li>Click \"Save Parameters\" to save settings, then \"Next\" to continue</li>"
            "</ul>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>3. ROI Selection Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>Select 3 corner points on the image using the buttons provided:"
            "<ol>"
            "<li>Top-left corner (P1)</li>"
            "<li>Top-right corner (P2)</li>"
            "<li>Bottom-left corner (P3)</li>"
            "</ol>"
            "</li>"
            "<li>Use the navigation toolbar to zoom for accurate point selection</li>"
            "<li>The fourth corner will be calculated automatically</li>"
            "<li>The selected region will be rectified and displayed in the right panel</li>"
            "<li>Click \"Next\" to move to the Digitization tab</li>"
            "</ul>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>4. Digitization Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>View the processing steps visually represented at the top of the tab</li>"
            "<li>Click \"Start Digitization\" to begin processing</li>"
            "<li>The process will proceed through these steps automatically:"
            "<ol>"
            "<li>Timeline Removal</li>"
            "<li>Baseline Detection</li>"
            "<li>Amplitude Extraction</li>"
            "<li>Resampling & Filtering</li>"
            "<li>SEGY Creation</li>"
            "</ol>"
            "</li>"
            "<li>Progress is shown in visualization tabs that update during processing</li>"
            "<li>When complete, click \"See Results\" to move to the Results tab</li>"
            "</ul>"
            
            "<h4 style='margin-top: 15px; margin-bottom: 6px;'>5. Results Tab</h4>"
            "<ul style='margin-top: 0px;'>"
            "<li>Displays the digitized SEGY section in the left panel</li>"
            "<li>Shows the average amplitude spectrum in the right panel</li>"
            "<li>Change display type using the dropdown (Variable Density/Wiggle)</li>"
            "<li>View file information including size and dimensions</li>"
            "<li>Click \"Start New Line\" to process another seismic image</li>"
            "</ul>"
        )
        workflow_text.setTextFormat(Qt.RichText)
        workflow_text.setWordWrap(True)
        workflow_layout.addWidget(workflow_text)
        
        content_layout.addWidget(workflow_frame)
        
        # File Structure section
        file_frame = self._create_section_frame()
        file_layout = QVBoxLayout(file_frame)
        
        file_title = QLabel("File Structure")
        file_title.setFont(QFont("Arial", 14, QFont.Bold))
        file_layout.addWidget(file_title)
        
        file_text = QLabel(
            "<p>SEGYRecover organizes data in the following folders:</p>"
            "<ul>"
            "<li><b>IMAGES/</b>: Store input seismic images</li>"
            "<li><b>GEOMETRY/</b>: Store .geometry files with trace coordinates</li>"
            "<li><b>ROI/</b>: Store region of interest points</li>"
            "<li><b>PARAMETERS/</b>: Store processing parameters</li>"
            "<li><b>SEGY/</b>: Store output SEGY files</li>"
            "</ul>"
        )
        file_text.setTextFormat(Qt.RichText)
        file_text.setWordWrap(True)
        file_layout.addWidget(file_text)
        
        content_layout.addWidget(file_frame)
        
        # Add spacer at the bottom
        content_layout.addStretch()
        
        # Set the content widget in the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Button section
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.setFixedSize(100, 32)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addWidget(button_container)
    
    def _create_section_frame(self, bg_color="#ffffff"):
        """Create a styled frame for a help section."""
        frame = QFrame()
        return frame


class FirstRunDialog(QDialog):
    """Dialog shown on first run to configure application settings."""
    
    def __init__(self, parent=None, default_location=None):
        super().__init__(parent)
        self.selected_location = default_location
        self.custom_location = None
        
        self.setWindowTitle("Welcome to SEGYRecover")
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        window_width = int(screen_width * 0.3)
        window_height = int(screen_height * 0.45)  # Slightly taller for better spacing
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        self.setGeometry(pos_x, pos_y, window_width, window_height)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Welcome heading with improved styling
        welcome_label = QLabel("Welcome to SEGYRecover!", self)
        welcome_label.setFont(QFont("Arial", 20, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Description with improved styling
        description = QLabel(
            "Choose where you'd like to store your data files.\n"
            "You can change this later in the application settings.", 
            self
        )
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        
        # Separator line for visual organization
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Location options group with improved styling
        location_group = QGroupBox("Data Storage Location", self)
        location_layout = QVBoxLayout(location_group)
        location_layout.setSpacing(12)
        
        # Radio button group with improved styling
        self.location_btn_group = QButtonGroup(self)
        
        # Default location option (from appdirs)
        self.default_radio = QRadioButton("Default location (system-managed)", self)
        self.default_radio.setToolTip(f"Store in: {self.selected_location}")
        self.location_btn_group.addButton(self.default_radio, 1)
        location_layout.addWidget(self.default_radio)
        
        # Documents folder option
        documents_path = os.path.join(os.path.expanduser("~"), "Documents", "SEGYRecover")
        self.documents_radio = QRadioButton(f"Documents folder: {documents_path}", self)
        self.location_btn_group.addButton(self.documents_radio, 2)
        location_layout.addWidget(self.documents_radio)
        
        # Custom location option
        custom_layout = QHBoxLayout()
        self.custom_radio = QRadioButton("Custom location:", self)
        self.location_btn_group.addButton(self.custom_radio, 3)
        custom_layout.addWidget(self.custom_radio)
        
        self.browse_btn = QPushButton("Browse...", self)
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.clicked.connect(self.browse_location)
        custom_layout.addWidget(self.browse_btn)
        
        location_layout.addLayout(custom_layout)
        
        # Selected path display with styled frame
        path_frame = QFrame()
        path_layout = QVBoxLayout(path_frame)
        path_layout.setContentsMargins(8, 8, 8, 8)
        
        self.path_label = QLabel("No custom location selected", self)
        self.path_label.setWordWrap(True)
        path_layout.addWidget(self.path_label)
        
        location_layout.addWidget(path_frame)
        layout.addWidget(location_group)
        
        # Info text with styled frame
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        
        info_text = QLabel(
            "After selecting a location, the application will create necessary folders to store "
            "your images, parameters, and SEGY files.", 
            self
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_frame)
        
        # Add spacer
        layout.addStretch()
        
        # Buttons with improved styling
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.continue_btn = QPushButton("Continue", self)
        self.continue_btn.setFixedSize(120, 36)
        self.continue_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.continue_btn)
        
        layout.addLayout(button_layout)
        
        # Set default selection
        self.default_radio.setChecked(True)
        self.location_btn_group.buttonClicked.connect(self.update_selection)
    
    def browse_location(self):
        """Open file dialog to select custom location."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory for SEGYRecover Data",
            os.path.expanduser("~")
        )
        
        if directory:
            self.custom_location = os.path.join(directory, "SEGYRecover")
            self.path_label.setText(f"Selected: {self.custom_location}")
            self.custom_radio.setChecked(True)
            self.update_selection(self.custom_radio)
    
    def update_selection(self, button):
        """Update the selected location based on radio button choice."""
        if button == self.default_radio:
            self.selected_location = self.selected_location
            self.path_label.setText("Using system default location")
        elif button == self.documents_radio:
            self.selected_location = os.path.join(os.path.expanduser("~"), "Documents", "SEGYRecover")
            self.path_label.setText(f"Selected: {self.selected_location}")
        elif button == self.custom_radio and self.custom_location:
            self.selected_location = self.custom_location
            self.path_label.setText(f"Selected: {self.custom_location}")
    
    def get_selected_location(self):
        """Return the user's selected location."""
        return self.selected_location
