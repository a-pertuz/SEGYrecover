"""Results tab for SEGYRecover application."""

import os
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QComboBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import seisio
import seisplot

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
    # Define which tools to keep
    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class ResultsTab(QWidget):
    """Tab for displaying results of the digitization process."""
    
    # Signals
    newLineRequested = Signal()
    
    def __init__(self, console, work_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("results_tab")
        self.console = console
        self.work_dir = work_dir
        self.segy_data = None
        self.plot_type = "image"  # Default plot type
        
        # Create canvases for both plots
        self.segy_figure = Figure(constrained_layout=True)
        self.segy_canvas = FigureCanvas(self.segy_figure)
        self.segy_canvas.setObjectName("segy_canvas")
        self.segy_ax = self.segy_figure.add_subplot(111)
        
        self.spectrum_figure = Figure(constrained_layout=True)
        self.spectrum_canvas = FigureCanvas(self.spectrum_figure)
        self.spectrum_canvas.setObjectName("spectrum_canvas")
        self.spectrum_ax = self.spectrum_figure.add_subplot(111)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header = QLabel("Results Viewer")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel(
            "Here are the results of the digitization process. The SEGY file has been created and is ready for use in interpretation software. "
            "You can review the seismic data and its amplitude spectrum below."
        )
        instruction.setObjectName("description_label")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("content_splitter")
        splitter.setHandleWidth(6)  # Slightly wider splitter handle for better usability
        
        # Left panel - SEGY display
        segy_container = QGroupBox("Digitized SEGY")
        segy_container.setObjectName("segy_container")
        segy_layout = QVBoxLayout(segy_container)
        segy_layout.setContentsMargins(15, 15, 15, 15)
        segy_layout.setSpacing(10)
        
        # Add controls container
        controls_container = QWidget()
        controls_container.setObjectName("controls_container")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 5)
        
        # Plot type dropdown
        plot_type_label = QLabel("Display Type:")
        plot_type_label.setObjectName("plot_type_label")
        controls_layout.addWidget(plot_type_label)
        
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.setObjectName("plot_type_combo")
        self.plot_type_combo.addItem("Variable Density", "image")
        self.plot_type_combo.addItem("Wiggle", "wiggle")
        self.plot_type_combo.currentIndexChanged.connect(self._on_plot_type_changed)
        controls_layout.addWidget(self.plot_type_combo)
        
        # Add spacer to push controls to the left
        controls_layout.addStretch(1)
        
        # Add controls to the layout
        segy_layout.addWidget(controls_container)
        
        # Add canvas
        segy_layout.addWidget(self.segy_canvas, 1)  # 1 = stretch factor
        
        # Add toolbar
        segy_toolbar = SimpleNavigationToolbar(self.segy_canvas, self)
        segy_toolbar.setObjectName("segy_toolbar")
        segy_layout.addWidget(segy_toolbar)
        
        # Right panel - Amplitude spectrum
        spectrum_container = QGroupBox("Amplitude Spectrum")
        spectrum_container.setObjectName("spectrum_container")
        spectrum_layout = QVBoxLayout(spectrum_container)
        spectrum_layout.setContentsMargins(15, 15, 15, 15)
        spectrum_layout.setSpacing(10)
        
        # Add canvas
        spectrum_layout.addWidget(self.spectrum_canvas)
        
        # Add toolbar
        spectrum_toolbar = SimpleNavigationToolbar(self.spectrum_canvas, self)
        spectrum_toolbar.setObjectName("spectrum_toolbar")
        spectrum_layout.addWidget(spectrum_toolbar)
        
        # Add panels to splitter
        splitter.addWidget(segy_container)
        splitter.addWidget(spectrum_container)
        splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        
        layout.addWidget(splitter, 1)  # 1 = stretch factor
        
        # Bottom section with SEGY file info and new line button
        info_container = QWidget()
        info_container.setObjectName("file_info_container")
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(5, 10, 5, 5)
        info_layout.setSpacing(15)
        
        # SEGY file info
        info_frame = QGroupBox("File Information")
        info_frame.setObjectName("file_info_frame")
        info_frame_layout = QVBoxLayout(info_frame)
        info_frame_layout.setContentsMargins(15, 15, 15, 15)
        
        self.segy_info = QLabel("")
        self.segy_info.setObjectName("segy_info")
        self.segy_info.setWordWrap(True)
        info_frame_layout.addWidget(self.segy_info)
        
        # Add info frame to layout
        info_layout.addWidget(info_frame, 3)  # 3 = stretch factor
        
        # Button container for vertical alignment
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_container.setFixedWidth(150)
        button_container.setMinimumHeight(80)
        button_layout = QVBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        
        # New line button
        new_line_button = QPushButton("Start New Line")
        new_line_button.setObjectName("start_new_button")
        new_line_button.setFixedWidth(140)
        new_line_button.setFixedHeight(36)
        new_line_button.clicked.connect(self.newLineRequested.emit)
        button_layout.addWidget(new_line_button)
        
        info_layout.addWidget(button_container, 0)  # 0 = no stretch factor
        
        layout.addWidget(info_container)
    
    def _on_plot_type_changed(self, index):
        """Handle plot type change"""
        self.plot_type = self.plot_type_combo.currentData()
        self._update_segy_display()
    
    def display_results(self, segy_path, filtered_data, dt):
        """Display results from the digitization process."""
        if not os.path.exists(segy_path) or filtered_data is None:
            return
        
        # Show file path and information
        file_size = os.path.getsize(segy_path) / (1024 * 1024)  # Size in MB
        self.segy_info.setText(
            f"<b>SEGY File:</b> {os.path.basename(segy_path)} <br>"
            f"<b>Location:</b> {os.path.dirname(segy_path)} <br>"
            f"<b>Size:</b> {file_size:.2f} MB <br>"
            f"<b>Dimensions:</b> {filtered_data.shape[1]} traces × {filtered_data.shape[0]} samples"
        )
        
        # Store data for later use
        self.filtered_data = filtered_data
        self.dt = dt
        self.segy_path = segy_path
        
        # Display SEGY data
        self._display_segy(segy_path)
        
        # Display amplitude spectrum
        self._display_spectrum(filtered_data, dt)
    
    def _display_segy(self, segy_path):
        """Display SEGY section."""
        try:
            # Clear existing figure
            self.segy_ax.clear()
            
            # Use seisio and seisplot to display the SEGY data
            sio = seisio.input(segy_path)
            dataset = sio.read_all_traces()
            self.segy_data = dataset["data"]
            
            # Use optimized parameters for display
            seisplot.plot(
                self.segy_data, 
                perc=99, 
                haxis="tracf", 
                hlabel="Trace no.", 
                vlabel="Time (ms)",
                plottype=self.plot_type,
                ax=self.segy_ax,
            )
            
            self.segy_figure.tight_layout()
            self.segy_canvas.draw_idle()  # Use draw_idle for better performance
            
        except Exception as e:
            self.console.append(f"Error displaying SEGY results: {str(e)}")
            self.segy_ax.clear()
            self.segy_ax.text(0.5, 0.5, "Error loading SEGY data", 
                          ha='center', va='center', fontsize=12, color='red')
            self.segy_canvas.draw()
    
    def _update_segy_display(self):
        """Update the SEGY display with current plot type."""
        if not hasattr(self, 'segy_data') or self.segy_data is None:
            return
            
        self.segy_ax.clear()
        
        # Redraw the SEGY data with current plot type and optimized parameters
        seisplot.plot(
            self.segy_data, 
            perc=99, 
            haxis="tracf", 
            hlabel="Trace no.", 
            vlabel="Time (ms)",
            plottype=self.plot_type,
            ax=self.segy_ax,
            interpolation='nearest'  # Use nearest neighbor interpolation for faster display
        )
        
        self.segy_figure.tight_layout()
        self.segy_canvas.draw_idle()  # Use draw_idle for better performance
    
    def _display_spectrum(self, filtered_data, dt):
        """Display amplitude spectrum."""
        try:
            # Clear existing figure
            self.spectrum_ax.clear()
            
            # Calculate and plot spectrum
            fs = 1 / (dt / 1000)  # Convert dt from ms to s
            fs_filtered = np.zeros(filtered_data.shape, dtype=complex)
            
            for i in range(filtered_data.shape[1]):
                fs_filtered[:, i] = np.fft.fft(filtered_data[:, i])
            
            freqs = np.fft.fftfreq(filtered_data.shape[0], 1/fs)
            fsa_filtered = np.mean(np.abs(fs_filtered), axis=1)
            fsa_filtered = fsa_filtered/np.max(fsa_filtered)
            
            # Plot positive frequencies
            pos_freq_mask = freqs >= 1
            self.spectrum_ax.plot(freqs[pos_freq_mask], fsa_filtered[pos_freq_mask], 'r')
            self.spectrum_ax.set_xlim(0, 100)
            self.spectrum_ax.set_xlabel('Frequency (Hz)')
            self.spectrum_ax.set_ylabel('Normalized Amplitude')
            self.spectrum_ax.set_title('Averaged Amplitude Spectrum')
            self.spectrum_ax.grid(True)
            
            self.spectrum_figure.tight_layout()
            self.spectrum_canvas.draw_idle()  # Use draw_idle for better performance
            
        except Exception as e:
            self.console.append(f"Error displaying amplitude spectrum: {str(e)}")
            self.spectrum_ax.clear()
            self.spectrum_ax.text(0.5, 0.5, "Error creating amplitude spectrum", 
                          ha='center', va='center', fontsize=12, color='red')
            self.spectrum_canvas.draw()
