"""Mute Topography Dialog for SEGYRecover application."""

import os
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPen, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSpinBox, QMessageBox, QApplication, QDialogButtonBox,
    QWidget
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import seisio
import seisplot

from ..utils.console_utils import info_message, success_message, error_message

from scipy.interpolate import CubicSpline


class MuteTopographyDialog(QDialog):
    """Dialog for muting topography in SEGY data."""
    
    def __init__(self, segy_path, console, work_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mute Topography")
        self.setModal(True)
        
        # Setup window size and positioning
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)   
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        self.setGeometry(100, 100, window_width, window_height)
        
        # Initialize data
        self.segy_path = segy_path
        self.console = console
        self.work_dir = work_dir
        self.picked_points = []  # List of (trace_idx, sample_idx) tuples
        self.taper_length = 5    # Default taper length in samples
        self.segy_data = None
        self.muted_data = None
        self.plot_type = "image"  # Default plot type (variable density)
        self.is_previewing = False  # Flag to track if we're showing the preview
        
        # Load SEGY data
        info_message(self.console, f"Loading SEGY data from {os.path.basename(self.segy_path)}")

        sio = seisio.input(self.segy_path)
        dataset = sio.read_all_traces()
        self.segy_data = dataset["data"]
        self.muted_data = self.segy_data.copy() 
        
        # Setup UI
        self.setup_ui()
        
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Mute Topography")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Click on the seismic section to define a surface for muting. All data above the surface "
            "will be muted (set to zero), with a taper applied below. \nClick 'Apply' to preview the changes, "
            "and 'Save' when you're satisfied with the result."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Main plot area
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Connect mouse click event
        self.canvas.mpl_connect('button_press_event', self.on_click)
        
        # Add canvas to layout
        layout.addWidget(self.canvas, 1)  # 1 = stretch factor
        
        # Controls panel
        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        
        # Taper length control
        taper_group = QGroupBox("Taper Settings")
        taper_group.setSizePolicy(taper_group.sizePolicy().horizontalPolicy(), taper_group.sizePolicy().verticalPolicy())
        taper_layout = QHBoxLayout(taper_group)
        taper_label = QLabel("Taper Length (samples):")
        self.taper_spin = QSpinBox()
        self.taper_spin.setRange(0, 100)
        self.taper_spin.setValue(self.taper_length)
        self.taper_spin.valueChanged.connect(self.on_taper_changed)
        taper_layout.addWidget(taper_label)
        taper_layout.addWidget(self.taper_spin)
        controls_layout.addWidget(taper_group)
        
        # Action buttons
        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout(button_group)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_muting)
        self.apply_button.setEnabled(False)  # Disabled until points are picked
        
        self.reset_button = QPushButton("Reset Points")
        self.reset_button.clicked.connect(self.reset_points)
        self.reset_button.setEnabled(False)  # Disabled until points are picked
        
        self.toggle_button = QPushButton("Show Original")
        self.toggle_button.clicked.connect(self.toggle_preview)
        self.toggle_button.setEnabled(False)  # Disabled until preview exists
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.toggle_button)
        controls_layout.addWidget(button_group)
        
        layout.addWidget(controls_panel)
        
        # Dialog buttons (Save/Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_changes)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Save).setEnabled(False)  # Disabled until changes are applied
        self.save_button = button_box.button(QDialogButtonBox.Save)
        layout.addWidget(button_box)
        
        # Display initial SEGY data
        self.display_segy_data()
        self.update_buttons()  # Ensure buttons are set correctly at start

    def update_buttons(self):
        """Enable or disable buttons based on picked points and preview state."""
        has_points = len(self.picked_points) >= 2
        self.apply_button.setEnabled(has_points)
        self.reset_button.setEnabled(len(self.picked_points) > 0)
        # Disable save button if points are changed (before apply)
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(self.is_previewing)

    def display_segy_data(self):
        """Display SEGY data in the plot."""
        try:
            self.ax.clear()
            
            # Determine which data to display
            data_to_display = self.muted_data if self.is_previewing else self.segy_data
            
            # Use seisplot for consistent display
            seisplot.plot(
                data_to_display, 
                perc=100, 
                haxis="tracf", 
                hlabel="Trace no.", 
                vlabel="Time (ms)",
                plottype=self.plot_type,
                ax=self.ax
                )
            
            self.draw_picked_points()
            
            self.canvas.draw()
            self.update_buttons()  # Update buttons after drawing
            
        except Exception as e:
            error_message(self.console, f"Error displaying SEGY data: {str(e)}")
    
    def draw_picked_points(self):
        """Draw picked points and interpolated surface on the plot."""
        if not self.picked_points:
            return
        
        # Extract trace and sample indices
        trace_indices = [p[0] for p in self.picked_points]
        sample_indices = [p[1] for p in self.picked_points]
        
        # Draw points with different colors for first and last point
        if len(self.picked_points) == 1:
            self.ax.plot(trace_indices[0], sample_indices[0], 'o', color='yellow', markersize=8, 
                         markeredgecolor='black', zorder=10)
        else:
            # Draw first point in green
            self.ax.plot(trace_indices[0], sample_indices[0], 'o', color='green', markersize=8, 
                         markeredgecolor='black', zorder=10)
            
            # Draw last point in red
            self.ax.plot(trace_indices[-1], sample_indices[-1], 'o', color='red', markersize=8, 
                         markeredgecolor='black', zorder=10)
            
            # Draw middle points in yellow
            if len(self.picked_points) > 2:
                self.ax.plot(trace_indices[1:-1], sample_indices[1:-1], 'o', color='yellow', markersize=8, 
                             markeredgecolor='black', zorder=10)
        
        # Draw interpolated surface if we have at least 2 points
        if len(self.picked_points) >= 2:
            # Sort points by trace number
            sorted_points = sorted(self.picked_points, key=lambda p: p[0])
            sorted_trace_indices = [p[0] for p in sorted_points]
            sorted_sample_indices = [p[1] for p in sorted_points]
            all_traces = np.arange(self.segy_data.shape[0])
            if len(sorted_points) > 2:
                # Use cubic spline for smooth curve
                cs = CubicSpline(sorted_trace_indices, sorted_sample_indices, extrapolate=True)
                interp_surface = cs(all_traces)
            else:
                # Fallback to linear interpolation for 2 points
                interp_surface = np.interp(
                    all_traces,
                    sorted_trace_indices,
                    sorted_sample_indices,
                    left=sorted_sample_indices[0],
                    right=sorted_sample_indices[-1]
                )
            
            # Draw interpolated surface line
            self.ax.plot(all_traces, interp_surface, '-', color='white', linewidth=2, alpha=0.8, zorder=9)
            
            # Show taper zone with semi-transparent area
            if self.taper_length > 0:
                taper_surface = interp_surface + self.taper_length
                self.ax.fill_between(
                    all_traces, 
                    interp_surface, 
                    taper_surface, 
                    color='blue', 
                    alpha=0.3, 
                    label='Taper Zone'
                )
    
    def on_click(self, event):
        """Handle mouse clicks on the plot."""
        if event.inaxes != self.ax:
            return
        
        # Get click position (trace, sample)
        trace_idx = int(round(event.xdata))
        sample_idx = int(round(event.ydata))
        
        # Ensure indices are within data bounds
        if trace_idx < 0 or trace_idx >= self.segy_data.shape[1] or sample_idx < 0 or sample_idx >= self.segy_data.shape[0]:
            return
        
        # Right-click to remove the nearest point
        if event.button == 3:  # Right click
            if self.picked_points:
                # Find closest point
                closest_idx = self.find_closest_point(trace_idx, sample_idx)
                if closest_idx is not None:
                    self.picked_points.pop(closest_idx)
                    self.display_segy_data()
                    self.update_buttons()
            return
        
        # Left-click to add a point
        if event.button == 1:  # Left click
            # Check if point already exists at this trace
            for i, (t, _) in enumerate(self.picked_points):
                if t == trace_idx:
                    # Update point at this trace
                    self.picked_points[i] = (trace_idx, sample_idx)
                    self.display_segy_data()
                    self.update_buttons()
                    return
            
            # Add new point
            self.picked_points.append((trace_idx, sample_idx))
            self.display_segy_data()
            self.update_buttons()

    def find_closest_point(self, trace_idx, sample_idx):
        """Find index of the closest picked point to the given coordinates."""
        if not self.picked_points:
            return None
        
        # Calculate squared distances
        distances = [(i, (p[0] - trace_idx)**2 + (p[1] - sample_idx)**2) 
                     for i, p in enumerate(self.picked_points)]
        
        # Find minimum
        closest_idx, min_dist = min(distances, key=lambda x: x[1])
        
        # Check if point is close enough (within 20 pixels)
        if min_dist > 400:  # 20^2 = 400
            return None
            
        return closest_idx
    
    
    def on_taper_changed(self, value):
        """Handle changes to taper length."""
        self.taper_length = value
        self.display_segy_data()  # Redraw to show taper zone
    
    def reset_points(self):
        """Clear all picked points."""
        if not self.picked_points:
            return
            
        self.picked_points = []
        self.is_previewing = False  # Reset preview state
        self.muted_data = self.segy_data.copy()  # Reset muted data
        self.toggle_button.setEnabled(False)
        self.toggle_button.setText("Show Original")
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(False)
        self.display_segy_data()
        self.update_buttons()

    def toggle_preview(self):
        """Toggle between original and muted data display."""
        if not self.is_previewing and self.muted_data is None:
            return
            
        self.is_previewing = not self.is_previewing
        self.toggle_button.setText("Show Original" if self.is_previewing else "Show Muted")
        self.display_segy_data()
    
    def apply_muting(self):
        """Apply muting to the SEGY data based on picked surface."""
        if len(self.picked_points) < 2:
            QMessageBox.warning(
                self, 
                "Insufficient Points", 
                "Please pick at least 2 points to define a muting surface."
            )
            return
        
        info_message(self.console, "Applying muting with defined surface...")
        
        # Sort points by trace number
        sorted_points = sorted(self.picked_points, key=lambda p: p[0])
        info_message(self.console, f"Using {len(sorted_points)} points to define muting surface")
        
        # Extract trace and sample indices
        trace_indices = [p[0] for p in sorted_points]
        sample_indices = [p[1] for p in sorted_points]
        
        # Interpolate to get a continuous surface for all traces
        all_traces = np.arange(self.segy_data.shape[0])
        if len(trace_indices) > 2:
            cs = CubicSpline(trace_indices, sample_indices, extrapolate=True)
            interp_surface = cs(all_traces)
        else:
            interp_surface = np.interp(
                all_traces,
                trace_indices,
                sample_indices,
                left=sample_indices[0],  # Extend first point to left edge
                right=sample_indices[-1]  # Extend last point to right edge
            )
        
        muting_mask = np.ones_like(self.segy_data)        
        
        for trace_idx in range(self.segy_data.shape[0]):
            # Get the sample index where the muting surface crosses this trace
            surface_sample = int(interp_surface[trace_idx])
            
            if surface_sample <= 0:
                # Skip if muting surface is at or above the first sample
                continue                
            
            # Mute all samples above the surface (samples with lower indices = shallower time)
            muting_mask[trace_idx, :surface_sample] = 0
            
            # Apply taper below the surface
            taper_end = min(surface_sample + self.taper_length, self.segy_data.shape[1])
            if taper_end > surface_sample:
                taper_samples = taper_end - surface_sample
                # Create taper from 0 to 1 (0 at surface, gradually increasing to 1)
                taper = np.linspace(0, 1, taper_samples)
                muting_mask[trace_idx, surface_sample:taper_end] = taper
        
        # Apply mask to create muted data
        self.muted_data = self.segy_data * muting_mask
        
        # Summarize the operation
        info_message(self.console, f"Muting complete - Applied to all {self.segy_data.shape[0]} traces with taper length {self.taper_length}")
        
        # Update preview
        self.is_previewing = True
        self.toggle_button.setText("Show Original")
        self.toggle_button.setEnabled(True)
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(True)
        
        # Show preview
        self.display_segy_data()
        
    
    def save_changes(self):
        """Save the muted data to the SEGY file."""
        if self.muted_data is None or not self.is_previewing:
            QMessageBox.warning(
                self, 
                "No Changes Applied", 
                "Please apply muting first."
            )
            return
        
        info_message(self.console, "Saving muted data to SEGY file...")
        
        # Load original SEGY file
        segy_in = seisio.input(self.segy_path)
        
        # Create temporary output file
        temp_segy_path = self.segy_path + ".temp.segy"
        
        try:
            # Create output SEGY file with same parameters
            segy_out = seisio.output(
                temp_segy_path,
                ns=segy_in.ns,
                vsi=segy_in.vsi,
                endian=">", 
                format=5, 
                txtenc="ebcdic"
            )
            
            # Copy textual header
            header_text = segy_in.get_txthead()
            segy_out.log_txthead(txthead=header_text)

            # Copy binary header
            binhead = segy_in.get_binhead()
            segy_out.log_binhead(binhead=binhead)

            # Initialize output
            segy_out.init(textual=header_text, binary=binhead)

            # Read and write trace headers with muted data
            trace_headers = segy_in.read_all_headers()
            segy_out.write_traces(data=self.muted_data, headers=trace_headers)

            # Finalize the output file
            segy_out.finalize()
            
            # Replace original file with new file
            if os.path.exists(self.segy_path):
                os.remove(self.segy_path)
            os.rename(temp_segy_path, self.segy_path)
            
            success_message(self.console, f"SEGY file updated with muted data")
            self.accept()
            
        except Exception as e:
            error_message(self.console, f"Error writing SEGY file: {str(e)}")
            
            # Clean up temp file if it exists
            if os.path.exists(temp_segy_path):
                try:
                    os.remove(temp_segy_path)
                except:
                    pass
                    
            QMessageBox.critical(
                self, 
                "Error Saving", 
                f"Failed to save muted data to SEGY file: {str(e)}"
            )

