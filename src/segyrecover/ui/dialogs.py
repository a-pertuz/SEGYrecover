"""Dialog windows for SEGYRecover."""
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


class ParameterDialog(QDialog):
    """Dialog for inputting SEGY processing parameters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Parameters")
        self.setGeometry(150, 120, 400, 600)
        self.layout = QVBoxLayout(self)

        # Define constants 
        self.POINT_CONFIGS = [
            ("P1", "Top Left", (7.5, 7.5), "Top left corner coordinates"),
            ("P2", "Top Right", (57.5, 7.5), "Top right corner coordinates"), 
            ("P3", "Bottom Left", (7.5, 37.5), "Bottom left corner coordinates")
        ]
        
        self.FREQUENCY_PARAMS = [
            ("F1", "Low cut-off"), ("F2", "Low pass"),
            ("F3", "High pass"), ("F4", "High cut-off")
        ]

        self.DETECTION_PARAMS = [
            ("TLT", "Traceline Thickness", "Thickness of vertical trace lines"),
            ("HLT", "Timeline Thickness", "Thickness of horizontal time lines"),
            ("HE", "Horizontal Erode", "Erosion size for horizontal features"),
            ("BDB", "Baseline Detection Begining", "Baseline Detection Begining"),
            ("BDE", "Baseline Detection End", "Baseline Detection End"),
            ("BFT", "Baseline Filter Threshold", "Baseline Filter Threshold")
        ]

        # Create and populate the dialog sections
        self._create_point_inputs()
        self._create_acquisition_params()
        self._create_detection_params()
        
        # Add accept button
        self.accept_button = QPushButton("Accept", self)
        self.accept_button.clicked.connect(self.accept)
        self.layout.addWidget(self.accept_button)

    def _create_point_inputs(self):
        """Create input fields for ROI point coordinates."""
        for point_id, label, dot_pos, tooltip in self.POINT_CONFIGS:
            # Create group box with tooltips
            group = QGroupBox(f"{point_id} - {label}", self)
            group.setFont(QFont("", -1, QFont.Bold))
            group.setToolTip(tooltip)
            layout = QFormLayout()
            
            # Create Trace and TWT inputs
            for param in ["Trace", "TWT"]:
                input_field = QLineEdit(self)
                input_field.setFixedWidth(50)
                input_field.setValidator(QIntValidator())
                layout.addRow(f"{param}_{point_id}:", input_field)
                setattr(self, f"{param}_{point_id}", input_field)
            
            group.setLayout(layout)
            
            # Create horizontal layout with icon
            h_layout = QHBoxLayout()
            h_layout.addWidget(group)
            
            # Create and add icon
            icon = QLabel(self)
            pixmap = QPixmap(70, 50)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.red)
            painter.drawRect(10, 10, 50, 30)
            painter.drawEllipse(dot_pos[0], dot_pos[1], 5, 5)
            painter.end()
            icon.setPixmap(pixmap)
            h_layout.addWidget(icon)
            
            self.layout.addLayout(h_layout)

    def _create_acquisition_params(self):
        """Create acquisition parameter inputs."""
        group = QGroupBox("Acquisition Parameters", self)
        group.setFont(QFont("", -1, QFont.Bold))
        layout = QFormLayout()
        
        # Sample rate input
        self.DT = QLineEdit(self)
        self.DT.setFixedWidth(50)
        self.DT.setValidator(QIntValidator())
        self.DT.setToolTip("Sample rate in milliseconds")
        layout.addRow("Sample Rate (ms):", self.DT)
        
        # Frequency band inputs
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency band (Hz):"))
        
        for param_id, tooltip in self.FREQUENCY_PARAMS:
            input_field = QLineEdit(self)
            input_field.setFixedWidth(30)
            input_field.setValidator(QIntValidator())
            input_field.setToolTip(tooltip)
            freq_layout.addWidget(input_field)
            setattr(self, param_id, input_field)
        
        # Add frequency band diagram
        icon = self._create_freq_band_icon()
        freq_layout.addWidget(icon)
        layout.addRow(freq_layout)
        
        group.setLayout(layout)
        self.layout.addWidget(group)
    
    def _create_detection_params(self):
        """Create timeline/baseline detection parameter inputs."""
        group = QGroupBox("Timeline and Baseline Detection Parameters", self)
        group.setFont(QFont("", -1, QFont.Bold))
        layout = QFormLayout()
        
        # Basic parameters - first two parameters (TLT, HLT)
        basic_params = self.DETECTION_PARAMS[:2]
        for param_id, label, tooltip in basic_params:
            input_field = QLineEdit(self)
            input_field.setFixedWidth(50)
            input_field.setValidator(QIntValidator())
            input_field.setToolTip(tooltip)
            layout.addRow(f"{label}:", input_field)
            setattr(self, param_id, input_field)
        
        # Add Advanced Parameters label
        advanced_label = QLabel("Advanced Parameters")
        advanced_label.setFont(QFont("", -1, QFont.Bold))
        advanced_label.setStyleSheet("color: #444; margin-top: 10px;")
        layout.addRow(advanced_label, QLabel(""))
        
        # Advanced parameters - remaining parameters (HE, BDB, BDE, BFT)
        advanced_params = self.DETECTION_PARAMS[2:]
        for param_id, label, tooltip in advanced_params:
            input_field = QLineEdit(self)
            input_field.setFixedWidth(50)
            input_field.setValidator(QIntValidator())
            input_field.setToolTip(tooltip)
            layout.addRow(f"{label}:", input_field)
            setattr(self, param_id, input_field)
        
        group.setLayout(layout)
        self.layout.addWidget(group)

    def _create_freq_band_icon(self):
        """Create frequency band diagram icon."""
        icon = QLabel(self)
        pixmap = QPixmap(70, 50)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setPen(Qt.red)
        
        # Draw trapezoid
        points = [
            QPointF(20, 10), QPointF(10, 40),
            QPointF(60, 40), QPointF(50, 10)
        ]
        painter.drawPolygon(QPolygonF(points))
        
        # Add frequency labels
        painter.setPen(QColor(0, 0, 0))
        labels = [("F2", 10, 10), ("F1", 5, 40),
                 ("F4", 55, 40), ("F3", 50, 10)]
        for text, x, y in labels:
            painter.drawText(x, y, text)
        
        painter.end()
        icon.setPixmap(pixmap)
        return icon

    def get_parameters(self):
        """Return all parameters as a dictionary."""
        params = {}
        
        # Get point parameters
        for point in ["P1", "P2", "P3"]:
            for param in ["Trace", "TWT"]:
                key = f"{param}_{point}"
                params[key] = int(getattr(self, key).text())
        
        # Get acquisition parameters
        params["DT"] = int(self.DT.text())
        for param_id, _ in self.FREQUENCY_PARAMS:
            params[param_id] = int(getattr(self, param_id).text())
            
        # Get detection parameters
        for param_id, _, _ in self.DETECTION_PARAMS:
            params[param_id] = int(getattr(self, param_id).text())
            
        return params


class TimelineBaselineWindow(QDialog):
    """Dialog for displaying and verifying timeline/baseline detection results."""
    
    def __init__(self, image_a, image_f, image_g, image_m, 
                 raw_baselines, clean_baselines, final_baselines, BDB, BDE):
        super().__init__()  
        self.setWindowTitle("Timeline and Baseline Detection")
        self.setGeometry(200, 150, 1100, 800)

        layout = QVBoxLayout()
        self.setLayout(layout)

        fig, ((ax1, ax4), (ax2, ax3)) = plt.subplots(2, 2)
        self.canvas = FigureCanvas(fig)
        self.canvas.setFocusPolicy(Qt.StrongFocus) 
        
        layout.addWidget(self.canvas)
        
        toolbar_segyrec = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar_segyrec)

        # Plot the images and lines
        ax1.imshow(image_g, cmap='gray')        
        ax1.set_title('Image with Timelines Removed')

        ax2.imshow(image_a, cmap='gray')
        ax2.axhline(y=BDB, color='blue', linewidth=2, linestyle='--')
        ax2.axhline(y=BDE, color='blue', linewidth=2, linestyle='--')
        ax2.set_title('Image with Baselines')

        ax3.imshow(image_m, cmap='gray')
        ax3.set_title('Debug Baseline Detection')
        ax3.axhline(y=BDB, color='blue', linewidth=2, linestyle='--')
        ax3.axhline(y=BDE, color='blue', linewidth=2, linestyle='--')

        ax4.imshow(image_f, cmap='gray')
        ax4.set_title('Timelines')

        # Draw baselines
        for baseline in final_baselines:
            ax2.axvline(x=baseline, color='lime', linewidth=1)
        
        for baseline in raw_baselines:
            ax3.axvline(x=baseline, color='red', linewidth=1)

        for baseline in final_baselines:
            if baseline not in raw_baselines:
                ax3.axvline(x=baseline, color='cyan', linewidth=1, linestyle='--')

        self._apply_initial_zoom([ax1, ax2, ax3, ax4], image_a.shape)
        toolbar_segyrec.update()

        button_layout = QHBoxLayout()
        
        continue_button = QPushButton("Continue")
        continue_button.clicked.connect(self.accept)
        button_layout.addWidget(continue_button)
        
        restart_button = QPushButton("Restart")
        restart_button.clicked.connect(self.reject)
        button_layout.addWidget(restart_button)
        
        layout.addLayout(button_layout)

    def _apply_initial_zoom(self, axes, image_shape):
        """Apply initial zoom to focus on the center of the image."""
        height, width = image_shape
        
        # Center-focused zoom without considering BDB and BDE
        zoom_factor = 0.5  # Show 50% of the image in both dimensions
        
        # Calculate center point
        y_center = height // 2
        x_center = width // 2
        
        # Calculate range based on zoom factor
        y_half_range = int(height * zoom_factor / 2)
        x_half_range = int(width * zoom_factor / 2)
        
        # Set limits around the center
        y_min = max(0, y_center - y_half_range)
        y_max = min(height, y_center + y_half_range)
        x_min = max(0, x_center - x_half_range)
        x_max = min(width, x_center + x_half_range)
        
        # Set limits for all plots
        for ax in axes:
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_max, y_min) 


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

