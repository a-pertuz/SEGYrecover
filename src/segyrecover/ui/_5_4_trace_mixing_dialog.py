"""Trace Mixing Dialog for SEGYRecover application."""

import os
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QRadioButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QComboBox, QCheckBox, QSplitter, QWidget,
    QProgressBar, QApplication
)
import seisio
import seisplot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from ..utils.console_utils import success_message, error_message, info_message

class MixingWorker(QThread):
    """Worker thread for trace mixing operations."""
    progress = Signal(int)
    finished = Signal(np.ndarray)
    error = Signal(str)
    
    def __init__(self, data, method, window_size, weights=None):
        super().__init__()
        self.data = data
        self.method = method
        self.window_size = window_size
        self.weights = weights
        
    def run(self):
        try:
            if self.method == 'weighted':
                result = self._weighted_trace_mix(self.data, self.window_size, self.weights)
            elif self.method == 'median':
                result = self._median_mix(self.data, self.window_size)
            # elif self.method == 'weighted_median':
            #     result = self._weighted_median_mix(self.data, self.window_size, self.weights)
            else:
                self.error.emit(f"Unknown mixing method: {self.method}")
                return
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f"Error during trace mixing: {str(e)}")
    
    def _handle_boundaries(self, trace_idx, n_traces):
        """Handle boundary conditions with mirroring."""
        if trace_idx < 0:
            return -trace_idx
        elif trace_idx >= n_traces:
            return 2*n_traces - trace_idx - 2
        return trace_idx
    
    def _weighted_trace_mix(self, data, window_size, weights=None):
        """Apply weighted average trace mixing using vectorized operations."""
        # Create a copy of the data to avoid modifying the original
        result = data.copy()
        n_traces = data.shape[0]
        n_samples = data.shape[1]
        
        # Create default weights if not provided
        if weights is None or len(weights) != window_size:
            # Create symmetric weights centered around the middle
            weights = np.linspace(1, window_size//2+1, window_size//2+1)
            weights = np.concatenate([weights[:-1], weights[::-1]])
        
        # Normalize weights
        weights = np.array(weights) / np.sum(weights)
        
        # Half window size for indexing
        half_window = window_size // 2
        
        # Process in smaller chunks to report progress
        chunk_size = max(1, n_traces // 100)
        
        for chunk_start in range(0, n_traces, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_traces)
            
            # Apply mixing for this chunk of traces
            for i in range(chunk_start, chunk_end):
                mixed_trace = np.zeros(n_samples)
                
                # Sum weighted traces in the window
                for j in range(window_size):
                    trace_idx = self._handle_boundaries(i - half_window + j, n_traces)
                    mixed_trace += data[trace_idx] * weights[j]
                
                # Apply the result
                result[i] = mixed_trace
            
            # Report progress
            self.progress.emit(int(chunk_end * 100 / n_traces))
            
        return result
    
    def _median_mix(self, data, window_size):
        """Apply median trace mixing using vectorized operations where possible."""
        # Create a copy of the data to avoid modifying the original
        result = data.copy()
        n_traces = data.shape[0]
        n_samples = data.shape[1]
        
        # Half window size for indexing
        half_window = window_size // 2
        
        # Process in smaller chunks to report progress
        chunk_size = max(1, n_traces // 100)
        
        for chunk_start in range(0, n_traces, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_traces)
            
            # Apply mixing for this chunk of traces
            for i in range(chunk_start, chunk_end):
                # Pre-allocate window traces array
                window_traces = np.zeros((window_size, n_samples))
                
                # Gather traces in the window
                for j in range(window_size):
                    trace_idx = self._handle_boundaries(i - half_window + j, n_traces)
                    window_traces[j] = data[trace_idx]
                
                # Compute median trace (already vectorized in numpy)
                result[i] = np.median(window_traces, axis=0)
            
            # Report progress
            self.progress.emit(int(chunk_end * 100 / n_traces))
                
        return result
    
    def _weighted_median_mix(self, data, window_size, weights=None):
        """Apply optimized weighted median trace mixing."""
        # Create a copy of the data to avoid modifying the original
        result = data.copy()
        n_traces = data.shape[0]
        n_samples = data.shape[1]
        
        # Create default weights if not provided
        if weights is None or len(weights) != window_size:
            # Create symmetric weights centered around the middle
            weights = np.linspace(1, window_size//2+1, window_size//2+1)
            weights = np.concatenate([weights[:-1], weights[::-1]])
        
        # Convert weights to integers for weighted median
        # Use smaller scaling to reduce memory usage
        int_weights = np.round(np.array(weights) * 10).astype(int)
        # Ensure at least weight of 1 for each value
        int_weights = np.maximum(int_weights, 1)
        
        # Half window size for indexing
        half_window = window_size // 2
        
        # Process in smaller chunks to report progress
        chunk_size = max(1, n_traces // 100)
        
        for chunk_start in range(0, n_traces, chunk_size):
            chunk_end = min(chunk_start + chunk_size, n_traces)
            
            # Apply mixing for this chunk of traces
            for i in range(chunk_start, chunk_end):
                mixed_trace = np.zeros(n_samples)
                
                # For each sample, compute weighted median more efficiently
                for s in range(n_samples):
                    # Use a more memory-efficient approach - store values and their counts
                    values = []
                    counts = []
                    
                    # Gather sample values from traces in window
                    for j in range(window_size):
                        trace_idx = self._handle_boundaries(i - half_window + j, n_traces)
                        val = data[trace_idx, s]
                        
                        # Check if value exists in our list
                        found = False
                        for idx, existing_val in enumerate(values):
                            if val == existing_val:
                                counts[idx] += int_weights[j]
                                found = True
                                break
                        
                        if not found:
                            values.append(val)
                            counts.append(int_weights[j])
                    
                    # Skip if no values collected (shouldn't happen)
                    if not values:
                        continue
                    
                    # Convert to arrays for sorting
                    values = np.array(values)
                    counts = np.array(counts)
                    
                    # Sort by values
                    sort_idx = np.argsort(values)
                    values = values[sort_idx]
                    counts = counts[sort_idx]
                    
                    # Calculate weighted median
                    total = counts.sum()
                    cumsum = np.cumsum(counts)
                    median_idx = np.searchsorted(cumsum, total / 2)
                    mixed_trace[s] = values[median_idx]
                
                # Apply the result
                result[i] = mixed_trace
            
            # Report progress
            self.progress.emit(int(chunk_end * 100 / n_traces))
                
        return result

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""

    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class TraceMixingDialog(QDialog):
    """Dialog for applying various trace mixing methods to SEGY data."""
    
    def __init__(self, segy_path, console, work_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apply Trace Mixing")
        self.setObjectName("trace_mixing_dialog")
        
        # Setup window size and positioning
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
        self.preview_params = None  # Store parameters used for preview
        self.worker = None
        
        # Load SEGY metadata and data
        sio = seisio.input(segy_path)
        self.sio = sio
        dataset = sio.read_all_traces()
        self.seismic_data = dataset["data"]
        self.trace_headers = sio.read_all_headers()

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
        header = QLabel("Trace Mixing")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Description
        description = QLabel(
            "Apply trace mixing to enhance coherent signals and attenuate random noise. "
            "This process combines adjacent traces to create a smoother seismic section."
        )
        description.setObjectName("description_label")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Parameters and save options container
        params_save_container = QWidget()
        params_save_layout = QHBoxLayout(params_save_container)
        params_save_layout.setContentsMargins(0, 0, 0, 0)
        params_save_layout.setSpacing(20)
        
        # Left side: Parameters and description container
        params_desc_container = QWidget()
        params_desc_layout = QHBoxLayout(params_desc_container)
        params_desc_layout.setContentsMargins(0, 0, 0, 0)
        params_desc_layout.setSpacing(5)
        
        # Parameters group (left side)
        params_group = QGroupBox("Mixing Parameters")
        params_group.setObjectName("params_group")
        params_group.setFixedWidth(300)
        params_layout = QVBoxLayout(params_group)
        
        # Mixing method
        method_layout = QHBoxLayout()
        method_label = QLabel("Mixing Method:")
        method_label.setObjectName("method_label")
        method_layout.addWidget(method_label)

        self.method_combo = QComboBox()
        self.method_combo.setObjectName("method_combo")
        self.method_combo.addItem("Weighted Average", "weighted")
        self.method_combo.addItem("Median", "median")
        # self.method_combo.addItem("Weighted Median", "weighted_median")
        self.method_combo.currentIndexChanged.connect(self._update_method_explanation)
        self.method_combo.currentIndexChanged.connect(self._update_weights_input_visibility)
        method_layout.addWidget(self.method_combo)
        params_layout.addLayout(method_layout)

        # Weights input (for weighted average) - separate layout
        self.weights_widget = QWidget()
        weights_layout = QHBoxLayout(self.weights_widget)
        weights_layout.setContentsMargins(0, 0, 0, 0)
        self.weights_label = QLabel("Weights (comma-separated):")
        self.weights_label.setObjectName("weights_label")
        weights_layout.addWidget(self.weights_label)
        self.weights_input = QLineEdit()
        self.weights_input.setObjectName("weights_input")
        self.weights_input.setText("1,2,3,2,1")  # Default weights for 5-point window
        weights_layout.addWidget(self.weights_input)
        params_layout.addWidget(self.weights_widget)

        # Window size input (for median) - separate layout
        self.window_size_widget = QWidget()
        window_size_layout = QHBoxLayout(self.window_size_widget)
        window_size_layout.setContentsMargins(0, 0, 0, 0)
        self.window_size_label = QLabel("Window size (odd integer):")
        self.window_size_label.setObjectName("window_size_label")
        window_size_layout.addWidget(self.window_size_label)
        self.window_size_input = QLineEdit()
        self.window_size_input.setObjectName("window_size_input")
        self.window_size_input.setText("5")
        window_size_layout.addWidget(self.window_size_input)
        params_layout.addWidget(self.window_size_widget)

        # Hide window size widget initially
        self.window_size_widget.setVisible(False)

        self.method_explanation = QLabel("")
        self.method_explanation.setObjectName("method_explanation")
        self.method_explanation.setWordWrap(True)
        params_layout.addWidget(self.method_explanation)

        # Add params_group to params_desc_layout so it appears at the start
        params_desc_layout.addWidget(params_group)

        # Set the layout for params_desc_container
        params_desc_container.setLayout(params_desc_layout)

        # Add the params+description container to main layout
        params_save_layout.addWidget(params_desc_container)
        
        # Save options group (right side)
        save_group = QGroupBox("Save Options")
        save_group.setObjectName("save_group")
        save_group.setFixedWidth(300)
        save_layout = QVBoxLayout(save_group)
        
        # Save type radios and suffix input in a horizontal layout
        save_type_layout = QHBoxLayout()
        self.save_with_suffix_radio = QRadioButton("Save as new file with suffix")
        self.save_with_suffix_radio.setObjectName("save_with_suffix_radio")
        self.save_with_suffix_radio.setChecked(True)  # Default option
        save_type_layout.addWidget(self.save_with_suffix_radio)
        
        # Suffix input field
        self.suffix_input = QLineEdit()
        self.suffix_input.setObjectName("suffix_input")
        self.suffix_input.setText("_mix")  # Default suffix
        save_type_layout.addWidget(self.suffix_input)

        save_layout.addLayout(save_type_layout)
        
        # Overwrite option
        self.overwrite_radio = QRadioButton("Overwrite original file")
        self.overwrite_radio.setObjectName("overwrite_radio")
        save_layout.addWidget(self.overwrite_radio)
        
        # Add save group to container
        params_save_layout.addWidget(save_group)
        params_save_layout.addStretch(1)  # Push groups to the left

        layout.addWidget(params_save_container)

        # Main content with splitter for side-by-side comparison
        preview_splitter = QSplitter(Qt.Horizontal)
        preview_splitter.setObjectName("preview_splitter")
        
        # Original data preview (left side)
        original_group = QGroupBox("Original Data")
        original_layout = QVBoxLayout(original_group)
        original_layout.addWidget(self.original_toolbar)
        original_layout.addWidget(self.original_canvas)
        preview_splitter.addWidget(original_group)
        
        # Processed data preview (right side)
        preview_group = QGroupBox("Trace Mixing Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self.preview_toolbar)
        preview_layout.addWidget(self.preview_canvas)
        preview_splitter.addWidget(preview_group)
        
        # Add equal sizing
        preview_splitter.setSizes([int(self.width() * 0.5), int(self.width() * 0.5)])
        layout.addWidget(preview_splitter, 1)  # 1 = stretch factor
        
        # Move Apply Mixing button above the button box for better distinction
        self.apply_button = QPushButton("Apply Mixing")
        self.apply_button.setObjectName("apply_button")
        self.apply_button.clicked.connect(self._apply_mixing)
        self.apply_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        layout.addWidget(self.apply_button)

        # Button box with Save/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.setObjectName("button_box")
        save_button = button_box.button(QDialogButtonBox.Save)
        save_button.clicked.connect(self._save_applied_data)
        save_button.setEnabled(False)  # Initially disabled
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Add the progress bar in the main layout between parameters and preview area
        layout.addWidget(self.progress_bar)
        
        # Initialize UI state
        self._update_method_explanation(0)  # Set initial explanation
        self.display_original_data()
            
    def _update_method_explanation(self, index):
        """Update the method explanation based on selected method."""
        method = self.method_combo.currentData()
        explanations = {
            "weighted": "Computes a weighted average of traces within the mixing window. "
                       "Each trace is multiplied by its corresponding weight before averaging.",
            "median": "Computes the median value for each sample across all traces in the window. "
                     "Weights are ignored for this method.",
            "weighted_median": "Computes a weighted median where traces with higher weights "
                              "contribute more to the median calculation. "
        }
        self.method_explanation.setText(explanations.get(method, ""))
    
    def _update_weights_input_visibility(self, index):
        """Show/hide weights or window size input depending on method."""
        method = self.method_combo.currentData()
        if method == "weighted":
            self.weights_widget.setVisible(True)
            self.window_size_widget.setVisible(False)
        elif method == "median":
            self.weights_widget.setVisible(False)
            self.window_size_widget.setVisible(True)
        else:
            self.weights_widget.setVisible(True)
            self.window_size_widget.setVisible(False)

    def _validate_weights(self, weights_text):
        """Validate and parse weights, returning weights and calculated window size."""
        try:
            if not weights_text.strip():
                # Use default weights if empty
                weights = [1, 2, 3, 2, 1]
                info_message(self.console, "Using default weights: 1,2,3,2,1")
                return weights, len(weights)
                
            weights = [float(w) for w in weights_text.split(",")]
            
            # Validate minimum number of weights
            if len(weights) < 3:
                error_message(self.console, "Minimum 3 weights required. Using default weights.")
                weights = [1, 2, 3, 2, 1]
                return weights, len(weights)
            
            # Validate maximum number of weights (reasonable limit)
            if len(weights) > 21:
                error_message(self.console, "Maximum 21 weights allowed. Using first 21 weights.")
                weights = weights[:21]
            
            # Ensure odd number of weights for symmetric mixing
            if len(weights) % 2 == 0:
                info_message(self.console, "Even number of weights detected. Adding a weight of 1 to make it odd.")
                weights.append(1.0)
            
            return weights, len(weights)
            
        except Exception as e:
            error_message(self.console, f"Error parsing weights: {str(e)}. Using default weights.")
            weights = [1, 2, 3, 2, 1]
            return weights, len(weights)
    
    def _validate_window_size(self, window_size_text):
        """Validate and parse window size for median mix."""
        try:
            window_size = int(window_size_text)
            if window_size < 3:
                error_message(self.console, "Minimum window size is 3. Using 5.")
                window_size = 5
            if window_size > 21:
                error_message(self.console, "Maximum window size is 21. Using 21.")
                window_size = 21
            if window_size % 2 == 0:
                info_message(self.console, "Even window size detected. Adding 1 to make it odd.")
                window_size += 1
            return window_size
        except Exception as e:
            error_message(self.console, f"Error parsing window size: {str(e)}. Using 5.")
            return 5

    def display_original_data(self):
        """Display the original seismic data."""
        if self.seismic_data is None:
            return
            
        self.original_ax.clear()
        
        # Use the entire dataset instead of a subset
        data = self.seismic_data
        
        # Use seisplot for consistent display
        seisplot.plot(
            data,
            perc=100,
            haxis="tracf",
            hlabel="Trace",
            vlabel="Time/Depth Sample",
            plottype="image",
            ax=self.original_ax
        )
        
        self.original_ax.set_title('Original SEGY Data')
        self.original_canvas.draw()
    
    def update_preview(self):
        """Update the preview with trace mixing applied."""
        # This method is now replaced by _apply_mixing
        pass
    
    def _apply_mixing(self):
        """Apply trace mixing and visualize the results."""
        if self.seismic_data is None:
            return

        try:
            method = self.method_combo.currentData()
            if method == "median":
                window_size = self._validate_window_size(self.window_size_input.text())
                weights = None
            else:
                weights, window_size = self._validate_weights(self.weights_input.text())
            data = self.seismic_data.copy()
            self.progress_bar.setValue(0)
            self.setEnabled(False)
            self.apply_button.setEnabled(False)  # Disable apply button while running
            # Ensure previous worker is cleaned up
            if self.worker is not None:
                self.worker.quit()
                self.worker.wait()
                self.worker = None
            self.worker = MixingWorker(data, method, window_size, weights)
            self.worker.setParent(self)  # Set parent to dialog for proper cleanup
            self.worker.progress.connect(self._update_progress)
            self.worker.finished.connect(self._apply_finished)
            self.worker.error.connect(self._apply_error)
            self.worker.finished.connect(self._cleanup_worker)
            self.worker.error.connect(self._cleanup_worker)
            self.worker.start()
        except Exception as e:
            error_message(self.console, f"Error applying trace mixing: {str(e)}")
            self.setEnabled(True)
            self.apply_button.setEnabled(True)

    def _cleanup_worker(self, *args):
        """Cleanup worker and re-enable UI."""
        self.worker = None
        self.setEnabled(True)
        self.apply_button.setEnabled(True)

    def closeEvent(self, event):
        """Ensure worker thread is stopped if dialog is closed."""
        if self.worker is not None and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
            self.worker = None
        event.accept()

    def _apply_finished(self, mixed_data):
        """Handle completion of trace mixing application."""
        if not self:  # Dialog might be deleted
            return
        self.preview_data = mixed_data
        method = self.method_combo.currentData()
        if method == "median":
            window_size = self._validate_window_size(self.window_size_input.text())
            weights_str = ""
        else:
            weights_str = self.weights_input.text()
            window_size = self._validate_weights(self.weights_input.text())[1]
        self.preview_params = {
            'method': method,
            'weights': weights_str,
            'window_size': window_size
        }
        
        # Display the results
        self.preview_ax.clear()
        
        # Use seisplot for consistent display
        seisplot.plot(
            mixed_data,
            perc=100,
            haxis="tracf",
            hlabel="Trace",
            vlabel="Time/Depth Sample",
            plottype="image",
            ax=self.preview_ax
        )
        
        method = self.method_combo.currentData()
        self.preview_ax.set_title(f'Applied: {method.replace("_", " ").title()} Mix')
        self.preview_canvas.draw()
                
        self.setEnabled(True)
        self.apply_button.setEnabled(True)
        
        # Enable the Save button now that mixing is applied
        save_button = self.findChild(QDialogButtonBox).button(QDialogButtonBox.Save)
        save_button.setEnabled(True)

        success_message(self.console, "Trace mixing applied successfully")

    def _apply_error(self, error_msg):
        """Handle errors during trace mixing application."""
        error_message(self.console, error_msg)
        self.setEnabled(True)
        self.apply_button.setEnabled(True)

    def _save_applied_data(self):
        """Save the already applied trace mixing data."""
        if self.preview_data is None:
            error_message(self.console, "No applied data to save. Please apply mixing first.")
            return

        # Determine output file path
        output_file = self._get_output_file_path()
        if output_file is None:
            return  # User cancelled

        # Save the applied data directly
        try:
            # Save processed data to SEGY file
            sio = self.sio
            headers = sio.read_all_headers().copy()

            import shutil
            if output_file != self.segy_path:
                shutil.copy2(self.segy_path, output_file)

            out = seisio.output(
                output_file,
                ns=self.preview_data.shape[1],
                vsi=sio.vsi,
                endian=">",
                format=5,
                txtenc="ebcdic"
            )
            # Copy textual and binary headers
            out.log_txthead(txthead=sio.get_txthead())
            out.log_binhead(binhead=sio.get_binhead())
            out.init(textual=sio.get_txthead(), binary=sio.get_binhead())
            # Write traces and headers
            out.write_traces(data=self.preview_data, headers=headers)
            out.finalize()
            self.output_file = output_file
            success_message(self.console, f"Trace mixing result saved: {output_file}")
            self.accept()
            
        except Exception as e:
            error_message(self.console, f"Error saving processed data: {str(e)}")

    def _get_output_file_path(self):
        """Determine output file path and handle user confirmation if needed."""
        input_file = self.segy_path
        if self.save_with_suffix_radio.isChecked():
            # Get suffix from input field
            suffix = self.suffix_input.text()
            if not suffix:
                suffix = "_mix"  # Default if empty
                
            # Create output path with suffix
            base_name, ext = os.path.splitext(input_file)
            output_file = f"{base_name}{suffix}{ext}"
        else:
            # Overwrite original file
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
    
    def _update_progress(self, value):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)
