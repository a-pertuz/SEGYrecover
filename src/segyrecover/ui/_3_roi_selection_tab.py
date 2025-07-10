"""ROI Selection tab for SEGYRecover application."""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QMessageBox, QDialog, QTabWidget
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
        
        # Set toolbar to show text labels next to icons
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)


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
        
        # Create visualization tabs container - similar to digitization tab
        visualization_container = QGroupBox("Image Processing")
        visualization_container.setObjectName("visualization_container")
        visualization_layout = QVBoxLayout(visualization_container)
        visualization_layout.setContentsMargins(10,10,10,10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("roi_visualization_tabs")
        
        # Tab 1: Original image with point selection
        original_tab = QWidget()
        # Change to horizontal layout to place buttons to the right of the canvas
        original_layout = QHBoxLayout(original_tab)
        original_layout.setContentsMargins(10, 10, 10, 10)
        original_layout.setSpacing(10)
        
        # Left side - Canvas and toolbar in a vertical layout
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(5)
        
        # Canvas and toolbar for original image
        canvas_layout.addWidget(self.canvas, 1)  # Add stretch factor to expand canvas
        self.toolbar = SimpleNavigationToolbar(self.canvas, self)
        self.toolbar.setObjectName("roi_original_toolbar")
        canvas_layout.addWidget(self.toolbar)
        
        # Add canvas container to main layout with stretch factor
        original_layout.addWidget(canvas_container, 3)  # Canvas gets 3/4 of space
        
        # Right side - Point selection buttons in a vertical layout
        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)
        
        # Create point selection buttons directly in the controls layout
        self.point_buttons = []
        self.point_labels = ["Top-Left (1)", "Top-Right (2)", "Bottom-Left (3)"]
        
        for i, label in enumerate(self.point_labels):
            button = QPushButton(label)
            button.setObjectName(f"point_button_{i+1}")
            button.setToolTip(f"Click to select the {label.split('(')[0].strip()} corner of the region")
            button.setFixedHeight(36)
            button.clicked.connect(lambda checked, idx=i: self.activate_point_selection(idx))
            controls_layout.addWidget(button)
            self.point_buttons.append(button)
        
        # Cancel selection button (always visible but initially disabled)
        self.cancel_selection_button = QPushButton("Cancel Selection")
        self.cancel_selection_button.setObjectName("cancel_selection_button")
        self.cancel_selection_button.setToolTip("Cancel the current point selection")
        self.cancel_selection_button.setFixedHeight(36)
        self.cancel_selection_button.clicked.connect(self.cancel_point_selection)
        self.cancel_selection_button.setStyleSheet("background-color: #f0f0f0; color: #666666; border: 1px solid #999999;")
        self.cancel_selection_button.setEnabled(False)  # Initially disabled
        controls_layout.addWidget(self.cancel_selection_button)
        
        # Reduce spacing between buttons and the retry button
        controls_layout.setSpacing(3)
        
        # Retry button with red styling
        self.retry_selection_button = QPushButton("Retry Selection")
        self.retry_selection_button.setIcon(QIcon.fromTheme("edit-undo"))
        self.retry_selection_button.setObjectName("retry_selection_button")
        self.retry_selection_button.clicked.connect(self.retry_selection)
        self.retry_selection_button.setEnabled(False)
        self.retry_selection_button.setFixedHeight(36)
        self.retry_selection_button.setToolTip("Reset all corner points and start selection again")
        self.retry_selection_button.setStyleSheet("background-color: #ffcccc; color: #cc0000; border: 1px solid #cc0000;")
        
        controls_layout.addWidget(self.retry_selection_button)
        controls_layout.addStretch(1)  # Add stretch at bottom to push buttons up
        
        # Add controls container to main layout with reduced spacing
        original_layout.setSpacing(5) 
        original_layout.addWidget(controls_container, 1)  
        
        # Tab 2: Rectified image
        rectified_tab = QWidget()
        rectified_layout = QVBoxLayout(rectified_tab)
        
        # Canvas and toolbar for rectified image
        rectified_layout.addWidget(self.rectified_canvas)
        rectified_toolbar = SimpleNavigationToolbar(self.rectified_canvas, self)
        rectified_toolbar.setObjectName("roi_rectified_toolbar")
        rectified_layout.addWidget(rectified_toolbar)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(original_tab, "Original Image & Point Selection")
        self.tab_widget.addTab(rectified_tab, "Rectified Result")
        
        # Add tab widget to container
        visualization_layout.addWidget(self.tab_widget)
        
        # Add container to main layout (stretch factor 1)
        layout.addWidget(visualization_container, 1)
        
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

        section_header(self.console, "ROI SELECTION")
        info_message(self.console, "Ready to select region of interest.")

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
                success_message(self.console, "Loaded existing ROI from file.")
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
        self.ax.imshow(self.roi_processor.display_image, cmap='gray', aspect='equal')
        self.ax.set_title("Original Image - Select Points")
        self.canvas.draw()
        
        # Clear rectified image canvas
        self.rectified_ax.clear()
        self.rectified_ax.set_title("Rectified Image (select ROI first)")
        self.rectified_canvas.draw()
        
            
    def activate_point_selection(self, point_idx):
        """Activate point selection mode for the specific point."""
        # Disable all point buttons during selection
        for button in self.point_buttons:
            button.setEnabled(False)
            button.setStyleSheet(self.BUTTON_STYLE_DISABLED)
        
        # Enable cancel button
        self.cancel_selection_button.setEnabled(True)
        self.cancel_selection_button.setStyleSheet("background-color: #ffcccc; color: #cc0000; border: 1px solid #cc0000;")
        
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

    def cancel_point_selection(self):
        """Cancel the current point selection process."""
        # Disable cancel button
        self.cancel_selection_button.setEnabled(False)
        self.cancel_selection_button.setStyleSheet("background-color: #f0f0f0; color: #666666; border: 1px solid #999999;")
        
        # Reset selection state
        self.is_selection_mode = False
        self.active_point_index = None
        
        # Update status
        self.status_label.setText("Selection canceled")
        
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

    def deactivate_point_selection(self):
        """Deactivate point selection mode."""
        self.active_point_index = None
        self.is_selection_mode = False
        
        # Disable cancel button
        self.cancel_selection_button.setEnabled(False)
        self.cancel_selection_button.setStyleSheet("background-color: #f0f0f0; color: #666666; border: 1px solid #999999;")
        
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
        self.ax.imshow(self.roi_processor.display_image, cmap='gray', aspect='equal')
        
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
            self.rectified_ax.imshow(self.roi_processor.binary_rectified_image, cmap='gray', aspect='equal')
            self.rectified_ax.set_title("Rectified Image")
            self.rectified_canvas.draw()
            
            # Update UI state
            self.update_ui_state()
            
            # Switch to the rectified image tab
            self.tab_widget.setCurrentIndex(1)
            
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
        self.rectified_canvas.draw()
        
        # Update UI state
        self.next_button.setEnabled(False)
        self.update_ui_state()
        
        # Reset button styles
        self._apply_button_styles()
        
        info_message(self.console, "ROI selection restarted")
        
        # Reset button styles
        self._apply_button_styles()
        
        info_message(self.console, "ROI selection restarted")
        self._apply_button_styles()
        
        info_message(self.console, "ROI selection restarted")


