import os
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QRadioButton, QButtonGroup, QFileDialog,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QPushButton, QGroupBox, QScrollArea, QWidget, QDialog, QDialogButtonBox
)



class AboutDialog(QDialog):
    """Dialog displaying information about the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About SEGYRecover")
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        window_width= int(screen_width * 0.3)
        window_height = int(screen_height * 0.85)
        self.setGeometry(pos_x, pos_y, window_width, window_height)        
        layout = QVBoxLayout(self)
        
        # App icon or logo would go here if available
        title = QLabel("SEGYRecover")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        
        # Version and copyright info
        __version__ = '1.1.0'
        version = QLabel(f"Version {__version__}")
        version.setAlignment(Qt.AlignCenter)
        
        copyright = QLabel("© 2025 Alejandro Pertuz")
        copyright.setAlignment(Qt.AlignCenter)
        
        # Description text
        description = QLabel(
            "A Python tool for digitizing scanned seismic sections\n"
            "and converting them to standard SEGY format."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        
        # License info
        license_info = QLabel("Released under the GPL-3.0 License")
        license_info.setAlignment(Qt.AlignCenter)
        
        # Add all widgets to layout
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(copyright)
        layout.addSpacing(10)
        layout.addWidget(description)
        layout.addSpacing(20)
        layout.addWidget(license_info)
        
        # Add OK button at bottom
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class HelpDialog(QDialog):
    """Help dialog with information about the application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("How to Use SEGYRECOVER")    
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = int(screen_width * 0.45 + 20)
        pos_y = int(screen_height * 0.15)
        window_width= int(screen_width * 0.3)
        window_height = int(screen_height * 0.85)
        self.setGeometry(pos_x, pos_y, window_width, window_height)          
        # Create scroll area
        scroll = QWidget()
        scroll_layout = QVBoxLayout(scroll)
        
        # Add content
        msg = """
        <h2>SEGYRECOVER Tutorial</h2>
        
        <p><b>SEGYRECOVER</b> is a comprehensive tool designed to digitize seismic images into SEGY format.</p>

        <h2> Visualization controls </h2>
        <p> The application provides a set of tools to navigate and interact with the seismic image:</p>
        <h3>Navigation Toolbar</h3>
        <ul>
            <li>🏠 <b>Home:</b> Reset view to original display</li>
            <li>⬅️ <b>Back:</b> Previous view</li>
            <li>➡️ <b>Forward:</b> Next view</li>
            <li>✋ <b>Pan:</b> Left click and drag to move around</li>
            <li>🔍 <b>Zoom:</b> Left click and drag to zoom into a rectangular region</li>
            <li>⚙️ <b>Configure:</b> Configure plot settings</li>
            <li>💾 <b>Save:</b> Save the figure</li>
        </ul>
        
        <h2>SEGYRECOVER Workflow</h2>
        <p>The application follows a step-by-step process to digitize and rectify seismic images:</p>

        <h3>Step 1: Load Image</h3>
        <ul>
            <li>Click "Load Image" to select an image (TIF, JPEG, PNG)</li>
            <li>Images should be in binary format (black and white pixels only)</li>
            <li>The corresponding geometry file  in the GEOMETRY folder will be automatically loaded and displayed</li>
        </ul>

        <h3>Step 2: Set Parameters</h3>
        <ul>
            <li><b>ROI Points</b>: Set trace number and TWT values for the 3 corner points</li>
            <li><b>Acquisition Parameters</b>:
            <ul>
                <li>Sample Rate (DT): Time interval in milliseconds</li> 
                <li>Frequency Band (F1-F4): Filter corners in Hz</li>
            </ul>
            </li>
            <li><b>Detection Parameters</b>:
            <ul>
                <li>TLT: Thickness in pixels of vertical trace lines</li>
                <li>HLT: Thickness in pixels of horizontal time lines</li>
                <li>HE: Erosion size for horizontal features</li>
                <li><b>Advanced parameters:</b></li>
                <li>BDB: Begining of baseline detection range in pixels from the top</li>
                <li>BDE: End of bÝaseline detection range in pixels from the top</li>
                <li>BFT: Baseline filter threshold</li>
            </ul>
            </li>
        </ul>

        <h3>Step 3: Region Selection</h3>
        <ul>
            <li>Click "Begin Digitization" and select 3 points on the image using <b>right-click</b>:</li>
            <ol>
                <li>Top-left corner (P1)</li>
                <li>Top-right corner (P2)</li>
                <li>Bottom-left corner (P3)</li>
            </ol>
            </li>
            <li>Zoom using the navigation toolbar to select points accurately</li>
            <li>The fourth corner will be calculated automatically</li>
            <li>The selected region will be rectified and displayed</li>
        </ul>

        <h3>Step 4: Processing</h3>
        <ul>
            <li>Process will continue with the following steps:</li>
            <li>Timeline detection and removal</li>
            <li>Baseline detection: a window will appear for quality control</li>
            <li>Amplitude extraction</li>
            <li>Data resampling and filtering</li>
            <li>Coordinate assignment</li>
            <li>SEGY file creation</li>
        </ul>

        <h3>Step 5: Results</h3>
        <ul>
            <li>Displays the digitized SEGY section</li>
            <li>Shows the average amplitude spectrum</li>
            <li>Creates SEGY file in the SEGY folder</li>
        </ul>

        <h3>File Structure</h3>
        <ul>
            <li><b>IMAGES/</b>: Store input seismic images</li>
            <li><b>GEOMETRY/</b>: Store .geometry files with trace coordinates</li>
            <li><b>ROI/</b>: Store region of interest points</li>
            <li><b>PARAMETERS/</b>: Store processing parameters</li>
            <li><b>SEGY/</b>: Store output SEGY files</li>
        </ul>
        """
        
        # Create text label with HTML content
        text = QLabel(msg)
        text.setWordWrap(True)
        text.setTextFormat(Qt.RichText)
        scroll_layout.addWidget(text)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll)
        scroll_area.setWidgetResizable(True)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)

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
        window_width= int(screen_width * 0.3)
        window_height = int(screen_height * 0.4)
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        self.setGeometry(pos_x, pos_y, window_width, window_height)          
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # Welcome heading
        welcome_label = QLabel("Welcome to SEGYRecover!", self)
        welcome_label.setFont(QFont("Arial", 18, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Description
        description = QLabel(
            "Choose where you'd like to store your data files.\n"
            "You can change this later in the application settings.\n", 
            self
        )
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)
        layout.addSpacing(20)
        
        # Location options group
        location_group = QGroupBox("Data Storage Location", self)
        location_layout = QVBoxLayout()
        
        # Radio button group
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
        self.custom_radio = QRadioButton("Custom location:" , self)
        self.location_btn_group.addButton(self.custom_radio, 3)
        custom_layout.addWidget(self.custom_radio)
        
        self.browse_btn = QPushButton("Browse...", self)
        self.browse_btn.clicked.connect(self.browse_location)
        custom_layout.addWidget(self.browse_btn)
        
        location_layout.addLayout(custom_layout)
        
        # Selected path display
        self.path_label = QLabel("", self)
        location_layout.addWidget(self.path_label)
        
        location_group.setLayout(location_layout)
        layout.addWidget(location_group)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.continue_btn = QPushButton("Continue", self)
        self.continue_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.continue_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
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
        elif button == self.documents_radio:
            self.selected_location = os.path.join(os.path.expanduser("~"), "Documents", "SEGYRecover")
        elif button == self.custom_radio and self.custom_location:
            self.selected_location = self.custom_location
    
    def get_selected_location(self):
        """Return the user's selected location."""
        return self.selected_location
