"""
Test script for the Coordinate Assignment Dialog.
This script allows you to test the dialog without running the full application.
"""

import sys
import os
import numpy as np

from PySide6.QtWidgets import QApplication

import os
import math
from PySide6.QtGui import QFont, QPixmap, QPen, QPainter, QColor, QPolygonF, QIntValidator
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QMessageBox, QDialog
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy.ndimage import zoom



class CoordinateAssignmentDialog(QDialog):
    """Dialog for assigning coordinates to traces."""
    
    def __init__(self, cdp_range, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign coordinates to traces")
        self.cdp_range = cdp_range
        self.min_cdp = min(cdp_range)
        self.max_cdp = max(cdp_range)
        
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
        
        # Create visual representation
        visual_group = QGroupBox("CDP Direction")
        visual_layout = QVBoxLayout()
        visual_layout.setSpacing(10)
        
        # Direction 1: Low to High
        self.direction1_radio = self._create_direction_option(
            "First trace → CDP {} // Last trace → CDP {}".format(self.min_cdp, self.max_cdp),
            "CDPs increase from left to right",
            True  # Default selected
        )
        
        # Direction 2: High to Low
        self.direction2_radio = self._create_direction_option(
            "First trace → CDP {} // Last trace → CDP {}".format(self.max_cdp, self.min_cdp),
            "CDPs decrease from left to right"
        )
        
        # Add visual representations
        visual_layout.addWidget(self.direction1_radio)
        visual_layout.addWidget(self._create_direction_diagram(True))
        visual_layout.addWidget(self.direction2_radio)
        visual_layout.addWidget(self._create_direction_diagram(False))
        
        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)
        
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

    def _create_direction_option(self, text, tooltip, selected=False):
        """Create a radio button option with proper styling"""
        radio = QPushButton(text)
        radio.setCheckable(True)
        radio.setChecked(selected)
        radio.setToolTip(tooltip)
        radio.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #e7f5fd;
                border: 2px solid #0078d7;
            }
        """)
        # Make the buttons in a group mutually exclusive
        radio.clicked.connect(lambda: self._handle_radio_click(radio))
        return radio
    
    def _handle_radio_click(self, clicked_radio):
        """Ensure only one radio button is checked"""
        if clicked_radio == self.direction1_radio:
            self.direction2_radio.setChecked(False)
        else:
            self.direction1_radio.setChecked(False)
    
    def _create_direction_diagram(self, low_to_high):
        """Create a visual diagram showing direction of coordinates"""
        # Make taller diagram to accommodate more labels
        diagram = QLabel()
        pixmap = QPixmap(400, 100)
        pixmap.fill(Qt.white)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw seismic section representation
        painter.setPen(Qt.black)
        painter.setBrush(Qt.lightGray)
        painter.drawRect(20, 20, 360, 40)
        
        # Draw direction arrow
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.setBrush(QColor(0, 120, 215))
        
        # Arrow line
        painter.drawLine(50, 40, 350, 40)
        
        # Arrow head
        arrow_head = QPolygonF()
        if low_to_high:
            arrow_head.append(QPointF(350, 40))
            arrow_head.append(QPointF(340, 35))
            arrow_head.append(QPointF(340, 45))
        else:
            arrow_head.append(QPointF(50, 40))
            arrow_head.append(QPointF(60, 35))
            arrow_head.append(QPointF(60, 45))
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
        painter.drawText(20, 15, "First Trace")
        painter.drawText(345, 15, "Last Trace")
        
        # Draw tick marks and CDP labels
        tick_positions = [20, 110, 200, 290, 380]
        
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
        if self.direction1_radio.isChecked():
            # Low to high CDP
            return (self.min_cdp, self.max_cdp)
        else:
            # High to low CDP
            return (self.max_cdp, self.min_cdp)


def test_dialog_with_geometry_file(app):
    """Test the coordinate assignment dialog with geometry from an actual file"""
    # Path to the geometry file
    geometry_file = os.path.join("src", "segyrecover", "examples", "GEOMETRY", "RIV6.geometry")
    
    try:
        # Read the geometry file to extract CDP values
        cdp_values = []
        with open(geometry_file, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) >= 3:  # Basic validation that the line has enough columns
                    try:
                        cdp = int(parts[0])  # Assuming CDP is in the third column
                        cdp_values.append(cdp)
                    except (ValueError, IndexError):
                        pass
        
        # Use the first 100 values (or all if less than 100)
        sample_cdps = cdp_values[:min(100, len(cdp_values))]
        
        if not sample_cdps:
            print("No valid CDP values found in the geometry file")
            return
            
        print(f"Testing with {len(sample_cdps)} CDP values from geometry file")
        print(f"CDP range: {min(sample_cdps)} to {max(sample_cdps)}")
        
        # Create and show the dialog with the real geometry data
        dialog = CoordinateAssignmentDialog(sample_cdps)
        
        if dialog.exec():
            cdp_i, cdp_f = dialog.get_coordinates()
            print(f"Selected coordinates from geometry file: {cdp_i} to {cdp_f}")
    
    except Exception as e:
        print(f"Error reading geometry file: {e}")


if __name__ == "__main__":
    # Create application first
    app = QApplication(sys.argv)
    
    # Load and apply stylesheet
    stylesheet_path = os.path.join("src", "segyrecover", "ui", "theme.qss")
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, 'r') as f:
            app_stylesheet = f.read()
            app.setStyleSheet(app_stylesheet)
    else:
        print(f"Warning: Could not find stylesheet at {stylesheet_path}")

    test_dialog_with_geometry_file(app)
    
    # Start the event loop if needed
    sys.exit(app.exec())
