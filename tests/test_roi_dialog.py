"""Test script for the ROISelectionDialog with sample images."""
import os
import sys
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QApplication

import os
import sys
import math
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPolygonF, QIntValidator
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import (QRadioButton, QButtonGroup, QFileDialog,
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QMessageBox, QScrollArea, QWidget, QDialog, QDialogButtonBox
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import zoom


class ROISelectionDialog(QDialog):
    """Dialog for selecting region of interest on an image."""
    
    # Maximum image dimension for display (pixels)
    MAX_DISPLAY_DIMENSION = 1200
    # Minimum image dimension for display (pixels)
    MIN_DISPLAY_DIMENSION = 400
    # Maximum downsampling factor allowed
    MAX_DOWNSAMPLE_FACTOR = 10
    
    def __init__(self, image, downsample_factor=None):
        super().__init__()
        self.setWindowTitle("Select Region of Interest")
        self.setGeometry(100, 100, 800, 600)
        
        # Store original image and dimensions
        self.original_image = image
        self.original_height, self.original_width = image.shape
        
        # Calculate adaptive downsampling factor if not provided
        if downsample_factor is None:
            downsample_factor = self._calculate_adaptive_downsample_factor()
        else:
            # Validate the provided downsample factor
            downsample_factor = self._validate_downsample_factor(downsample_factor)
        
        self.downsample_factor = downsample_factor
        
        try:
            # Create downsampled image for display
            self.display_image = self.downsample_image(image, downsample_factor)
            self.initial_display_image = self.display_image.copy()  # Store copy for retry
        except MemoryError:
            # Handle extremely large images that cause memory issues
            QMessageBox.warning(
                self, 
                "Memory Warning", 
                "The image is too large to process. Increasing downsampling factor."
            )
            self.downsample_factor = min(self.downsample_factor * 2, self.MAX_DOWNSAMPLE_FACTOR)
            self.display_image = self.downsample_image(image, self.downsample_factor)
            self.initial_display_image = self.display_image.copy()
            
        self.display_height, self.display_width = self.display_image.shape
        
        # Calculate marker and annotation size based on downsampling
        self.marker_size = max(5, int(20 / self.downsample_factor))
        self.line_width = max(1, int(2 / math.sqrt(self.downsample_factor)))
        self.annotation_offset = max(5, int(10 / math.sqrt(self.downsample_factor)))
        
        # Store points and active point index
        self.points = []
        self.active_point_index = None
        self.is_selection_mode = False
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create canvas for image display
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.StrongFocus) 
        self.ax = self.figure.add_subplot(111)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        
        # Display the downsampled image and connect mouse event
        self.ax.imshow(self.display_image, cmap='gray')
        self.click_cid = self.canvas.mpl_connect('button_press_event', self.on_click)
        layout.addWidget(self.canvas)
        
        # Add downsampling indicator
        if downsample_factor > 1:
            self.resolution_label = QLabel(
                f"⚠️ Image displayed at reduced resolution ({100/downsample_factor:.1f}%). "
                f"Point selection still works at full resolution."
            )
            self.resolution_label.setStyleSheet("color: orange;")
            layout.addWidget(self.resolution_label)
        
        # Instructions label
        self.instruction_label = QLabel(
            "Use the tools below to select the region of interest. "
            "Use the navigation toolbar to zoom and pan as needed before selecting points."
        )
        layout.addWidget(self.instruction_label)
        
        # Status label for showing current action
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(self.status_label)
        
        # Point selection buttons
        points_group = QGroupBox("Select Points")
        points_layout = QHBoxLayout()
        
        # Create point selection buttons
        self.point_buttons = []
        self.point_labels = ["Top-Left (1)", "Top-Right (2)", "Bottom-Left (3)"]
        
        for i, label in enumerate(self.point_labels):
            button = QPushButton(label)
            button.setToolTip(f"Click to select the {label.split('(')[0].strip()} corner of the region")
            button.clicked.connect(lambda checked, idx=i: self.activate_point_selection(idx))
            points_layout.addWidget(button)
            self.point_buttons.append(button)
        
        points_group.setLayout(points_layout)
        layout.addWidget(points_group)
        
        # Button layout for main actions
        button_layout = QHBoxLayout()
        
        # Accept button (initially disabled)
        self.accept_button = QPushButton("Accept Selection")
        self.accept_button.setEnabled(False)
        self.accept_button.clicked.connect(self.accept)
        
        # Retry button
        self.retry_button = QPushButton("Retry All")
        self.retry_button.clicked.connect(self.retry)
        
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.retry_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Update UI state
        self.update_ui_state()


    def _calculate_adaptive_downsample_factor(self):
        """Calculate an adaptive downsampling factor based on image size."""
        # Get max dimension of image
        max_dim = max(self.original_height, self.original_width)
        
        # No downsampling needed for small images
        if max_dim <= self.MAX_DISPLAY_DIMENSION:
            return 1
            
        # Calculate factor to make the largest dimension fit within MAX_DISPLAY_DIMENSION
        factor = max(1, math.ceil(max_dim / self.MAX_DISPLAY_DIMENSION))
        
        # Ensure the factor isn't too large
        return min(factor, self.MAX_DOWNSAMPLE_FACTOR)
    
    def _validate_downsample_factor(self, factor):
        """Validate and adjust the downsampling factor if needed."""
        if factor <= 0:
            factor = 1
            
        # Check if the resulting image would be too small
        min_dim = min(self.original_height // factor, self.original_width // factor)
        if min_dim < self.MIN_DISPLAY_DIMENSION:
            # Adjust factor to maintain minimum dimension
            adjusted_factor = min(
                self.original_height // self.MIN_DISPLAY_DIMENSION,
                self.original_width // self.MIN_DISPLAY_DIMENSION
            )
            factor = max(1, adjusted_factor)
            
        return min(factor, self.MAX_DOWNSAMPLE_FACTOR)

    def downsample_image(self, image, factor):
        """Downsample image using a high-quality method."""
        if factor <= 1:
            return image
            
        try:
            # Use zoom for better quality downsampling
            scale_factor = 1.0 / factor
            return zoom(image, scale_factor, order=1, prefilter=True)
        except MemoryError:
            # Fallback to simpler method if memory error occurs
            return image[::factor, ::factor]

    def display_to_original(self, x, y):
        """Convert coordinates from display to original image space with proper rounding."""
        if x is None or y is None:
            return None, None
            
        # Use more precise scaling with rounding
        orig_x = round(x * self.downsample_factor)
        orig_y = round(y * self.downsample_factor)
        
        # Ensure coordinates remain within original image bounds
        orig_x = max(0, min(orig_x, self.original_width - 1))
        orig_y = max(0, min(orig_y, self.original_height - 1))
        
        return orig_x, orig_y

    def original_to_display(self, x, y):
        """Convert coordinates from original to display image space with proper rounding."""
        if x is None or y is None:
            return None, None
            
        # Use more precise scaling with rounding
        display_x = round(x / self.downsample_factor)
        display_y = round(y / self.downsample_factor)
        
        # Ensure coordinates remain within display image bounds
        display_x = max(0, min(display_x, self.display_width - 1))
        display_y = max(0, min(display_y, self.display_height - 1))
        
        return display_x, display_y

    def activate_point_selection(self, point_idx):
        """Activate point selection mode for the specific point."""
        # Disable all point buttons
        for button in self.point_buttons:
            button.setEnabled(False)
        
        # Store the active point index
        self.active_point_index = point_idx
        self.is_selection_mode = True
        
        # Update status
        self.status_label.setText(f"Click on the image to select {self.point_labels[point_idx]} point")
        
        # Disable the matplotlib toolbar actions temporarily
        self.toolbar.setEnabled(False)

    def deactivate_point_selection(self):
        """Deactivate point selection mode."""
        self.active_point_index = None
        self.is_selection_mode = False
        
        # Update status
        self.status_label.setText("")
        
        # Re-enable the matplotlib toolbar
        self.toolbar.setEnabled(True)
        
        # Update UI buttons state
        self.update_ui_state()

    def update_ui_state(self):
        """Update the UI state based on selected points."""
        # Enable/disable point buttons based on what's already selected
        for i, button in enumerate(self.point_buttons):
            if i < len(self.points):
                button.setText(f"{self.point_labels[i]} ✓")
                button.setStyleSheet("background-color: #8f8;")
            else:
                button.setText(self.point_labels[i])
                button.setStyleSheet("")
            button.setEnabled(not self.is_selection_mode)
        
        # Enable accept only if we have 3 points
        has_three_points = len(self.points) >= 3
        self.accept_button.setEnabled(has_three_points and not self.is_selection_mode)
        
        # Update instruction text
        if has_three_points:
            self.instruction_label.setText("All points selected. Review the selection and click 'Accept Selection'.")
        elif self.is_selection_mode:
            point_name = self.point_labels[self.active_point_index].split('(')[0].strip()
            self.instruction_label.setText(f"Click on the image to place the {point_name} point.")
        else:
            remaining = self.point_labels[len(self.points):len(self.point_labels)]
            next_points = ", ".join([p.split('(')[0].strip() for p in remaining])
            self.instruction_label.setText(
                f"Click the button below to select the {next_points} point{'s' if len(remaining) > 1 else ''}. "
                "Use the navigation toolbar to zoom and pan as needed before selecting."
            )

    def on_click(self, event):
        """Handle mouse clicks for point selection."""
        # Only process left clicks in selection mode with valid coordinates
        if (self.is_selection_mode and event.button == 1 and 
            event.xdata is not None and event.ydata is not None):
            
            # Convert coordinates to original image space
            orig_x, orig_y = self.display_to_original(event.xdata, event.ydata)
            
            # Create confirmation dialog
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Confirm Point")
            point_name = self.point_labels[self.active_point_index].split('(')[0].strip()
            msg_box.setText(f"Confirm {point_name} point at coordinates:\nX: {orig_x}\nY: {orig_y}")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            
            if msg_box.exec() == QMessageBox.Yes:
                # If this point was already set, remove the old one
                if self.active_point_index < len(self.points):
                    self.points[self.active_point_index] = (orig_x, orig_y)
                    # We need to redraw everything
                    self.update_display()
                else:
                    # Add new point
                    self.points.append((orig_x, orig_y))
                    
                    # Draw the point with scaled marker size
                    self.ax.plot(event.xdata, event.ydata, 'ro', markersize=self.marker_size)
                    
                    # Draw number next to point with appropriate offset
                    point_num = self.active_point_index + 1
                    self.ax.annotate(str(point_num), 
                            (event.xdata, event.ydata),
                            xytext=(self.annotation_offset, self.annotation_offset),
                            textcoords='offset points')
                
                # Exit selection mode
                self.deactivate_point_selection()
                
                # If we have all three points, calculate and draw the fourth point
                if len(self.points) == 3:
                    self.calculate_and_draw_fourth_point()
                
                self.canvas.draw()

    def calculate_and_draw_fourth_point(self):
        """Calculate and draw the fourth point of the quadrilateral."""
        if len(self.points) == 3:
            # Calculate fourth point in original coordinates
            p1, p2, p3 = self.points
            p4 = (p2[0] + (p3[0] - p1[0]), p3[1] + (p2[1] - p1[1]))
            self.points.append(p4)
            
            # Convert fourth point to display coordinates for visualization
            display_p4x, display_p4y = self.original_to_display(p4[0], p4[1])
            
            # Draw fourth point with scaled marker size
            self.ax.plot(display_p4x, display_p4y, 'ro', markersize=self.marker_size)
            self.ax.annotate('4', (display_p4x, display_p4y), 
               xytext=(self.annotation_offset, self.annotation_offset),
               textcoords='offset points')
            
            # Draw lines connecting points to form quadrilateral
            # Convert all points to display coordinates for visualization
            display_points = [self.original_to_display(p[0], p[1]) for p in self.points]
            dp1, dp2, dp3, dp4 = display_points
            
            # Draw lines with scaled width
            self.ax.plot([dp1[0], dp2[0]], [dp1[1], dp2[1]], 'b-', linewidth=self.line_width)  # Line 1-2
            self.ax.plot([dp1[0], dp3[0]], [dp1[1], dp3[1]], 'b-', linewidth=self.line_width)  # Line 1-3
            self.ax.plot([dp2[0], dp4[0]], [dp2[1], dp4[1]], 'b-', linewidth=self.line_width)  # Line 2-4
            self.ax.plot([dp3[0], dp4[0]], [dp3[1], dp4[1]], 'b-', linewidth=self.line_width)  # Line 3-4
            
            self.canvas.draw()

    def update_display(self):
        """Redraw the display with current points."""
        self.ax.clear()
        self.ax.imshow(self.initial_display_image, cmap='gray')
        
        # Draw all existing points
        for i, point in enumerate(self.points):
            display_x, display_y = self.original_to_display(point[0], point[1])
            self.ax.plot(display_x, display_y, 'ro', markersize=self.marker_size)
            self.ax.annotate(str(i+1), (display_x, display_y),
                      xytext=(self.annotation_offset, self.annotation_offset),
                      textcoords='offset points')
        
        # If we have all four points, draw the connecting lines
        if len(self.points) == 4:
            display_points = [self.original_to_display(p[0], p[1]) for p in self.points]
            dp1, dp2, dp3, dp4 = display_points
            
            self.ax.plot([dp1[0], dp2[0]], [dp1[1], dp2[1]], 'b-', linewidth=self.line_width)  # Line 1-2
            self.ax.plot([dp1[0], dp3[0]], [dp1[1], dp3[1]], 'b-', linewidth=self.line_width)  # Line 1-3
            self.ax.plot([dp2[0], dp4[0]], [dp2[1], dp4[1]], 'b-', linewidth=self.line_width)  # Line 2-4
            self.ax.plot([dp3[0], dp4[0]], [dp3[1], dp4[1]], 'b-', linewidth=self.line_width)  # Line 3-4
        
        self.canvas.draw()

    def retry(self):
        """Clear all points and restart selection."""
        self.points = []
        self.active_point_index = None
        self.is_selection_mode = False
        
        # Reset the display
        self.update_display()
        
        # Update UI state
        self.update_ui_state()

    def get_points(self):
        """Return the selected points in original image coordinates."""
        return self.points


def create_sample_seismic_image(width=1500, height=1000):
    """Create a sample seismic image with some line patterns for testing."""
    # Create a base image with some noise
    image = np.random.rand(height, width) * 0.2
    
    # Add horizontal timeline patterns
    for i in range(50, height, 50):
        image[i:i+2, :] = 1.0
    
    # Add vertical trace line patterns
    for i in range(30, width, 30):
        image[:, i:i+1] = 0.9
    
    # Add some diagonal features
    for i in range(height):
        pos = int(width * 0.2 + i * 0.5) % width
        if 0 <= pos < width:
            image[i, pos:pos+5] = 0.8
    
    # Add a brighter area to simulate a seismic event
    center_y, center_x = height // 2, width // 2
    for i in range(height):
        for j in range(width):
            dist = np.sqrt((i - center_y)**2 + (j - center_x)**2)
            if 200 < dist < 400:
                image[i, j] += 0.5 * np.exp(-(dist - 300)**2 / 10000)
    
    # Clip values to 0-1 range
    image = np.clip(image, 0, 1)
    
    # Convert to binary image (0s and 1s only)
    binary_image = (image > 0.5).astype(np.float32)
    
    return binary_image


def load_and_test_roi_dialog():
    """Load a sample image and test the ROISelectionDialog."""
    # Check if we already have a sample image or need to create one
    sample_image_path = os.path.join(os.path.dirname(__file__), "sample_seismic_image.png")
    
    if os.path.exists(sample_image_path):
        # Load existing image
        print(f"Loading existing sample image from {sample_image_path}")
        image = np.array(Image.open(sample_image_path).convert('L')) / 255.0
    else:
        # Create and save a new sample image
        print("Creating new sample seismic image...")
        image = create_sample_seismic_image()
        plt.imsave(sample_image_path, image, cmap='gray')
        print(f"Sample image saved to {sample_image_path}")
    
    # Initialize QApplication (required for Qt widgets)
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    # Create and show the ROISelectionDialog
    print("Opening ROISelectionDialog...")
    dialog = ROISelectionDialog(image)
    
    # Execute the dialog
    if dialog.exec():
        # If accepted, get the points
        points = dialog.get_points()
        print("\nSelected ROI Points:")
        for i, point in enumerate(points):
            print(f"Point {i+1}: ({point[0]:.1f}, {point[1]:.1f})")
    else:
        print("\nDialog was canceled or closed.")


if __name__ == "__main__":
    # Initialize QApplication
    app = QApplication.instance() or QApplication([])
    
    # Load and set stylesheet
    stylesheet_path = os.path.join("src", "segyrecover", "ui", "theme.qss")
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, 'r') as file:
            app.setStyleSheet(file.read())
    
    load_and_test_roi_dialog()
