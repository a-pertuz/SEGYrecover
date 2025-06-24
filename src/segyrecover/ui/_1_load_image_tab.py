"""Load Image tab for SEGYRecover application."""

import os
import numpy as np
import cv2
from scipy.ndimage import zoom
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSplitter, QFileDialog, QMessageBox, QGroupBox, QStyle
)
from PySide6.QtGui import QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from ..utils.console_utils import section_header, info_message, error_message, success_message

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
    # Define which tools to keep
    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class LoadImageTab(QWidget):
    """Tab for loading and displaying seismic images."""
    
    # Signals
    imageLoaded = Signal(str, object)  # path, image_array
    proceedRequested = Signal()
    
    def __init__(self, console, work_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("load_image_tab")
        self.console = console
        self.work_dir = work_dir
        self.image_path = None
        self.img_array = None
        
        # Create image canvases
        self.image_figure = plt.figure()
        self.image_canvas = FigureCanvas(self.image_figure)
        self.image_canvas.setObjectName("image_canvas")
        self.image_ax = self.image_figure.add_subplot(111)
        
        # Create location figure with constrained layout to avoid overflow
        self.location_figure = plt.figure(constrained_layout=True)
        self.location_canvas = FigureCanvas(self.location_figure)
        self.location_canvas.setObjectName("location_canvas")
        self.location_ax = self.location_figure.add_subplot(111)
        self.location_ax.set_xlabel('UTM X')
        self.location_ax.set_ylabel('UTM Y')
        self.location_ax.grid(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header = QLabel("Load Seismic Image")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel(
            "Select a seismic image file (TIFF, JPEG, PNG) to begin the digitization process.\n"
            "The corresponding geometry file from the GEOMETRY folder will be loaded automatically if available."
        )
        instruction.setObjectName("description_label")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("content_splitter")
        splitter.setHandleWidth(6)  
        
        # Left panel - Image display
        image_container = QGroupBox("Seismic Image")
        image_container.setObjectName("image_container")
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(15, 15, 15, 15)
        image_layout.setSpacing(10)
        
        image_layout.addWidget(self.image_canvas)
        image_toolbar = SimpleNavigationToolbar(self.image_canvas, self)
        image_toolbar.setObjectName("image_toolbar")
        image_layout.addWidget(image_toolbar)
        
        # Right panel - Location plot
        location_container = QGroupBox("Location Plot")
        location_container.setObjectName("location_container")
        location_layout = QVBoxLayout(location_container)
        location_layout.setContentsMargins(15, 15, 15, 15)
        location_layout.setSpacing(10)
        
        location_layout.addWidget(self.location_canvas)
        location_toolbar = SimpleNavigationToolbar(self.location_canvas, self)
        location_toolbar.setObjectName("location_toolbar")
        location_layout.addWidget(location_toolbar)
        
        # Add panels to splitter
        splitter.addWidget(image_container)
        splitter.addWidget(location_container)
        splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        layout.addWidget(splitter, 1)  # 1 = stretch factor

        # Button section at the bottom for consistency with other tabs
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        
        # Add spacer to push buttons to the right
        button_layout.addStretch()
        
        # Load button
        self.load_button = QPushButton("Load Image")
        self.load_button.setObjectName("load_button")
        self.load_button.setIcon(QIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon)))
        self.load_button.setMinimumWidth(150)
        self.load_button.setFixedHeight(36)
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)
        
        # Next button with fixed width
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("next_button")
        self.next_button.setMinimumWidth(100)
        self.next_button.setFixedHeight(36)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.next_button)
        
        layout.addWidget(button_container)
    
    def load_image(self):
        """Open file dialog to select and load an image."""
        # Start in the IMAGES folder of the script directory
        images_dir = os.path.join(self.work_dir, "IMAGES")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Seismic Image File",
            images_dir,
            "Image Files (*.tif *.jpg *.png);;All Files (*.*)"
        )
        
        if not file_path:
            return False
            
        section_header(self.console, "IMAGE LOADING")
        info_message(self.console, f"Loading image: {file_path}")
        
        try:
            # Load image directly in this tab
            img_array = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img_array is None:
                error_message(self.console, "Could not load image")
                QMessageBox.warning(self, "Error", "Could not load image.")
                return False

            self.image_path = file_path
            self.img_array = img_array
            
            # Display image with reduced resolution
            self._display_image()
            
            # Load and display geometry data
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            self._load_geometry_data(base_name)
            
            success_message(self.console, f"Image loaded: {os.path.basename(file_path)}")
            info_message(self.console, f"Dimensions: {img_array.shape[1]}x{img_array.shape[0]} pixels")
            
            # Enable next button
            self.next_button.setEnabled(True)
            
            # Emit signal with loaded image information
            self.imageLoaded.emit(self.image_path, self.img_array)
            
            return True
            
        except Exception as e:
            error_message(self.console, f"Error loading image: {str(e)}")
            return False
    
    def _display_image(self):
        """Display image at reduced resolution."""
        # Clear previous content
        self.image_ax.clear()
        
        # Create downsampled version for better performance
        display_img = zoom(self.img_array, 0.25, order=1, prefilter=True)
        
        # Display the image
        self.image_ax.imshow(display_img, cmap='gray')
        self.image_ax.set_title("Seismic Image")
        self.image_ax.axis('off')
        self.image_figure.tight_layout()
        self.image_canvas.draw()
    
    def _load_geometry_data(self, base_name):
        """Load and display geometry data."""
        # Clear previous coordinate display
        self.location_ax.clear()
        self.location_ax.set_xlabel('UTM X')
        self.location_ax.set_ylabel('UTM Y')
        self.location_ax.grid(True)
        self.location_ax.set_title("COORDINATES")
        
        geometry_file = os.path.join(self.work_dir, 'GEOMETRY', f'{base_name}.geometry')
        
        if not os.path.exists(geometry_file):
            error_message(self.console, "Geometry file not found.")
            self.location_canvas.draw()
            return False
            
        try:
            cdp, x, y = [], [], []
            with open(geometry_file, 'r') as file:
                for line in file:
                    parts = line.strip().split()
                    cdp.append(parts[0])
                    x.append(float(parts[1]))
                    y.append(float(parts[2]))
                    
            # Plot coordinates
            self.location_ax.plot(x, y, marker='o', markersize=2, color='red', linestyle='-')
            
            # Add labels with threshold to avoid overcrowding
            threshold = 1000
            annotated_positions = []
            for i, txt in enumerate(cdp):
                position = (x[i], y[i])
                if all(np.linalg.norm(np.array(position) - np.array(p)) > threshold 
                      for p in annotated_positions):
                    self.location_ax.annotate(txt, position)
                    annotated_positions.append(position)
                    
            self.location_ax.set_title(f"COORDINATES \"{base_name}\"")
            self.location_ax.set_aspect('equal', adjustable='datalim')
            
            # Rotate x-axis labels to prevent overlap
            plt.setp(self.location_ax.get_xticklabels(), rotation=45, ha='right')
            
            # Use constrained_layout to avoid overflow issues
            self.location_figure.set_constrained_layout(True)
            self.location_canvas.draw()
            
            success_message(self.console, "Geometry data loaded successfully")
            return True

        except Exception as e:
            error_message(self.console, f"Error loading geometry: {str(e)}")
            return False

    def reset(self):
        """Reset the tab to its initial state."""
        # Clear the image path and array
        self.image_path = None
        self.img_array = None
        
        # Clear image display
        self.image_ax.clear()
        self.image_ax.set_title("No Image Loaded")
        self.image_ax.text(0.5, 0.5, "Click 'Load Image' to begin", 
                           ha='center', va='center', transform=self.image_ax.transAxes)
        self.image_ax.axis('off')
        self.image_figure.tight_layout()
        self.image_canvas.draw()
        
        # Clear location display
        self.location_ax.clear()
        self.location_ax.set_xlabel('UTM X')
        self.location_ax.set_ylabel('UTM Y')
        self.location_ax.grid(True)
        self.location_ax.set_title("COORDINATES")
        self.location_ax.text(0.5, 0.5, "No geometry data available", 
                              ha='center', va='center', transform=self.location_ax.transAxes)
        self.location_figure.set_constrained_layout(True)
        self.location_canvas.draw()
        
        # Disable next button
        self.next_button.setEnabled(False)
