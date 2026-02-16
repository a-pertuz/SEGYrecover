"""Standalone Mute Topography Tool.

This script provides a standalone GUI for muting topography in SEGY files.
It replicates the functionality of the SEGYRecover Mute Topography Dialog.
"""

import sys
import os
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSpinBox, QMessageBox, QWidget, QFileDialog, QTextEdit
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.interpolate import CubicSpline

# Add src to path to allow imports if necessary
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    import seisio
    import seisplot
except ImportError as e:
    print(f"Error importing seismic libraries: {e}")
    print("Please ensure seisio and seisplot are installed in your environment.")

# --- Console Utilities (Copied/Adapted) ---

def _write_to_log(message):
    """Mock log writer."""
    # In a real app, this would write to a file.
    pass

def info_message(console, message):
    """Print an info message."""
    formatted = f'<br>{message}<br>'
    console.insertHtml(formatted)
    print(f"INFO: {message}")

def success_message(console, message):
    """Print a success message."""
    formatted = f'<br><span style="color:green;">&#10003; {message}</span><br>'
    console.insertHtml(formatted)
    print(f"SUCCESS: {message}")

def error_message(console, message):
    """Print an error message."""
    formatted = f'<br><span style="color:red;"><b>&#10060; ERROR:</b> {message}</span><br>'
    console.insertHtml(formatted)
    print(f"ERROR: {message}")

# --- Main Application Class ---

