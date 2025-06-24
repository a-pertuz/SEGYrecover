"""AGC RMS Dialog for SEGYRecover application."""

import os
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QRadioButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QSplitter, QWidget, QApplication
)
from scipy.ndimage import uniform_filter1d

import seisio
import seisplot

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from ..utils.console_utils import success_message, error_message, info_message

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""

    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class AGCRMSDialog(QDialog):
    """Dialog for applying AGC (Automatic Gain Control) RMS to SEGY data."""
    def __init__(self, segy_path, console, work_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apply AGC RMS")
        self.setObjectName("agc_rms_dialog")


        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)   
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        self.setGeometry(100, 100, window_width, window_height)
        
        self.segy_path = segy_path
        self.console = console
        self.work_dir = work_dir
        self.output_file = None
        self.seismic_data = None
        self.preview_data = None
        
        # Load SEGY metadata and data
        sio = seisio.input(segy_path)
        self.dt_ms = sio.vsi / 1000.0  
        dataset = sio.read_all_traces()
        self.seismic_data = dataset["data"]
        
        # Create figures for preview
        self.original_figure = Figure(constrained_layout=True)
        self.original_canvas = FigureCanvas(self.original_figure)
        self.original_ax = self.original_figure.add_subplot(111)
        self.original_toolbar = SimpleNavigationToolbar(self.original_canvas, self)

        self.preview_figure = Figure(constrained_layout=True)
        self.preview_canvas = FigureCanvas(self.preview_figure)
        self.preview_ax = self.preview_figure.add_subplot(111)
        self.preview_toolbar = SimpleNavigationToolbar(self.preview_canvas, self)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the dialog's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        # Header section
        header = QLabel("AGC RMS Amplitude Balancing")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Description
        description = QLabel(
            "Apply Automatic Gain Control (AGC) using RMS method to balance trace amplitudes. "
            "This will enhance weaker signals and reduce the dominance of stronger ones."
        )
        description.setObjectName("description_label")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Parameters group at the top
        params_group = QGroupBox("AGC Parameters")
        params_group.setObjectName("params_group")
        params_group.setMaximumWidth(200)  
        params_layout = QVBoxLayout(params_group)
        
        # Gate length
        gate_layout = QHBoxLayout()
        gate_label = QLabel("Gate Length (ms):")
        gate_label.setObjectName("gate_label")
        gate_layout.addWidget(gate_label)
        
        self.gate_spinbox = QSpinBox()
        self.gate_spinbox.setObjectName("gate_spinbox")
        self.gate_spinbox.setRange(10, 2000)
        self.gate_spinbox.setSingleStep(10)
        self.gate_spinbox.setValue(500)  # Default: 500ms
        self.gate_spinbox.valueChanged.connect(self.update_preview)  
        gate_layout.addWidget(self.gate_spinbox)
        params_layout.addLayout(gate_layout)
        
        save_group = QGroupBox("Save Options")
        save_group.setObjectName("save_group")
        save_group.setMaximumWidth(250)  
        save_layout = QVBoxLayout(save_group)
        
        save_file_layout = QHBoxLayout()
        self.save_with_suffix_radio = QRadioButton("Save as new file with suffix")
        self.save_with_suffix_radio.setObjectName("save_with_suffix_radio")
        self.save_with_suffix_radio.setChecked(True)  # Default option
        save_file_layout.addWidget(self.save_with_suffix_radio)

        self.suffix_input = QLineEdit()
        self.suffix_input.setObjectName("suffix_input")
        self.suffix_input.setText("_agc")  
        self.suffix_input.setMaximumWidth(20)  
        save_file_layout.addWidget(self.suffix_input)

        save_layout.addLayout(save_file_layout)
        
        # Overwrite option
        self.overwrite_radio = QRadioButton("Overwrite original file")
        self.overwrite_radio.setObjectName("overwrite_radio")
        save_layout.addWidget(self.overwrite_radio)
        
        # Create a horizontal layout for top section with both groups
        top_layout = QHBoxLayout()
        top_layout.addWidget(params_group)
        top_layout.addWidget(save_group)
        top_layout.addStretch(1)  # This pushes both groups to the left
        layout.addLayout(top_layout)
        
        # Main content with splitter for side-by-side comparison
        preview_splitter = QSplitter(Qt.Horizontal)
        preview_splitter.setObjectName("preview_splitter")
        
        # Original data preview (left side)
        original_group = QGroupBox("Original Data")
        original_layout = QVBoxLayout(original_group)
        original_layout.addWidget(self.original_canvas)
        original_layout.addWidget(self.original_toolbar)
        preview_splitter.addWidget(original_group)
        
        # Processed data preview (right side)
        preview_group = QGroupBox("AGC RMS Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self.preview_canvas)
        preview_layout.addWidget(self.preview_toolbar)
        preview_splitter.addWidget(preview_group)
        
        # Add equal sizing
        preview_splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        layout.addWidget(preview_splitter, 1)  # 1 = stretch factor
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.setObjectName("button_box")
        save_button = button_box.button(QDialogButtonBox.Save)
        save_button.setText("Save")
        save_button.clicked.connect(self._process_and_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Display initial preview
        self.display_original_data()
        self.update_preview()
    
    def _apply_agc_rms(self, data, gate_samples, desired_rms=1.0):
        """Apply AGC RMS to all traces in the data array."""
        data_processed = data.copy()
        for i in range(data_processed.shape[0]):
            trace = data_processed[i]
            trace_power = trace ** 2
            smooth_power = uniform_filter1d(trace_power, size=gate_samples, mode='reflect')
            rms = np.sqrt(np.maximum(smooth_power, 1e-10))  # Prevent division by zero
            data_processed[i] = trace / rms * desired_rms
        return data_processed

    def _get_output_file_path(self, gate_ms):
        """Determine output file path and handle user confirmation if needed."""
        input_file = self.segy_path
        if self.save_with_suffix_radio.isChecked():
            suffix = self.suffix_input.text()
            if not suffix:
                suffix = f"_agc_{gate_ms}ms"
            base_name, ext = os.path.splitext(input_file)
            output_file = f"{base_name}{suffix}{ext}"
        else:
            output_file = input_file

        # Confirm overwrite if file exists and isn't the original
        if os.path.exists(output_file) and output_file != input_file:
            response = QMessageBox.question(
                self,
                "Confirm Overwrite",
                f"File {output_file} already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if response == QMessageBox.No:
                info_message(self.console, "Operation cancelled by user")
                return None
        return output_file

    def display_original_data(self):
        """Display the original seismic data."""
        if self.seismic_data is None:
            return
            
        self.original_ax.clear()
        
        # Use seisplot for consistent display with all data
        seisplot.plot(
            self.seismic_data,
            perc=100,
            haxis="tracf",
            hlabel="Trace",
            vlabel="Time (ms)",
            plottype="image",
            ax=self.original_ax
        )
        
        self.original_ax.set_title('Original SEGY Data')
        self.original_canvas.draw()

    def update_preview(self):
        """Update the preview with AGC RMS applied."""
        if self.seismic_data is None:
            return
            
        try:
            gate_ms = self.gate_spinbox.value()
                        
            gate_samples = max(1, int(round(gate_ms / self.dt_ms)))
            
            data_processed = self._apply_agc_rms(self.seismic_data, gate_samples)
            
            self.preview_data = data_processed
            
            self.preview_ax.clear()
            
            seisplot.plot(
                data_processed,
                perc=100,
                haxis="tracf",
                hlabel="Trace",
                vlabel="Time (ms)",
                plottype="image",
                ax=self.preview_ax
            )
            
            self.preview_ax.set_title(f'AGC RMS Preview (Gate: {gate_ms} ms)')
            self.preview_canvas.draw()
            
        except Exception as e:
            error_message(self.console, f"Error generating preview: {str(e)}")

    def _process_and_save(self):
        """Process the SEGY data and save according to selected options."""
        
        # Get parameters
        gate_ms = self.gate_spinbox.value()
        desired_rms = 1.0  
        
        # Determine output file path
        output_file = self._get_output_file_path(gate_ms)
        if output_file is None:
            return
        
        try:
            # Load original SEGY data
            sio = seisio.input(self.segy_path)
            dataset = sio.read_all_traces()
            data = dataset["data"].copy()  # Make a copy to avoid modifying the original
            dt_ms = sio.vsi / 1000.0  # Sample interval in ms
            
            # Convert gate from ms to samples
            gate_samples = max(1, int(round(gate_ms / dt_ms)))
                        
            # Apply AGC RMS to all traces
            data = self._apply_agc_rms(data, gate_samples, desired_rms)
                        
            # Write out the processed data
            try:
                # Create a temp file for output
                temp_output_file = output_file + ".temp.segy"
                
                # Get headers from original file
                input_segy = seisio.input(self.segy_path)
                
                # Create output file with same parameters
                output_segy = seisio.output(
                    temp_output_file,
                    ns=input_segy.ns,
                    vsi=input_segy.vsi,
                    endian=">", 
                    format=5, 
                    txtenc="ebcdic"
                )
                
                # Copy textual header
                header_text = input_segy.get_txthead()
                output_segy.log_txthead(txthead=header_text)
                
                # Copy binary header
                binhead = input_segy.get_binhead()
                output_segy.log_binhead(binhead=binhead)
                
                # Initialize output
                output_segy.init(textual=header_text, binary=binhead)
                
                # Get trace headers from original file
                trace_headers = input_segy.read_all_headers()
                
                # Write traces with headers
                output_segy.write_traces(data=data, headers=trace_headers)
                output_segy.finalize()
                
                # Replace original file with new file
                if os.path.exists(output_file):
                    os.remove(output_file)
                os.rename(temp_output_file, output_file)
                
                success_message(self.console, f"Successfully saved AGC RMS processed data to {output_file}")
                
                # Store the output file path
                self.output_file = output_file
                
                # Close dialog with accept status
                self.accept()
                
            except Exception as e:
                error_message(self.console, f"Error saving data: {str(e)}")
                
                # Clean up temp file if it exists
                if os.path.exists(temp_output_file):
                    try:
                        os.remove(temp_output_file)
                    except:
                        pass
            
        except Exception as e:
            error_message(self.console, f"Error processing data: {str(e)}")
