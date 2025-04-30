"""ROI Selection tab for SEGYRecover application."""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QMessageBox, QDialog
)
from PySide6.QtGui import QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ..utils.console_utils import info_message, error_message, success_message, section_header
from ._3_1_roi_selection_logic import ROIProcessor

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
    # Define which tools to keep
    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)


class ROISelectionTab(QWidget):
    """Tab for selecting the region of interest on a seismic image."""
    
    # Signals
    roiSelected = Signal(list, object)  # points, binary_rectified_image
    proceedRequested = Signal()
    
    # Button style constants
    BUTTON_STYLE_SELECTED = "background-color: #4CAF50; color: white; font-weight: bold;"
    BUTTON_STYLE_NEXT = "background-color: #2196F3; color: white;"
    BUTTON_STYLE_DISABLED = "background-color: #f0f0f0; color: #a0a0a0;"
    
    def __init__(self, console, work_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("roi_selection_tab")
        self.console = console
        self.work_dir = work_dir
        
        # Create the ROI processor for handling the logic
        self.roi_processor = ROIProcessor(console, work_dir)
        
        # Selection state variables
        self.active_point_index = None
        self.is_selection_mode = False
        self.marker_size = 8
        self.line_width = 2
        self.annotation_offset = 10
        
        # Create image canvases
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setObjectName("roi_original_canvas")
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.ax = self.figure.add_subplot(111)
        
        self.rectified_figure = Figure(constrained_layout=True)
        self.rectified_canvas = FigureCanvas(self.rectified_figure)
        self.rectified_canvas.setObjectName("roi_rectified_canvas")
        self.rectified_ax = self.rectified_figure.add_subplot(111)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header = QLabel("Region of Interest Selection")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        self.instruction_label = QLabel(
            "Select the region of interest (ROI) by defining the corners of your seismic section. "
            "The section will be rectified based on these points."
        )
        self.instruction_label.setObjectName("description_label")
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        layout.addWidget(self.status_label)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("content_splitter")
        splitter.setHandleWidth(6)  
        
        # Left panel - Original image with point selection
        original_container = QGroupBox("Original Image")
        original_container.setObjectName("original_image_container")
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(15, 15, 15, 15)
        original_layout.setSpacing(10)
        
        # Canvas and toolbar for original image
        original_layout.addWidget(self.canvas)
        self.toolbar = SimpleNavigationToolbar(self.canvas, self)
        self.toolbar.setObjectName("roi_original_toolbar")
        original_layout.addWidget(self.toolbar)
        
        # Point selection buttons 
        points_group = QGroupBox("Select Corner Points")
        points_group.setObjectName("corner_points_group")
        points_layout = QHBoxLayout(points_group)
        points_layout.setContentsMargins(15, 15, 15, 15)
        points_layout.setSpacing(10)
        
        # Create point selection buttons
        self.point_buttons = []
        self.point_labels = ["Top-Left (1)", "Top-Right (2)", "Bottom-Left (3)"]
        
        for i, label in enumerate(self.point_labels):
            button = QPushButton(label)
            button.setObjectName(f"point_button_{i+1}")
            button.setToolTip(f"Click to select the {label.split('(')[0].strip()} corner of the region")
            button.setMinimumWidth(120)
            button.setFixedHeight(36)
            button.clicked.connect(lambda checked, idx=i: self.activate_point_selection(idx))
            points_layout.addWidget(button)
            self.point_buttons.append(button)
        
        original_layout.addWidget(points_group)
        
        # Retry button for point selection with icon
        retry_button_layout = QHBoxLayout()
        retry_button_layout.addStretch()
        
        self.retry_selection_button = QPushButton()
        self.retry_selection_button.setIcon(QIcon.fromTheme("edit-undo", QIcon.fromTheme("refresh")))
        self.retry_selection_button.setText("Retry")
        self.retry_selection_button.setObjectName("retry_selection_button")
        self.retry_selection_button.clicked.connect(self.retry_selection)
        self.retry_selection_button.setEnabled(False)
        self.retry_selection_button.setFixedWidth(80)
        self.retry_selection_button.setFixedHeight(36)
        self.retry_selection_button.setToolTip("Reset all corner points and start selection again")
        
        retry_button_layout.addWidget(self.retry_selection_button)
        retry_button_layout.addStretch()
        original_layout.addLayout(retry_button_layout)
        
        # Right panel - Rectified image
        rectified_container = QGroupBox("Rectified Image")
        rectified_container.setObjectName("rectified_image_container")
        rectified_layout = QVBoxLayout(rectified_container)
        rectified_layout.setContentsMargins(15, 15, 15, 15)
        rectified_layout.setSpacing(10)
        
        # Canvas and toolbar for rectified image
        rectified_layout.addWidget(self.rectified_canvas)
        rectified_toolbar = SimpleNavigationToolbar(self.rectified_canvas, self)
        rectified_toolbar.setObjectName("roi_rectified_toolbar")
        rectified_layout.addWidget(rectified_toolbar)
        
        # Add panels to splitter
        splitter.addWidget(original_container)
        splitter.addWidget(rectified_container)
        splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        
        layout.addWidget(splitter, 1)  # 1 = stretch factor
        
        # Bottom button section
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        
        # Add spacer to push button to the right
        button_layout.addStretch()
        
        # Main next button with fixed width
        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("next_button")
        self.next_button.setMinimumWidth(100)
        self.next_button.setFixedHeight(36)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.next_button)
        
        layout.addWidget(button_container)
        
        # Initialize button styles
        self._apply_button_styles()
    
    def _apply_button_styles(self):
        """Apply the appropriate styles to all buttons based on their state."""
        # Disable point buttons 2 and 3 initially and apply styles
        for i, button in enumerate(self.point_buttons):
            if i == 0:
                button.setStyleSheet(self.BUTTON_STYLE_NEXT)
            else:
                button.setEnabled(False)
                button.setStyleSheet(self.BUTTON_STYLE_DISABLED)
    
    def update_with_image(self, image_path, img_array):
        """Update the tab with the loaded image and prepare for ROI selection."""
        if img_array is None:
            return
            
        section_header(self.console, "ROI SELECTION")
        info_message(self.console, "Ready to select region of interest")
        
        # Set the image in the processor
        self.roi_processor.set_image(image_path, img_array)
        
        # Check if existing ROI file exists and offer to load it
        if self.roi_processor.check_existing_roi():
            reply = QMessageBox.question(
                self,
                "Existing ROI",
                "An existing ROI file was found. Do you want to use it?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.roi_processor.load_roi_points()
                success_message(self.console, "Loaded existing ROI")
                self.process_roi()
                return
        
        # Reset state
        self.next_button.setEnabled(False)
        self.retry_selection_button.setEnabled(False)
        
        # Reset and apply button styles
        self._apply_button_styles()
        
        # Update instruction
        self.instruction_label.setText(
            "Select the three corner points of your seismic section in this order:\n"
            "1. Top-Left, 2. Top-Right, 3. Bottom-Left. The fourth point will be calculated automatically."
        )
        
        # Clear and update image canvas
        self.ax.clear()
        self.ax.imshow(self.roi_processor.display_image, cmap='gray')
        self.ax.set_title("Original Image - Select Points")
        self.ax.axis('off')
        self.canvas.draw()
        
        # Clear rectified image canvas
        self.rectified_ax.clear()
        self.rectified_ax.set_title("Rectified Image (select ROI first)")
        self.rectified_ax.axis('off')
        self.rectified_canvas.draw()
        
        # Show resolution message if downsampled
        if self.roi_processor.downsample_factor > 1:
            info_message(self.console, 
                f"Image displayed at reduced resolution ({100/self.roi_processor.downsample_factor:.1f}%) for performance")
    
    def activate_point_selection(self, point_idx):
        """Activate point selection mode for the specific point."""
        # Disable all point buttons during selection
        for button in self.point_buttons:
            button.setEnabled(False)
            button.setStyleSheet(self.BUTTON_STYLE_DISABLED)
        
        # Store the active point index
        self.active_point_index = point_idx
        self.is_selection_mode = True
        
        # Update status and instructions
        point_name = self.point_labels[point_idx].split('(')[0].strip()
        self.status_label.setText(f"Click on the image to select {point_name} point")
        self.instruction_label.setText(f"Click on the image to place the {point_name} point.")
        
        # Temporarily disable navigation toolbar
        self.toolbar.setEnabled(False)
        
        # Store and disable the current toolbar mode
        self._prev_toolbar_mode = self.toolbar.mode
        if hasattr(self.toolbar, 'mode'):
            self.toolbar.mode = ''
        
        # Disconnect any existing pan/zoom callbacks
        if hasattr(self.toolbar, '_active'):
            if self.toolbar._active == 'PAN':
                self.toolbar.pan()
            elif self.toolbar._active == 'ZOOM':
                self.toolbar.zoom()
    
    def deactivate_point_selection(self):
        """Deactivate point selection mode."""
        self.active_point_index = None
        self.is_selection_mode = False
        
        # Update status
        self.status_label.setText("")
        
        # Re-enable toolbar
        self.toolbar.setEnabled(True)
        
        # Restore previous toolbar mode
        if hasattr(self, '_prev_toolbar_mode') and self._prev_toolbar_mode:
            if self._prev_toolbar_mode == 'pan':
                self.toolbar.pan()
            elif self._prev_toolbar_mode == 'zoom':
                self.toolbar.zoom()
        
        # Update UI buttons state
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI state based on selected points."""
        # Get points from processor
        points = self.roi_processor.points
        
        # Update point buttons
        for i, button in enumerate(self.point_buttons):
            button.setEnabled(False)
            
            if i < len(points):
                button.setText(f"{self.point_labels[i]} ✓")
                button.setEnabled(True)  # Allow re-selecting points
                button.setStyleSheet(self.BUTTON_STYLE_SELECTED)
            else:
                button.setText(self.point_labels[i])
                button.setStyleSheet(self.BUTTON_STYLE_DISABLED)
        
        # Enable the next point button if not in selection mode
        if not self.is_selection_mode and len(points) < len(self.point_buttons):
            next_point_button = self.point_buttons[len(points)]
            next_point_button.setEnabled(True)
            next_point_button.setStyleSheet(self.BUTTON_STYLE_NEXT)
        
        # Enable/disable retry button
        has_points = len(points) > 0
        self.retry_selection_button.setEnabled(has_points and not self.is_selection_mode)
        
        # Enable next button if we have all points and rectified image
        has_roi = len(points) >= 4 and self.roi_processor.binary_rectified_image is not None
        self.next_button.setEnabled(has_roi and not self.is_selection_mode)

        
        # Update instruction text
        if has_roi:
            self.instruction_label.setText("Region selected and image rectified. Click 'Next' to continue.")
        elif self.is_selection_mode:
            point_name = self.point_labels[self.active_point_index].split('(')[0].strip()
            self.instruction_label.setText(f"Click on the image to place the {point_name} point.")
        else:
            if len(points) < len(self.point_labels):
                next_point = self.point_labels[len(points)].split('(')[0].strip()
                self.instruction_label.setText(
                    f"Select the {next_point} point by clicking the button below."
                )
    
    def on_click(self, event):
        """Handle mouse clicks for point selection."""
        # Only process clicks in selection mode
        if not self.is_selection_mode or event.button != 1 or event.xdata is None or event.ydata is None:
            return
            
        # Convert coordinates to original image space
        orig_x, orig_y = self.roi_processor.display_to_original(event.xdata, event.ydata)
        
        # Create confirmation dialog
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirm Point")
        point_name = self.point_labels[self.active_point_index].split('(')[0].strip()
        msg_box.setText(f"Confirm {point_name} point at coordinates:\nX: {orig_x}\nY: {orig_y}")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        
        if msg_box.exec() == QMessageBox.Yes:
            # If this point was already set, replace it
            if self.active_point_index < len(self.roi_processor.points):
                self.roi_processor.points[self.active_point_index] = (orig_x, orig_y)
                # Redraw everything
                self.update_display()
            else:
                # Add new point
                self.roi_processor.points.append((orig_x, orig_y))
                
                # Draw the point
                self.ax.plot(event.xdata, event.ydata, 'ro', markersize=self.marker_size)
                
                # Draw number next to point
                point_num = self.active_point_index + 1
                self.ax.annotate(str(point_num), 
                        (event.xdata, event.ydata),
                        xytext=(self.annotation_offset, self.annotation_offset),
                        textcoords='offset points')
            
            # Exit selection mode
            self.deactivate_point_selection()
            
            # Log the selection
            info_message(self.console, f"Selected {point_name} point")
            
            # If we have all three points, calculate the fourth point
            if len(self.roi_processor.points) == 3:
                self.calculate_and_draw_fourth_point()
                self.process_roi()
            
            self.canvas.draw()
    
    def calculate_and_draw_fourth_point(self):
        """Calculate and draw the fourth point of the quadrilateral."""
        if len(self.roi_processor.points) == 3:
            # Calculate the fourth point using the processor
            p4 = self.roi_processor.calculate_fourth_point()
            
            # Convert to display coordinates
            display_p4x, display_p4y = self.roi_processor.original_to_display(p4[0], p4[1])
            
            # Draw fourth point
            self.ax.plot(display_p4x, display_p4y, 'ro', markersize=self.marker_size)
            self.ax.annotate('4', (display_p4x, display_p4y), 
               xytext=(self.annotation_offset, self.annotation_offset),
               textcoords='offset points')
            
            # Draw lines connecting all points
            display_points = [
                self.roi_processor.original_to_display(p[0], p[1]) 
                for p in self.roi_processor.points
            ]
            dp1, dp2, dp3, dp4 = display_points
            
            self.ax.plot([dp1[0], dp2[0]], [dp1[1], dp2[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp1[0], dp3[0]], [dp1[1], dp3[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp2[0], dp4[0]], [dp2[1], dp4[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp3[0], dp4[0]], [dp3[1], dp4[1]], 'b-', linewidth=self.line_width)
            
            self.canvas.draw()
            
            info_message(self.console, "Fourth point calculated automatically")
    
    def update_display(self):
        """Redraw the display with current points."""
        self.ax.clear()
        self.ax.imshow(self.roi_processor.display_image, cmap='gray')
        
        # Draw all existing points
        for i, point in enumerate(self.roi_processor.points):
            display_x, display_y = self.roi_processor.original_to_display(point[0], point[1])
            self.ax.plot(display_x, display_y, 'ro', markersize=self.marker_size)
            self.ax.annotate(str(i+1), (display_x, display_y),
                      xytext=(self.annotation_offset, self.annotation_offset),
                      textcoords='offset points')
        
        # If we have all four points, draw the connecting lines
        if len(self.roi_processor.points) == 4:
            display_points = [
                self.roi_processor.original_to_display(p[0], p[1]) 
                for p in self.roi_processor.points
            ]
            dp1, dp2, dp3, dp4 = display_points
            
            self.ax.plot([dp1[0], dp2[0]], [dp1[1], dp2[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp1[0], dp3[0]], [dp1[1], dp3[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp2[0], dp4[0]], [dp2[1], dp4[1]], 'b-', linewidth=self.line_width)
            self.ax.plot([dp3[0], dp4[0]], [dp3[1], dp4[1]], 'b-', linewidth=self.line_width)
        
        self.canvas.draw()
    
    def process_roi(self):
        """Process the selected ROI and generate rectified image."""
        if len(self.roi_processor.points) != 4:
            error_message(self.console, "Invalid ROI or missing image")
            return
        
        # Process the ROI using the processor
        if self.roi_processor.process_roi():
            # Display the rectified image
            self.rectified_ax.clear()
            self.rectified_ax.imshow(self.roi_processor.binary_rectified_image, cmap='gray')
            self.rectified_ax.set_title("Rectified Image")
            self.rectified_ax.axis('off')
            self.rectified_canvas.draw()
            
            # Update UI state
            self.update_ui_state()
            
            # Emit signal with points and binary image
            self.roiSelected.emit(
                self.roi_processor.points, 
                self.roi_processor.binary_rectified_image
            )
    
    def retry_selection(self):
        """Clear all points and restart selection."""
        # Clear points in the processor
        self.roi_processor.clear_points()
        
        # Reset the display
        self.update_display()
        
        # Clear rectified image
        self.rectified_ax.clear()
        self.rectified_ax.set_title("Rectified Image (select ROI first)")
        self.rectified_ax.axis('off')
        self.rectified_canvas.draw()
        
        # Update UI state
        self.next_button.setEnabled(False)
        self.update_ui_state()
        
        # Reset button styles
        self._apply_button_styles()
        
        info_message(self.console, "ROI selection restarted")


