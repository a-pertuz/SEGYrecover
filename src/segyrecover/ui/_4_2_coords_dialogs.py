"""Common dialog classes used across the application."""

import os
import math
import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPen, QPainter, QColor, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QMessageBox, QApplication, QSplitter, QRadioButton, QWidget
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
    # Define which tools to keep
    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        
        # Configure the toolbar to show text labels
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

class CoordinateAssignmentDialog(QDialog):
    """Dialog for assigning coordinates to traces with geographic direction detection."""
    
    def __init__(self, cdp_range, x_coords=None, y_coords=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign coordinates to traces")
        self.resize(900, 600)  # Larger size to accommodate the location plot
        
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)

        pos_x = (screen_width - 900) // 2
        pos_y = (screen_height - 600) // 2
        self.move(pos_x, pos_y)
        
        self.cdp_range = cdp_range
        self.min_cdp = min(cdp_range)
        self.max_cdp = max(cdp_range)
        self.x_coords = x_coords
        self.y_coords = y_coords
        
        
        # Create location plot figure
        self.location_figure = plt.figure(constrained_layout=True)
        self.location_canvas = FigureCanvas(self.location_figure)
        self.location_canvas.setMinimumHeight(250)
        self.location_ax = self.location_figure.add_subplot(111)
        
        # Setup main layout
        self._setup_ui()
        
        # Display location plot if coordinates are available
        if x_coords and y_coords:
            self._display_location_plot()
            
   
    def _setup_ui(self):
        """Set up the dialog's user interface."""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Add info label
        info_label = QLabel(
            "Select the direction to assign coordinates to traces.\n"
            "This defines how CDP points from the geometry file are mapped to the digitized traces."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Location plot
        if self.x_coords and self.y_coords:
            location_container = QGroupBox("Location Map")
            location_layout = QVBoxLayout(location_container)
            location_layout.setContentsMargins(10, 10, 10, 10)
            location_layout.setSpacing(5)
            
            location_layout.addWidget(self.location_canvas)
            location_toolbar = SimpleNavigationToolbar(self.location_canvas, self)
            location_layout.addWidget(location_toolbar)
            
            splitter.addWidget(location_container)
        
        # Right panel - CDP direction options
        visual_group = QGroupBox("CDP Direction")
        visual_layout = QVBoxLayout(visual_group)
        visual_layout.setSpacing(10)

        # Direction 1: Maps to the geographic direction indicated by CDP increase
        direction1_text = "<b>First trace</b> → CDP {}<br><b>Last trace</b> → CDP {}".format(self.min_cdp, self.max_cdp)
        direction1_tooltip = "CDPs increase from left to right"
        
        self.direction1_radio = self._create_direction_option(
            direction1_text,
            direction1_tooltip,
            True  
        )
        
        # Direction 2: Maps to the geographic direction indicated by CDP decrease
        direction2_text = "<b>First trace</b> → CDP {}<br><b>Last trace</b> → CDP {}".format(self.max_cdp, self.min_cdp)        
        direction2_tooltip = "CDPs decrease from left to right"
        
        self.direction2_radio = self._create_direction_option(
            direction2_text,
            direction2_tooltip
        )
        
        

        # Add visual representations
        visual_layout.addWidget(self.direction1_radio)
        visual_layout.addSpacing(10)
        visual_layout.addWidget(self._create_direction_diagram(True))
        
        visual_layout.addWidget(self.direction2_radio)
        visual_layout.addSpacing(10)
        visual_layout.addWidget(self._create_direction_diagram(False))
        
        visual_group.setLayout(visual_layout)
        splitter.addWidget(visual_group)
        
        # Add splitter to layout
        layout.addWidget(splitter, 1)  

        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(accept_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)  
        
    def _display_location_plot(self):
        """Display the location plot with CDP points and directions."""

        self.location_ax.clear()
        self.location_ax.set_xlabel('UTM X')
        self.location_ax.set_ylabel('UTM Y')
        self.location_ax.grid(True)
        self.location_ax.set_title("CDP Coordinates Map")
        
        try:
            # Convert CDP range to strings for annotation
            cdp_str = [str(cdp) for cdp in self.cdp_range]
            
            # Plot coordinates
            self.location_ax.plot(self.x_coords, self.y_coords, marker='o', markersize=2, 
                                 color='red', linestyle='-')
            
            # Highlight the start and end points with larger markers
            self.location_ax.plot([self.x_coords[0]], [self.y_coords[0]], marker='o', 
                                 markersize=6, color='green')
            self.location_ax.plot([self.x_coords[-1]], [self.y_coords[-1]], marker='o', 
                                 markersize=6, color='blue')
            


            
            # Add labels with threshold to avoid overcrowding
            threshold = 1000
            annotated_positions = []
            
            # Always annotate first and last points
            self.location_ax.annotate(cdp_str[0], 
                                     (self.x_coords[0], self.y_coords[0]),
                                     xytext=(5, 5), textcoords='offset points',
                                     fontweight='bold')
            self.location_ax.annotate(cdp_str[-1], 
                                     (self.x_coords[-1], self.y_coords[-1]),
                                     xytext=(5, 5), textcoords='offset points',
                                     fontweight='bold')
            annotated_positions.append((self.x_coords[0], self.y_coords[0]))
            annotated_positions.append((self.x_coords[-1], self.y_coords[-1]))
            
            # Add a few intermediate labels
            for i in range(1, len(cdp_str)-1):
                position = (self.x_coords[i], self.y_coords[i])
                if all(np.linalg.norm(np.array(position) - np.array(p)) > threshold 
                      for p in annotated_positions):
                    self.location_ax.annotate(cdp_str[i], position)
                    annotated_positions.append(position)
            
            # Adjust plot appearance
            self.location_ax.set_aspect('equal', adjustable='datalim')
            plt.setp(self.location_ax.get_xticklabels(), rotation=45, ha='right')
            self.location_canvas.draw()
            return True

        except Exception as e:
            print(f"Error displaying location plot: {str(e)}")
            return False
            

    def _create_direction_option(self, text, tooltip, selected=False):
        """Create a radio button option with proper styling"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)
        
        radio = QRadioButton()
        radio.setChecked(selected)

        font = radio.font()
        font.setPointSize(10)
        radio.setFont(font)
        size = 15  # Increase size of the radio button
        radio.setStyleSheet(f"QRadioButton::indicator {{ width: {size}px; height: {size}px; }}")
        
        label = QLabel(text)
        label.setTextFormat(Qt.RichText)  # Enable rich text interpretation
        label.setToolTip(tooltip)
        
        layout.addWidget(radio)
        layout.addWidget(label)
        layout.addStretch()
        
        # Make the buttons in a group mutually exclusive
        radio.clicked.connect(lambda: self._handle_radio_click(container))
        
        # Store the radio button as an attribute of the container for access
        container.radio = radio
        return container
    
    def _handle_radio_click(self, clicked_container):
        """Ensure only one radio button is checked"""
        if clicked_container == self.direction1_radio:
            self.direction2_radio.radio.setChecked(False)
        else:
            self.direction1_radio.radio.setChecked(False)
    
    def _create_direction_diagram(self, low_to_high):
        """Create a visual diagram showing direction of coordinates"""
        # Make taller diagram to accommodate more labels
        diagram = QLabel()
        pixmap = QPixmap(400, 120)  # Made taller to accommodate direction info
        pixmap.fill(Qt.white)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw seismic section representation
        painter.setPen(Qt.black)
        painter.setBrush(Qt.lightGray)
        # Reduced rectangle width from 360 to 250
        rect_width = 250
        rect_start = 75  # Adjusted start position to center the rectangle
        painter.drawRect(rect_start, 20, rect_width, 40)
        
        # Draw direction arrow
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.setBrush(QColor(0, 120, 215))
        
        # Arrow line - adjusted for new rectangle dimensions
        arrow_start = rect_start + 30
        arrow_end = rect_start + rect_width - 30
        painter.drawLine(arrow_start, 40, arrow_end, 40)
        
        # Arrow head
        arrow_head = QPolygonF()
        if low_to_high:
            arrow_head.append(QPointF(arrow_end, 40))
            arrow_head.append(QPointF(arrow_end - 10, 35))
            arrow_head.append(QPointF(arrow_end - 10, 45))
        else:
            arrow_head.append(QPointF(arrow_start, 40))
            arrow_head.append(QPointF(arrow_start + 10, 35))
            arrow_head.append(QPointF(arrow_start + 10, 45))
        painter.drawPolygon(arrow_head)
        
        # Calculate intermediate CDP points
        if len(self.cdp_range) >= 5:
            # Use actual CDP values from the range if available
            step = len(self.cdp_range) // 4
            sample_points = [self.cdp_range[0], 
                            self.cdp_range[step], 
                            self.cdp_range[2*step],
                            self.cdp_range[3*step],
                            self.cdp_range[-1]]
        else:
            # Generate evenly spaced points
            step = (self.max_cdp - self.min_cdp) / 4
            sample_points = [
                int(self.min_cdp + i * step) for i in range(5)
            ]
        
        # Add Trace labels at top
        painter.setPen(Qt.black)
        painter.drawText(rect_start, 15, "First Trace")
        painter.drawText(rect_start + rect_width - 55, 15, "Last Trace")
        
        # Draw tick marks and CDP labels - adjusted for new rectangle dimensions
        tick_positions = [
            rect_start, 
            rect_start + rect_width/4, 
            rect_start + rect_width/2, 
            rect_start + 3*rect_width/4, 
            rect_start + rect_width
        ]
        
        # Add CDP labels at bottom
        painter.setPen(Qt.black)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        
        # Draw ticks and CDP values
        for i, (pos, cdp) in enumerate(zip(tick_positions, sample_points if low_to_high else reversed(sample_points))):
            # Draw tick
            painter.drawLine(pos, 60, pos, 65)
            
            # Draw CDP value
            cdp_text = str(cdp)
            text_width = painter.fontMetrics().horizontalAdvance(cdp_text)
            painter.drawText(pos - text_width//2, 80, cdp_text)
        
        # Add CDP direction label
        direction_text = "CDP values increase →" if low_to_high else "← CDP values decrease"
        painter.drawText(150, 95, direction_text)
        
        painter.end()
        diagram.setPixmap(pixmap)
        return diagram
    
    def get_coordinates(self):
        """Return the selected coordinates based on direction choice"""
        if self.direction1_radio.radio.isChecked():
            # Natural direction (Low to high CDP)
            return (self.min_cdp, self.max_cdp)
        else:
            # Reverse direction (High to low CDP)
            return (self.max_cdp, self.min_cdp)