class MuteTopographyApp(QMainWindow):
    """Standalone application for muting topography in SEGY data."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Standalone Mute Topography")
        
        # Setup window size
        screen = QApplication.primaryScreen().geometry()
        window_width = int(min(screen.width(), 1920) * 0.8)
        window_height = int(min(screen.height(), 1080) * 0.8)
        self.resize(window_width, window_height)
        
        # Initialize data
        self.segy_path = None
        self.segy_data = None
        self.muted_data = None
        self.picked_points = []  # List of (trace_idx, sample_idx) tuples
        self.taper_length = 5    # Default taper length in samples
        self.plot_type = "image"  # Default plot type
        self.is_previewing = False
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the main window UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Mute Topography Tool")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Load Button Area
        load_layout = QHBoxLayout()
        self.load_button = QPushButton("Load SEGY File")
        self.load_button.setMinimumHeight(40)
        self.load_button.clicked.connect(self.load_segy)
        load_layout.addWidget(self.load_button)
        load_layout.addStretch()
        layout.addLayout(load_layout)
        
        # Instructions
        self.instructions = QLabel(
            "Load a SEGY file to begin. Then click on the seismic section to define a surface for muting."
        )
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)
        
        # Main plot area
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Connect mouse click event
        self.canvas.mpl_connect('button_press_event', self.on_click)
        
        # Add canvas to layout
        layout.addWidget(self.canvas, 1)
        
        # Controls panel
        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        
        # Taper length control
        taper_group = QGroupBox("Taper Settings")
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
        
        self.apply_button = QPushButton("Apply Muting")
        self.apply_button.clicked.connect(self.apply_muting)
        self.apply_button.setEnabled(False)
        
        self.reset_button = QPushButton("Reset Points")
        self.reset_button.clicked.connect(self.reset_points)
        self.reset_button.setEnabled(False)
        
        self.toggle_button = QPushButton("Show Original")
        self.toggle_button.clicked.connect(self.toggle_preview)
        self.toggle_button.setEnabled(False)
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.toggle_button)
        controls_layout.addWidget(button_group)
        
        # Save Button
        self.save_button = QPushButton("Save Result")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setEnabled(False)
        controls_layout.addWidget(self.save_button)
        
        layout.addWidget(controls_panel)
        
        # Console Output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        layout.addWidget(self.console)
        
        info_message(self.console, "Ready.")

    def load_segy(self):
        """Open file dialog to load a SEGY file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open SEGY File", "", "SEGY Files (*.segy *.sgy);;All Files (*)"
        )
        
        if not file_path:
            return
            
        self.segy_path = file_path
        info_message(self.console, f"Loading SEGY data from {os.path.basename(self.segy_path)}")
        
        try:
            sio = seisio.input(self.segy_path)
            dataset = sio.read_all_traces()
            self.segy_data = dataset["data"]
            self.muted_data = self.segy_data.copy()
            
            # Reset state
            self.picked_points = []
            self.is_previewing = False
            self.toggle_button.setText("Show Original")
            
            self.display_segy_data()
            self.update_buttons()
            
            self.instructions.setText(
                "Click on the seismic section to define a surface for muting. "
                "Right-click to remove points. "
                "Click 'Apply Muting' to preview, then 'Save Result' to overwrite the file."
            )
            success_message(self.console, "File loaded successfully.")
            
        except Exception as e:
            error_message(self.console, f"Error loading SEGY file: {str(e)}")

    def update_buttons(self):
        """Enable or disable buttons based on state."""
        has_points = len(self.picked_points) >= 2
        self.apply_button.setEnabled(has_points)
        self.reset_button.setEnabled(len(self.picked_points) > 0)
        
        # Save is enabled only if we have applied muting (previewing)
        self.save_button.setEnabled(self.is_previewing)
        self.toggle_button.setEnabled(self.is_previewing)

    def display_segy_data(self):
        """Display SEGY data in the plot."""
        if self.segy_data is None:
            return
            
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
            self.update_buttons()
            
        except Exception as e:
            error_message(self.console, f"Error displaying SEGY data: {str(e)}")
    
    def draw_picked_points(self):
        """Draw picked points and interpolated surface on the plot."""
        if not self.picked_points:
            return
        
        # Extract trace and sample indices
        trace_indices = [p[0] for p in self.picked_points]
        sample_indices = [p[1] for p in self.picked_points]
        
        # Draw points
        if len(self.picked_points) == 1:
            self.ax.plot(trace_indices[0], sample_indices[0], 'o', color='yellow', markersize=8, 
                         markeredgecolor='black', zorder=10)
        else:
            self.ax.plot(trace_indices[0], sample_indices[0], 'o', color='green', markersize=8, 
                         markeredgecolor='black', zorder=10)
            self.ax.plot(trace_indices[-1], sample_indices[-1], 'o', color='red', markersize=8, 
                         markeredgecolor='black', zorder=10)
            if len(self.picked_points) > 2:
                self.ax.plot(trace_indices[1:-1], sample_indices[1:-1], 'o', color='yellow', markersize=8, 
                             markeredgecolor='black', zorder=10)
        
        # Draw interpolated surface
        if len(self.picked_points) >= 2:
            sorted_points = sorted(self.picked_points, key=lambda p: p[0])
            sorted_trace_indices = [p[0] for p in sorted_points]
            sorted_sample_indices = [p[1] for p in sorted_points]
            all_traces = np.arange(self.segy_data.shape[0])
            
            if len(sorted_points) > 2:
                cs = CubicSpline(sorted_trace_indices, sorted_sample_indices, extrapolate=True)
                interp_surface = cs(all_traces)
            else:
                interp_surface = np.interp(
                    all_traces,
                    sorted_trace_indices,
                    sorted_sample_indices,
                    left=sorted_sample_indices[0],
                    right=sorted_sample_indices[-1]
                )
            
            self.ax.plot(all_traces, interp_surface, '-', color='white', linewidth=2, alpha=0.8, zorder=9)
            
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
        if self.segy_data is None or event.inaxes != self.ax:
            return
        
        trace_idx = int(round(event.xdata))
        sample_idx = int(round(event.ydata))
        
        if trace_idx < 0 or trace_idx >= self.segy_data.shape[0] or sample_idx < 0 or sample_idx >= self.segy_data.shape[1]:
            return
        
        if event.button == 3:  # Right click
            if self.picked_points:
                closest_idx = self.find_closest_point(trace_idx, sample_idx)
                if closest_idx is not None:
                    self.picked_points.pop(closest_idx)
                    self.display_segy_data()
            return
        
        if event.button == 1:  # Left click
            for i, (t, _) in enumerate(self.picked_points):
                if t == trace_idx:
                    self.picked_points[i] = (trace_idx, sample_idx)
                    self.display_segy_data()
                    return
            
            self.picked_points.append((trace_idx, sample_idx))
            self.display_segy_data()

    def find_closest_point(self, trace_idx, sample_idx):
        """Find index of the closest picked point."""
        if not self.picked_points:
            return None
        
        distances = [(i, (p[0] - trace_idx)**2 + (p[1] - sample_idx)**2) 
                     for i, p in enumerate(self.picked_points)]
        
        closest_idx, min_dist = min(distances, key=lambda x: x[1])
        
        if min_dist > 400:
            return None
            
        return closest_idx
    
    def on_taper_changed(self, value):
        """Handle changes to taper length."""
        self.taper_length = value
        if self.segy_data is not None:
            self.display_segy_data()
    
    def reset_points(self):
        """Clear all picked points."""
        if not self.picked_points:
            return
            
        self.picked_points = []
        self.is_previewing = False
        self.muted_data = self.segy_data.copy()
        self.toggle_button.setText("Show Original")
        self.display_segy_data()

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
            QMessageBox.warning(self, "Insufficient Points", "Please pick at least 2 points.")
            return
        
        info_message(self.console, "Applying muting with defined surface...")
        
        sorted_points = sorted(self.picked_points, key=lambda p: p[0])
        trace_indices = [p[0] for p in sorted_points]
        sample_indices = [p[1] for p in sorted_points]
        
        all_traces = np.arange(self.segy_data.shape[0])
        if len(trace_indices) > 2:
            cs = CubicSpline(trace_indices, sample_indices, extrapolate=True)
            interp_surface = cs(all_traces)
        else:
            interp_surface = np.interp(
                all_traces,
                trace_indices,
                sample_indices,
                left=sample_indices[0],
                right=sample_indices[-1]
            )
        
        muting_mask = np.ones_like(self.segy_data)        
        
        for trace_idx in range(self.segy_data.shape[0]):
            surface_sample = int(interp_surface[trace_idx])
            
            if surface_sample <= 0:
                continue                
            
            muting_mask[trace_idx, :surface_sample] = 0
            
            taper_end = min(surface_sample + self.taper_length, self.segy_data.shape[1])
            if taper_end > surface_sample:
                taper_samples = taper_end - surface_sample
                taper = np.linspace(0, 1, taper_samples)
                muting_mask[trace_idx, surface_sample:taper_end] = taper
        
        self.muted_data = self.segy_data * muting_mask
        
        info_message(self.console, f"Muting complete. Taper length: {self.taper_length}")
        
        self.is_previewing = True
        self.toggle_button.setText("Show Original")
        self.display_segy_data()
        
    def save_changes(self):
        """Save the muted data to the SEGY file."""
        if self.muted_data is None or not self.is_previewing:
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Save", 
            "This will overwrite the original SEGY file. Are you sure?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return

        info_message(self.console, "Saving muted data to SEGY file...")
        
        try:
            segy_in = seisio.input(self.segy_path)
            temp_segy_path = self.segy_path + ".temp.segy"
            
            segy_out = seisio.output(
                temp_segy_path,
                ns=segy_in.ns,
                vsi=segy_in.vsi,
                endian=">", 
                format=5, 
                txtenc="ebcdic"
            )
            
            header_text = segy_in.get_txthead()
            segy_out.log_txthead(txthead=header_text)

            binhead = segy_in.get_binhead()
            segy_out.log_binhead(binhead=binhead)

            segy_out.init(textual=header_text, binary=binhead)

            trace_headers = segy_in.read_all_headers()
            segy_out.write_traces(data=self.muted_data, headers=trace_headers)

            segy_out.finalize()
            
            if os.path.exists(self.segy_path):
                os.remove(self.segy_path)
            os.rename(temp_segy_path, self.segy_path)
            
            success_message(self.console, f"SEGY file updated successfully: {self.segy_path}")
            QMessageBox.information(self, "Success", "File saved successfully.")
            
        except Exception as e:
            error_message(self.console, f"Error writing SEGY file: {str(e)}")
            if os.path.exists(temp_segy_path):
                try:
                    os.remove(temp_segy_path)
                except:
                    pass
            QMessageBox.critical(self, "Error Saving", f"Failed to save: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MuteTopographyApp()
    window.show()
    sys.exit(app.exec())
