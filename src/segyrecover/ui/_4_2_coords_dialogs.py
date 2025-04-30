"""Common dialog classes used across the application."""

import os
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPen, QPainter, QColor, QPolygonF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QMessageBox, QApplication
)

class CoordinateAssignmentDialog(QDialog):
    """Dialog for assigning coordinates to traces."""
    
    def __init__(self, cdp_range, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign coordinates to traces")
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)

        pos_x = (screen_width-200) // 2
        pos_y = (screen_height-200) // 2
        self.move(pos_x, pos_y)
        
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