"""Results tab for SEGYRecover application."""

import os
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QComboBox, QDialog, QMessageBox
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import seisio
import seisplot

from ._5_1_edit_header import SEGYHeaderEditorDialog
from ._5_2_mute_topography import MuteTopographyDialog
from ._5_3_agc_rms_dialog import AGCRMSDialog
from ._5_4_trace_mixing_dialog import TraceMixingDialog
from ..utils.console_utils import section_header, success_message, error_message, info_message

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
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
        
    def reset(self):
        """Reset the results tab state completely when starting a new line."""
        # Reset data state
        self.segy_data = None
        self.filtered_data = None
        self.dt = None
        self.segy_path = None        # Disable buttons
        self.edit_header_button.setEnabled(False)
        self.mute_topo_button.setEnabled(False)
        self.agc_rms_button.setEnabled(False)
        self.trace_mixing_button.setEnabled(False)
        
        # Clear SEGY display
        self.segy_ax.clear()
        self.segy_ax.set_title("No data available")
        self.segy_ax.text(0.5, 0.5, "Process a new line to view results", 
                    ha='center', va='center', fontsize=12, color='gray')
        self.segy_ax.axis('off')
        self.segy_canvas.draw()
        
        # Clear spectrum display
        self.spectrum_ax.clear()
        self.spectrum_ax.set_title("No data available")
        self.spectrum_ax.text(0.5, 0.5, "Process a new line to view spectrum", 
                    ha='center', va='center', fontsize=12, color='gray')
        self.spectrum_ax.axis('off')
        self.spectrum_canvas.draw()


    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        # Header section
        header = QLabel("Results Viewer")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel(
            "You can review the digitized seismic data and its amplitude spectrum below. "
            "Use the buttons to edit the SEGY header, mute topography, apply AGC RMS, "
            "or apply trace mixing to the seismic data."
        )
        instruction.setObjectName("description_label")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
          # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("content_splitter")
        splitter.setHandleWidth(6)  
        
        # Left panel - SEGY display (wider)
        segy_container = QGroupBox("Digitized SEGY")
        segy_container.setObjectName("segy_container")
        segy_layout = QVBoxLayout(segy_container)
        segy_layout.setContentsMargins(15, 15, 15, 15)

        # Add canvas
        segy_layout.addWidget(self.segy_canvas, 1)  # 1 = stretch factor
        
        # Add toolbar
        segy_toolbar = SimpleNavigationToolbar(self.segy_canvas, self)
        segy_toolbar.setObjectName("segy_toolbar")
        segy_layout.addWidget(segy_toolbar)
        
        # Right panel with Spectrum and Buttons
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Amplitude spectrum at the top
        spectrum_container = QGroupBox("Amplitude Spectrum")
        spectrum_container.setObjectName("spectrum_container")
        spectrum_layout = QVBoxLayout(spectrum_container)
        spectrum_layout.setContentsMargins(15, 15, 15, 15)
        spectrum_layout.setSpacing(5)
        
        # Add canvas
        spectrum_layout.addWidget(self.spectrum_canvas)
        
        # Add toolbar
        spectrum_toolbar = SimpleNavigationToolbar(self.spectrum_canvas, self)
        spectrum_toolbar.setObjectName("spectrum_toolbar")
        spectrum_layout.addWidget(spectrum_toolbar)
        
        # Add spectrum container to right panel
        right_layout.addWidget(spectrum_container, 1)  # 1 = stretch factor
        
        # Button container with center alignment
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QVBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(10)
        
        # Edit SEGY Header button
        self.edit_header_button = QPushButton("Edit SEGY Header")
        self.edit_header_button.setObjectName("edit_header_button")
        self.edit_header_button.clicked.connect(self.edit_segy_header)
        button_layout.addWidget(self.edit_header_button)
        
        # Mute Topography button
        self.mute_topo_button = QPushButton("Mute Topography")
        self.mute_topo_button.setObjectName("mute_topo_button")
        self.mute_topo_button.clicked.connect(self.open_mute_topography_dialog)
        button_layout.addWidget(self.mute_topo_button)
        
        # AGC RMS button
        self.agc_rms_button = QPushButton("Apply AGC RMS")
        self.agc_rms_button.setObjectName("agc_rms_button")
        self.agc_rms_button.clicked.connect(self.open_agc_rms_dialog)
        self.agc_rms_button.setEnabled(False)
        button_layout.addWidget(self.agc_rms_button)
        
        # Trace Mixing button
        self.trace_mixing_button = QPushButton("Apply Trace Mixing")
        self.trace_mixing_button.setObjectName("trace_mixing_button")
        self.trace_mixing_button.clicked.connect(self.open_trace_mixing_dialog)
        self.trace_mixing_button.setEnabled(False)
        button_layout.addWidget(self.trace_mixing_button)
        
        # New line button
        new_line_button = QPushButton("Start New Line")
        new_line_button.setObjectName("start_new_button")
        new_line_button.clicked.connect(self.newLineRequested.emit)
        button_layout.addWidget(new_line_button)
        
        # Add button container to right panel
        right_layout.addWidget(button_container)

        splitter.addWidget(segy_container)
        splitter.addWidget(right_panel)
        splitter.setSizes([int(self.width() * 0.7), int(self.width() * 0.3)])
        
        layout.addWidget(splitter, 1)  # 1 = stretch factor
    
    
    def display_results(self, segy_path, filtered_data, dt):
        """Display results from the digitization process."""

        self.filtered_data = filtered_data
        self.dt = dt
        self.segy_path = segy_path        
        self.edit_header_button.setEnabled(True)
        self.mute_topo_button.setEnabled(True)
        self.agc_rms_button.setEnabled(True)
        self.trace_mixing_button.setEnabled(True)
        
        # Display SEGY data
        self._display_segy(segy_path)
        
        # Display amplitude spectrum
        self._display_spectrum(filtered_data, dt)
    
    def _display_segy(self, segy_path):
        """Display SEGY section."""

        # Clear existing figure
        self.segy_ax.clear()
        
        # Use seisio and seisplot to display the SEGY data
        sio = seisio.input(segy_path)
        dataset = sio.read_all_traces()
        self.segy_data = dataset["data"]
        
        seisplot.plot(
            self.segy_data, 
            perc=100, 
            haxis="tracf", 
            hlabel="Trace no.", 
            vlabel="Time (ms)",
            ax=self.segy_ax,
        )
        
        self.segy_canvas.draw_idle()  
            
    
    def _display_spectrum(self, filtered_data, dt):
        """Display amplitude spectrum."""
        try:
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
            self.spectrum_ax.xaxis.label.set_fontsize(8)
            self.spectrum_ax.yaxis.label.set_fontsize(8)
            self.spectrum_ax.title.set_fontsize(11)
            self.spectrum_ax.grid(True)
            
            self.spectrum_canvas.draw_idle()  
            
        except Exception as e:
            self.console.append(f"Error displaying amplitude spectrum: {str(e)}")
            self.spectrum_ax.clear()
            self.spectrum_ax.text(0.5, 0.5, "Error creating amplitude spectrum", 
                          ha='center', va='center', fontsize=12, color='red')
            self.spectrum_canvas.draw()

    def edit_segy_header(self):
        """Open dialog to edit SEGY header."""

        section_header(self.console, "SEGY HEADER EDITOR")
        info_message(self.console, "Opening SEGY Header Editor dialog...")

        dialog = SEGYHeaderEditorDialog(
            segy_path=self.segy_path,
            console=self.console,
            work_dir=self.work_dir,
            parent=self
        )
        
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            info_message(self.console, "Reloading data from updated SEGY file...")
            try:
                self._display_segy(self.segy_path)
                success_message(self.console, "SEGY header updated successfully.")
            except Exception as e:
                error_message(self.console, f"Error reloading SEGY file after header edit: {str(e)}")
        else:
            info_message(self.console, "SEGY header editing cancelled.")

    def open_mute_topography_dialog(self):
        """Open the mute topography dialog to allow editing SEGY data."""

        section_header(self.console, "MUTE TOPOGRAPHY")
        info_message(self.console, "Opening Mute Topography dialog...")

        dialog = MuteTopographyDialog(
            segy_path=self.segy_path,
            console=self.console,
            work_dir=self.work_dir,
            parent=self
        )
        
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            info_message(self.console, "Reloading data from updated SEGY file after muting topography...")
            try:
                sio = seisio.input(self.segy_path)
                dataset = sio.read_all_traces()
                updated_data = dataset["data"]
                self.filtered_data = updated_data
                self.segy_data = updated_data
                self._display_segy(self.segy_path)
                self._display_spectrum(updated_data.T, self.dt)
                success_message(self.console, "Muted SEGY data loaded successfully.")
            except Exception as e:
                error_message(self.console, f"Error reloading SEGY file after muting: {str(e)}")
        else:
            info_message(self.console, "Mute Topography dialog cancelled.")

    def open_agc_rms_dialog(self):
        """Open the AGC RMS dialog to apply AGC to SEGY data."""
        section_header(self.console, "AGC RMS")
        info_message(self.console, "Opening AGC RMS dialog...")

        dialog = AGCRMSDialog(
            segy_path=self.segy_path,
            console=self.console,
            work_dir=self.work_dir,
            parent=self
        )
        
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            try:
                output_file = dialog.output_file
                if output_file != self.segy_path:
                    self.segy_path = output_file
                sio = seisio.input(self.segy_path)
                dataset = sio.read_all_traces()
                updated_data = dataset["data"]
                self.filtered_data = updated_data
                self.segy_data = updated_data
                self._display_segy(self.segy_path)
                self._display_spectrum(updated_data.T, self.dt)
            except Exception as e:
                error_message(self.console, f"Error reloading SEGY file after AGC RMS: {str(e)}")
        else:
            info_message(self.console, "AGC RMS dialog cancelled.")

    def open_trace_mixing_dialog(self):
        """Open the Trace Mixing dialog to apply mixing to SEGY data."""
        section_header(self.console, "TRACE MIXING")
        info_message(self.console, "Opening Trace Mixing dialog...")

        dialog = TraceMixingDialog(
            segy_path=self.segy_path,
            console=self.console,
            work_dir=self.work_dir,
            parent=self
        )
        
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            try:
                output_file = dialog.output_file
                if output_file != self.segy_path:
                    self.segy_path = output_file
                sio = seisio.input(self.segy_path)
                dataset = sio.read_all_traces()
                updated_data = dataset["data"]
                self.filtered_data = updated_data
                self.segy_data = updated_data
                self._display_segy(self.segy_path)
                self._display_spectrum(updated_data.T, self.dt)
                success_message(self.console, "Trace mixing processed data loaded successfully.")
            except Exception as e:
                error_message(self.console, f"Error reloading SEGY file after trace mixing: {str(e)}")
        else:
            info_message(self.console, "Trace Mixing dialog cancelled.")
