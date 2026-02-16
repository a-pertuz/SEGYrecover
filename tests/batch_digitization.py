"""
SEGYRecover - Batch vectorization Tool
======================================
Ultra-simple interface for batch processing multiple seismic images.

Usage:
    python batch_vectorization.py
    
Features:
    - Select multiple images from IMAGES folder
    - Automatically validates required files (.par, .roi, .geometry)
    - Batch vectorization with optional AGC and Trace Mixing
    - Save with optional suffix
    - Text-based console output only
"""

import os
import sys
import traceback
import re
from pathlib import Path

# Setup path for imports - must be done before any other imports
_script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_script_dir / "src"))

# MOCK UI MODULES TO PREVENT CIRCULAR IMPORT
# The core module imports UI components which causes a circular dependency
# when running this script. We mock the UI modules since we don't need them here.
from unittest.mock import MagicMock
sys.modules['segyrecover.ui'] = MagicMock()
sys.modules['segyrecover.ui._4_2_coords_dialogs'] = MagicMock()
# Ensure CoordinateAssignmentDialog is available on the mock
sys.modules['segyrecover.ui._4_2_coords_dialogs'].CoordinateAssignmentDialog = MagicMock()

import numpy as np
import cv2
from scipy.ndimage import uniform_filter1d
import seisio

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QCheckBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QComboBox, QLineEdit, QProgressBar, QFileDialog, QMessageBox,
    QFormLayout, QFrame
)
from PySide6.QtGui import QFont, QTextCursor

# Import core modules
from segyrecover.core._1_image_processor import ImageProcessor
from segyrecover.core._2_amplitude_extractor import AmplitudeExtractor
from segyrecover.core._3_data_processor import DataProcessor


class ConsoleOutput:
    """Simple console output handler that writes to terminal."""
    
    def __init__(self):
        pass
    
    def _strip_html(self, text):
        """Remove HTML tags from text."""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    def write(self, text):
        """Write text to console."""
        print(text)
    
    def insertHtml(self, html):
        """Handle HTML input from core modules by stripping tags and printing."""
        text = self._strip_html(html)
        if text.strip():
            print(text.strip())
    
    def section_header(self, title):
        """Write a section header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    
    def info(self, message):
        """Write an info message."""
        print(f"[INFO] {message}")
    
    def success(self, message):
        """Write a success message."""
        print(f"[✓] {message}")
    
    def error(self, message):
        """Write an error message."""
        print(f"[✗] {message}")
    
    def warning(self, message):
        """Write a warning message."""
        print(f"[!] {message}")
    
    def progress(self, current, total, message=""):
        """Write progress information."""
        percentage = int((current / total) * 100) if total > 0 else 0
        print(f"[{percentage}%] {message}")


class BatchProcessor(QThread):
    """Background thread for batch processing images."""
    
    progress_update = Signal(int, int, str)  # current, total, message
    image_completed = Signal(str, bool, str)  # image_name, success, message
    finished = Signal()
    
    def __init__(self, selected_images, work_dir, console, options):
        super().__init__()
        self.selected_images = selected_images
        self.work_dir = work_dir
        self.console = console
        self.options = options
        self._is_running = True
    
    def stop(self):
        """Stop the processing."""
        self._is_running = False
    
    def run(self):
        """Run the batch processing."""
        total = len(self.selected_images)
        
        for idx, image_info in enumerate(self.selected_images):
            if not self._is_running:
                self.console.warning("Batch processing cancelled by user")
                break
            
            image_name = image_info['name']
            image_path = image_info['path']
            
            self.progress_update.emit(idx, total, f"Processing {image_name}...")
            self.console.section_header(f"PROCESSING: {image_name}")
            
            try:
                success = self._process_single_image(image_path)
                
                if success:
                    self.image_completed.emit(image_name, True, "Completed successfully")
                    self.console.success(f"Completed: {image_name}")
                else:
                    self.image_completed.emit(image_name, False, "Failed")
                    self.console.error(f"Failed: {image_name}")
                    
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.image_completed.emit(image_name, False, error_msg)
                self.console.error(f"Error processing {image_name}: {str(e)}")
                self.console.write(traceback.format_exc())
        
        self.progress_update.emit(total, total, "Batch processing completed")
        self.finished.emit()
    
    def _process_single_image(self, image_path):
        """Process a single image through the complete pipeline."""
        
        # Step 1: Load image
        self.console.info("Loading image...")
        img_array = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img_array is None:
            self.console.error("Failed to load image")
            return False
        
        # Step 2: Load parameters
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        par_path = os.path.join(self.work_dir, "PARAMETERS", f"{base_name}.par")
        
        self.console.info(f"Loading parameters from {os.path.basename(par_path)}...")
        parameters = self._load_parameters(par_path)
        if not parameters:
            self.console.error("Failed to load parameters")
            return False
        
        # Step 3: Load and apply ROI
        roi_path = os.path.join(self.work_dir, "ROI", f"{base_name}.roi")
        
        self.console.info(f"Loading ROI from {os.path.basename(roi_path)}...")
        binary_rectified_image = self._apply_roi(img_array, roi_path)
        if binary_rectified_image is None:
            self.console.error("Failed to apply ROI")
            return False
        
        # Step 4: vectorization process
        self.console.info("Starting vectorization...")
        
        # Create a dummy progress bar object
        class DummyProgress:
            def start(self, title, maximum): pass
            def update(self, value, message=None): pass
            def finish(self): pass
            def wasCanceled(self): return False
        
        progress_bar = DummyProgress()
        
        # Initialize processors
        image_processor = ImageProcessor(progress_bar, self.console, self.work_dir)
        amplitude_extractor = AmplitudeExtractor(progress_bar, self.console, self.work_dir)
        data_processor = DataProcessor(progress_bar, self.console, self.work_dir)
        
        # Step 4.1: Remove timelines
        self.console.info("Removing timelines...")
        image_clean, image_timelines = image_processor.remove_timelines(
            binary_rectified_image,
            parameters["HE"],
            parameters["HLT"],
            parameters.get("TPT", 30)
        )
        
        if image_clean is None:
            self.console.error("Timeline removal failed")
            return False
        
        # Step 4.2: Detect baselines
        self.console.info("Detecting baselines...")
        image_baselines, raw_baselines, clean_baselines, final_baselines = \
            image_processor.detect_baselines(
                image_clean,
                parameters["TLT"],
                parameters["BDB"],
                parameters["BDE"],
                parameters["BFT"]
            )
        
        if final_baselines is None or len(final_baselines) == 0:
            self.console.error("Baseline detection failed")
            return False
        
        self.console.info(f"Detected {len(final_baselines)} traces")
        
        # Step 4.3: Extract amplitudes
        self.console.info("Extracting amplitudes...")
        raw_amplitude = amplitude_extractor.extract_amplitude(image_clean, final_baselines)
        processed_amplitude = amplitude_extractor.process_amplitudes(raw_amplitude)
        
        # Step 4.4: Resample and filter
        self.console.info("Resampling and filtering data...")
        old_times = np.linspace(parameters["TWT_P1"], parameters["TWT_P3"], 
                                processed_amplitude.shape[0])
        new_times = np.arange(parameters["TWT_P1"], 
                              parameters["TWT_P3"] + parameters["DT"], 
                              parameters["DT"])
        
        resampled = data_processor.resample_data(processed_amplitude, old_times, new_times)
        filtered_data = data_processor.filter_data(resampled, parameters)
        
        self.console.info(f"Data shape: {filtered_data.shape[0]} samples × {filtered_data.shape[1]} traces")
        
        # --- SAVE RAW (FILTERED) ---
        base_segy_path = os.path.join(self.work_dir, "SEGY", f"{base_name}.segy")
        self.console.info(f"Writing base SEGY: {os.path.basename(base_segy_path)}...")
        if not self._write_segy_file(filtered_data, final_baselines, base_name, base_segy_path, parameters["DT"], parameters["F1"], parameters["F2"], parameters["F3"], parameters["F4"]):
             self.console.error("Failed to write base SEGY file")
             return False
        
        current_data = filtered_data
        current_suffix = ""

        # Step 5: Apply optional AGC
        if self.options['apply_agc']:
            agc_window = self.options['agc_window']
            self.console.info(f"Applying AGC with {agc_window} ms window...")
            current_data = self._apply_agc(current_data, agc_window, parameters["DT"])
            
            current_suffix = f"_agc{agc_window}"
            agc_segy_path = os.path.join(self.work_dir, "SEGY", f"{base_name}{current_suffix}.segy")
            self.console.info(f"Writing AGC SEGY: {os.path.basename(agc_segy_path)}...")
            self._write_segy_file(current_data, final_baselines, base_name, agc_segy_path, parameters["DT"], parameters["F1"], parameters["F2"], parameters["F3"], parameters["F4"])
        
        # Step 6: Apply optional Trace Mixing
        if self.options['apply_mixing']:
            self.console.info(f"Applying trace mixing ({self.options['mixing_method']})...")
            current_data = self._apply_trace_mixing(
                current_data, 
                self.options['mixing_method'],
                self.options['mixing_window'],
                self.options.get('mixing_weights')
            )
            
            current_suffix += "_mix"
            mix_segy_path = os.path.join(self.work_dir, "SEGY", f"{base_name}{current_suffix}.segy")
            self.console.info(f"Writing Mixed SEGY: {os.path.basename(mix_segy_path)}...")
            self._write_segy_file(current_data, final_baselines, base_name, mix_segy_path, parameters["DT"], parameters["F1"], parameters["F2"], parameters["F3"], parameters["F4"])

        return True
    
    def _write_segy_file(self, data, baselines, base_name, output_path, dt, f1, f2, f3, f4):
        """Write SEGY file with seisio."""
        try:
            # Ensure SEGY directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Transpose data to (traces, samples) format
            data_transposed = data.T
            
            # Create SEGY file
            ns = data.shape[0]  # Number of samples
            nt = len(baselines)
            vsi = float(dt * 1000)  # Sample interval in microseconds
            
            # Load coordinates if geometry file exists
            geometry_path = os.path.join(self.work_dir, "GEOMETRY", f"{base_name}.geometry")
            trace_coords = None
            
            if os.path.exists(geometry_path):
                try:
                    trace_coords = self._load_coordinates(geometry_path, nt, base_name)
                except:
                    pass
            
            # Calculate stats for text header
            profile_length = 0.0
            trace_spacing = 0.0
            
            if trace_coords is not None:
                # Calculate total SEGY profile length based on trace coordinates
                diffs = np.diff(trace_coords, axis=0)
                distances = np.sqrt((diffs[:, 0])**2 + (diffs[:, 1])**2)
                profile_length = np.sum(distances)

                # Calculate average trace spacing in meters
                trace_diffs = np.diff(trace_coords, axis=0)
                trace_distances = np.sqrt((trace_diffs[:, 0])**2 + (trace_diffs[:, 1])**2)
                trace_spacing = np.mean(trace_distances)

            segy_out = seisio.output(
                output_path,
                ns=ns,
                vsi=vsi,
                endian=">",
                format=5,
                txtenc="ebcdic"
            )
            
            # Create textual header
            text_header = []
            for i in range(40):  # SEGY standard: 40 lines of 80 characters
                text_header.append('' * 80)  # Initialize with spaces

            text_header[0] = f'{"SEGY FILE vectorizED BY SEGYRECOVER":<80}'
            text_header[1] = f'{"ORIGINAL IMAGE: " + base_name:<80}'
            text_header[2] = f'{"SAMPLE INTERVAL: " + str(dt) + " MS":<80}'
            text_header[3] = f'{"TRACES: " + str(nt) + ", SAMPLES: " + str(ns):<80}'
            text_header[4] = f'{"PROFILE LENGTH: " + f"{profile_length:.2f} m":<80}'
            text_header[5] = f'{"TRACE SPACING: " + f"{trace_spacing:.2f} m":<80}'
            text_header[6] = f'{"FILTER: " + str(f1) + "-" + str(f2) + "-" + str(f3) + "-" + str(f4) + " HZ":<80}'
            text_header[7] = f'{"COORDINATE SYSTEM: UTM":<80}'
            
            text_header_str = "".join(text_header)
            
            # Create binary header
            binary_header = segy_out.binhead_template
            binary_header["nt"] = float(nt)  # Number of traces
            binary_header["ns"] = float(ns)  # Number of samples per trace
            binary_header["dt"] = float(dt * 1000)  # Sample interval in microseconds
            segy_out.log_binhead(binhead=binary_header)
            
            # Create trace headers
            headers = segy_out.headers_template(nt=nt)
            headers["tracl"] = np.arange(1, nt + 1, dtype=float)  # Trace sequence number
            headers["dt"] = float(dt * 1000)  # Sample interval in microseconds
            headers["ns"] = float(ns)  # Number of samples per trace
            headers["trid"] = 1  # Trace identification code (1 for seismic data)
            headers["duse"] = 2  # Data use (2 for standard)
            headers["delrt"] = 0  # Delay time for the first trace (optional)
            headers["cdp"] = np.arange(1, nt + 1)  # Common depth point
            
            # Add coordinates if available
            if trace_coords is not None:
                headers['sx'] = trace_coords[:, 0]  # Source X coordinate
                headers['sy'] = trace_coords[:, 1]  # Source Y coordinate
                headers['gx'] = headers['sx']  # Receiver X coordinate (same as source for now)
                headers['gy'] = headers['sy']  # Receiver Y coordinate (same as source for now)
            
            # Initialize and write data
            segy_out.init(textual=text_header_str, binary=binary_header)
            segy_out.write_traces(data=data_transposed, headers=headers)
            segy_out.finalize()
            
            return True
            
        except Exception as e:
            self.console.error(f"Error writing SEGY file: {str(e)}")
            import traceback
            self.console.write(traceback.format_exc())
            return False
            
        except Exception as e:
            self.console.error(f"Error writing SEGY file: {str(e)}")
            import traceback
            self.console.write(traceback.format_exc())
            return False
    
    def _load_coordinates(self, geometry_path, n_baselines, base_name):
        """Load coordinates from geometry file and interpolate to baselines."""
        try:
            # Load geometry data
            geom_data = []
            with open(geometry_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        cdp = int(parts[0])
                        x = float(parts[1])
                        y = float(parts[2])
                        geom_data.append([cdp, x, y])
            
            if len(geom_data) < 2:
                return None
            
            geom_data = np.array(geom_data)
            
            # Check for FLIP file
            # 0: First CDP in geometry -> First trace (Normal)
            # 1: Last CDP in geometry -> First trace (Flipped)
            flip_mode = 0
            flip_path = os.path.join(self.work_dir, "FLIP", f"{base_name}.flip")
            
            if os.path.exists(flip_path):
                try:
                    with open(flip_path, 'r') as f:
                        content = f.read().strip()
                        if content:
                            flip_mode = int(content)
                            self.console.info(f"Found FLIP file: mode {flip_mode}")
                except Exception as e:
                    self.console.warning(f"Error reading FLIP file: {e}")
            
            # Interpolate coordinates for all baselines
            cdp_values = geom_data[:, 0]
            x_values = geom_data[:, 1]
            y_values = geom_data[:, 2]
            
            # Determine start and end CDPs based on flip mode
            # We use the order in the geometry file
            if flip_mode == 1:
                # Flipped: Trace 1 corresponds to the LAST CDP in geometry
                start_cdp = cdp_values[-1]
                end_cdp = cdp_values[0]
            else:
                # Normal: Trace 1 corresponds to the FIRST CDP in geometry
                start_cdp = cdp_values[0]
                end_cdp = cdp_values[-1]
                
            # Create target CDP values for baselines
            baseline_cdps = np.linspace(start_cdp, end_cdp, n_baselines)
            
            # Sort geometry data by CDP for interpolation (np.interp requires sorted xp)
            sort_idx = np.argsort(cdp_values)
            cdp_sorted = cdp_values[sort_idx]
            x_sorted = x_values[sort_idx]
            y_sorted = y_values[sort_idx]
            
            # Interpolate X and Y
            x_interp = np.interp(baseline_cdps, cdp_sorted, x_sorted)
            y_interp = np.interp(baseline_cdps, cdp_sorted, y_sorted)
            
            # Stack coordinates
            coordinates = np.column_stack([x_interp, y_interp])
            
            return coordinates
            
        except Exception as e:
            self.console.warning(f"Could not load geometry: {str(e)}")
            return None
    
    def _load_parameters(self, par_path):
        """Load parameters from .par file."""
        if not os.path.exists(par_path):
            return None
        
        try:
            params = {}
            with open(par_path, "r") as f:
                for line in f:
                    if '\t' in line:
                        key, value = line.strip().split('\t', 1)
                        # Convert to int for numeric parameters
                        try:
                            params[key] = int(value)
                        except ValueError:
                            params[key] = value
            
            # Validate required parameters
            required = ["HE", "HLT", "TLT", "BDB", "BDE", "BFT", "DT", 
                       "TWT_P1", "TWT_P3", "F1", "F2", "F3", "F4"]
            
            for req in required:
                if req not in params:
                    self.console.error(f"Missing required parameter: {req}")
                    return None
            
            # Set default TPT if not present
            if "TPT" not in params:
                params["TPT"] = 30
            
            return params
            
        except Exception as e:
            self.console.error(f"Error loading parameters: {str(e)}")
            return None
    
    def _apply_roi(self, img_array, roi_path):
        """Load ROI and apply perspective transformation."""
        if not os.path.exists(roi_path):
            return None
        
        try:
            # Load ROI points
            points = []
            with open(roi_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2:
                        points.append((float(parts[0]), float(parts[1])))
            
            if len(points) != 4:
                self.console.error(f"Invalid ROI file: expected 4 points, got {len(points)}")
                return None
            
            # Apply perspective transform
            pts1 = np.float32(points)
            width = int(np.linalg.norm(np.array(points[0]) - np.array(points[1])))
            height = int(np.linalg.norm(np.array(points[0]) - np.array(points[2])))
            pts2 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            rectified_image = cv2.warpPerspective(img_array, matrix, (width, height))
            
            # Convert to binary
            ret, binary_rectified_image = cv2.threshold(rectified_image, 128, 255, cv2.THRESH_BINARY)
            
            return binary_rectified_image
            
        except Exception as e:
            self.console.error(f"Error applying ROI: {str(e)}")
            return None
    
    def _apply_agc(self, data, gate_ms, dt_ms, desired_rms=1.0):
        """Apply AGC RMS to data."""
        try:
            gate_samples = max(1, int(round(gate_ms / dt_ms)))
            data_processed = data.copy()
            
            for i in range(data_processed.shape[1]):  # For each trace
                trace = data_processed[:, i]
                trace_power = trace ** 2
                smooth_power = uniform_filter1d(trace_power, size=gate_samples, mode='reflect')
                rms = np.sqrt(np.maximum(smooth_power, 1e-10))
                data_processed[:, i] = trace / rms * desired_rms
            
            return data_processed
            
        except Exception as e:
            self.console.error(f"Error applying AGC: {str(e)}")
            return data
    
    def _apply_trace_mixing(self, data, method, window_size, weights=None):
        """Apply trace mixing to data."""
        try:
            if method == 'weighted':
                return self._weighted_trace_mix(data, window_size, weights)
            elif method == 'median':
                return self._median_mix(data, window_size)
            else:
                self.console.error(f"Unknown mixing method: {method}")
                return data
                
        except Exception as e:
            self.console.error(f"Error applying trace mixing: {str(e)}")
            return data
    
    def _handle_boundaries(self, trace_idx, n_traces):
        """Handle boundary conditions with mirroring."""
        if trace_idx < 0:
            return -trace_idx
        elif trace_idx >= n_traces:
            return 2 * n_traces - trace_idx - 2
        return trace_idx
    
    def _weighted_trace_mix(self, data, window_size, weights=None):
        """Apply weighted average trace mixing."""
        result = data.copy()
        n_traces = data.shape[1]
        
        if weights is None or len(weights) != window_size:
            # Create symmetric weights
            weights = np.linspace(1, window_size // 2 + 1, window_size // 2 + 1)
            weights = np.concatenate([weights[:-1], weights[::-1]])
        
        weights = np.array(weights) / np.sum(weights)
        half_window = window_size // 2
        
        for i in range(n_traces):
            mixed_trace = np.zeros(data.shape[0])
            
            for j in range(window_size):
                trace_idx = self._handle_boundaries(i - half_window + j, n_traces)
                mixed_trace += data[:, trace_idx] * weights[j]
            
            result[:, i] = mixed_trace
        
        return result
    
    def _median_mix(self, data, window_size):
        """Apply median trace mixing."""
        result = data.copy()
        n_traces = data.shape[1]
        half_window = window_size // 2
        
        for i in range(n_traces):
            window_traces = np.zeros((window_size, data.shape[0]))
            
            for j in range(window_size):
                trace_idx = self._handle_boundaries(i - half_window + j, n_traces)
                window_traces[j] = data[:, trace_idx]
            
            result[:, i] = np.median(window_traces, axis=0)
        
        return result


class BatchvectorizationWindow(QMainWindow):
    """Main window for batch vectorization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SEGYRecover - Batch vectorization")
        self.setMinimumSize(900, 700)
        
        # State
        self.work_dir = None
        self.image_list = []
        self.processor = None
        
        self._setup_ui()
        self._load_default_directory()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("🔄 SEGYRecover - Batch vectorization")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Data directory selection
        dir_group = QGroupBox("Data Directory")
        dir_layout = QHBoxLayout(dir_group)
        
        self.dir_label = QLabel("No directory selected")
        dir_layout.addWidget(self.dir_label, 1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)
        
        layout.addWidget(dir_group)
        
        # Image selection table
        images_group = QGroupBox("Select Images to vectorize")
        images_layout = QVBoxLayout(images_group)
        
        self.images_table = QTableWidget()
        self.images_table.setColumnCount(6)
        self.images_table.setHorizontalHeaderLabels(["Select", "Image", ".par", ".roi", ".geom", ".flip"])
        self.images_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.images_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.images_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.images_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.images_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.images_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.images_table.setSelectionMode(QTableWidget.NoSelection)
        images_layout.addWidget(self.images_table)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All Valid")
        select_all_btn.clicked.connect(self._select_all_valid)
        actions_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear Selection")
        clear_btn.clicked.connect(self._clear_selection)
        actions_layout.addWidget(clear_btn)
        
        actions_layout.addStretch()
        images_layout.addLayout(actions_layout)
        
        layout.addWidget(images_group)
        
        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        
        # AGC option
        agc_layout = QHBoxLayout()
        self.agc_check = QCheckBox("Apply AGC")
        self.agc_check.setChecked(True)
        agc_layout.addWidget(self.agc_check)
        
        agc_layout.addWidget(QLabel("Window (ms):"))
        self.agc_window = QSpinBox()
        self.agc_window.setRange(10, 2000)
        self.agc_window.setSingleStep(50)
        self.agc_window.setValue(1000)
        self.agc_window.setEnabled(True)
        self.agc_check.toggled.connect(self.agc_window.setEnabled)
        agc_layout.addWidget(self.agc_window)
        
        agc_layout.addStretch()
        options_layout.addLayout(agc_layout)
        
        # Trace mixing option
        mixing_layout = QHBoxLayout()
        self.mixing_check = QCheckBox("Apply Trace Mixing")
        self.mixing_check.setChecked(True)
        mixing_layout.addWidget(self.mixing_check)
        
        mixing_layout.addWidget(QLabel("Method:"))
        self.mixing_method = QComboBox()
        self.mixing_method.addItem("Weighted Average", "weighted")
        self.mixing_method.addItem("Median", "median")
        self.mixing_method.setEnabled(True)
        mixing_layout.addWidget(self.mixing_method)
        
        mixing_layout.addWidget(QLabel("Window:"))
        self.mixing_window = QSpinBox()
        self.mixing_window.setRange(3, 21)
        self.mixing_window.setSingleStep(2)
        self.mixing_window.setValue(5)
        self.mixing_window.setEnabled(True)
        mixing_layout.addWidget(self.mixing_window)
        
        mixing_layout.addStretch()
        options_layout.addLayout(mixing_layout)

        # Mixing Weights
        weights_layout = QHBoxLayout()
        weights_layout.addWidget(QLabel("Mixing Weights:"))
        self.mixing_weights = QLineEdit("0.2, 0.3, 1, 0.3, 0.2")
        self.mixing_weights.setPlaceholderText("Comma-separated weights (e.g. 1, 2, 1)")
        self.mixing_weights.setEnabled(True)
        weights_layout.addWidget(self.mixing_weights)
        options_layout.addLayout(weights_layout)

        # Connect signals
        self.mixing_check.toggled.connect(self._update_mixing_ui)
        self.mixing_method.currentIndexChanged.connect(self._update_mixing_ui)
        self.mixing_window.valueChanged.connect(self._update_default_weights)
        
        # Suffix option (kept for compatibility but logic will change)
        suffix_layout = QHBoxLayout()
        self.suffix_check = QCheckBox("Save with suffix:")
        suffix_layout.addWidget(self.suffix_check)
        
        self.suffix_input = QLineEdit("_processed")
        self.suffix_input.setMaximumWidth(150)
        self.suffix_input.setEnabled(False)
        self.suffix_check.toggled.connect(self.suffix_input.setEnabled)
        suffix_layout.addWidget(self.suffix_input)
        
        suffix_layout.addStretch()
        options_layout.addLayout(suffix_layout)
        
        layout.addWidget(options_group)
        
        # Initial update
        self._update_mixing_ui()
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Batch Process")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_btn.clicked.connect(self._start_batch)
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.clicked.connect(self._stop_batch)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Initialize console handler
        self.console_output = ConsoleOutput()
        self.console_output.info("Application started. Please select a data directory.")
    
    def _load_default_directory(self):
        """Try to load the default data directory."""
        try:
            import appdirs
            user_data_dir = appdirs.user_data_dir("SEGYRecover")
            default_dir = os.path.join(user_data_dir, 'data')
            
            if os.path.exists(default_dir):
                self._set_directory(default_dir)
        except:
            pass
    
    def _browse_directory(self):
        """Browse for data directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Data Directory",
            self.work_dir or os.path.expanduser("~")
        )
        
        if directory:
            self._set_directory(directory)
    
    def _set_directory(self, directory):
        """Set the working directory and scan for images."""
        self.work_dir = directory
        self.dir_label.setText(directory)
        
        # Scan for images
        self._scan_images()
        
        self.console_output.section_header("DIRECTORY SELECTED")
        self.console_output.info(f"Data directory: {directory}")
    
    def _scan_images(self):
        """Scan IMAGES folder and validate required files."""
        self.image_list = []
        self.images_table.setRowCount(0)
        
        images_dir = os.path.join(self.work_dir, "IMAGES")
        
        if not os.path.exists(images_dir):
            self.console_output.error(f"IMAGES folder not found: {images_dir}")
            return
        
        # Find all image files
        image_files = []
        for ext in ['*.tif', '*.tiff', '*.jpg', '*.jpeg', '*.png']:
            image_files.extend(Path(images_dir).glob(ext))
        
        if not image_files:
            self.console_output.warning("No image files found in IMAGES folder")
            return
        
        self.console_output.section_header("SCANNING IMAGES")
        
        for img_path in sorted(image_files):
            base_name = img_path.stem
            
            # Check for required files
            par_path = os.path.join(self.work_dir, "PARAMETERS", f"{base_name}.par")
            roi_path = os.path.join(self.work_dir, "ROI", f"{base_name}.roi")
            geom_path = os.path.join(self.work_dir, "GEOMETRY", f"{base_name}.geometry")
            flip_path = os.path.join(self.work_dir, "FLIP", f"{base_name}.flip")
            
            has_par = os.path.exists(par_path)
            has_roi = os.path.exists(roi_path)
            has_geom = os.path.exists(geom_path)
            has_flip = os.path.exists(flip_path)
            
            is_valid = has_par and has_roi and has_geom and has_flip
            
            # Add to list
            self.image_list.append({
                'name': img_path.name,
                'path': str(img_path),
                'base_name': base_name,
                'has_par': has_par,
                'has_roi': has_roi,
                'has_geom': has_geom,
                'has_flip': has_flip,
                'is_valid': is_valid
            })
            
            # Add to table
            row = self.images_table.rowCount()
            self.images_table.insertRow(row)
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setEnabled(is_valid)
            self.images_table.setCellWidget(row, 0, checkbox)
            
            # Image name
            self.images_table.setItem(row, 1, QTableWidgetItem(img_path.name))
            
            # .par status
            par_status = "✓" if has_par else "✗"
            par_item = QTableWidgetItem(par_status)
            par_item.setTextAlignment(Qt.AlignCenter)
            if not has_par:
                par_item.setForeground(Qt.red)
            self.images_table.setItem(row, 2, par_item)
            
            # .roi status
            roi_status = "✓" if has_roi else "✗"
            roi_item = QTableWidgetItem(roi_status)
            roi_item.setTextAlignment(Qt.AlignCenter)
            if not has_roi:
                roi_item.setForeground(Qt.red)
            self.images_table.setItem(row, 3, roi_item)

            # .geom status
            geom_status = "✓" if has_geom else "✗"
            geom_item = QTableWidgetItem(geom_status)
            geom_item.setTextAlignment(Qt.AlignCenter)
            if not has_geom:
                geom_item.setForeground(Qt.red)
            self.images_table.setItem(row, 4, geom_item)

            # .flip status
            flip_status = "✓" if has_flip else "✗"
            flip_item = QTableWidgetItem(flip_status)
            flip_item.setTextAlignment(Qt.AlignCenter)
            if not has_flip:
                flip_item.setForeground(Qt.red)
            self.images_table.setItem(row, 5, flip_item)
            
            # Log status
            status = "✓ Valid" if is_valid else "✗ Missing files"
            if is_valid:
                self.console_output.success(f"{img_path.name}: {status}")
            else:
                missing = []
                if not has_par:
                    missing.append(".par")
                if not has_roi:
                    missing.append(".roi")
                if not has_geom:
                    missing.append(".geometry")
                if not has_flip:
                    missing.append(".flip")
                self.console_output.error(f"{img_path.name}: Missing {', '.join(missing)}")
        
        self.console_output.info(f"Found {len(self.image_list)} images, {sum(1 for i in self.image_list if i['is_valid'])} valid")
        
        # Enable start button if we have images
        self._update_start_button()
    
    def _select_all_valid(self):
        """Select all valid images."""
        for row in range(self.images_table.rowCount()):
            checkbox = self.images_table.cellWidget(row, 0)
            if checkbox and checkbox.isEnabled():
                checkbox.setChecked(True)
        self._update_start_button()
    
    def _clear_selection(self):
        """Clear all selections."""
        for row in range(self.images_table.rowCount()):
            checkbox = self.images_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
        self._update_start_button()
    
    def _update_start_button(self):
        """Update start button enabled state."""
        selected_count = self._get_selected_count()
        self.start_btn.setEnabled(selected_count > 0)
    
    def _get_selected_count(self):
        """Get number of selected images."""
        count = 0
        for row in range(self.images_table.rowCount()):
            checkbox = self.images_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                count += 1
        return count
    
    def _get_selected_images(self):
        """Get list of selected image info."""
        selected = []
        for row in range(self.images_table.rowCount()):
            checkbox = self.images_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected.append(self.image_list[row])
        return selected
    
    def _start_batch(self):
        """Start batch processing."""
        selected = self._get_selected_images()
        
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one image to process.")
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Start Batch Processing",
            f"Process {len(selected)} images?\n\nThis may take several minutes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Parse weights
        weights_str = self.mixing_weights.text()
        weights = None
        if self.mixing_check.isChecked() and self.mixing_method.currentData() == 'weighted':
            try:
                weights = [float(x.strip()) for x in weights_str.split(',') if x.strip()]
                if len(weights) != self.mixing_window.value():
                    QMessageBox.warning(self, "Invalid Weights", 
                        f"Number of weights ({len(weights)}) must match window size ({self.mixing_window.value()}).")
                    return
            except ValueError:
                QMessageBox.warning(self, "Invalid Weights", "Please enter valid numeric weights separated by commas.")
                return

        # Gather options
        options = {
            'apply_agc': self.agc_check.isChecked(),
            'agc_window': self.agc_window.value(),
            'apply_mixing': self.mixing_check.isChecked(),
            'mixing_method': self.mixing_method.currentData(),
            'mixing_window': self.mixing_window.value(),
            'mixing_weights': weights,
            'use_suffix': self.suffix_check.isChecked(),
            'suffix': self.suffix_input.text()
        }
        
        # Disable UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.images_table.setEnabled(False)
        
        # Start processing
        self.console_output.section_header("BATCH PROCESSING STARTED")
        self.console_output.info(f"Processing {len(selected)} images")
        
        if options['apply_agc']:
            self.console_output.info(f"AGC enabled: {options['agc_window']} ms window")
        
        if options['apply_mixing']:
            self.console_output.info(f"Trace mixing enabled: {options['mixing_method']}, window {options['mixing_window']}")
        
        # Start processor thread
        self.processor = BatchProcessor(selected, self.work_dir, self.console_output, options)
        self.processor.progress_update.connect(self._on_progress_update)
        self.processor.image_completed.connect(self._on_image_completed)
        self.processor.finished.connect(self._on_batch_finished)
        self.processor.start()
    
    def _stop_batch(self):
        """Stop batch processing."""
        if self.processor:
            reply = QMessageBox.question(
                self,
                "Stop Processing",
                "Are you sure you want to stop batch processing?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.processor.stop()
    
    def _on_progress_update(self, current, total, message):
        """Handle progress update."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} - {message}")
    
    def _on_image_completed(self, image_name, success, message):
        """Handle individual image completion."""
        # Update table with status icon
        for row in range(self.images_table.rowCount()):
            item = self.images_table.item(row, 1)
            if item and item.text() == image_name:
                status = "✓" if success else "✗"
                item.setText(f"{status} {image_name}")
                break
    
    def _on_batch_finished(self):
        """Handle batch completion."""
        # Re-enable UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.images_table.setEnabled(True)
        
        self.console_output.section_header("BATCH PROCESSING COMPLETE")
        
        # Show completion message
        QMessageBox.information(
            self,
            "Complete",
            "Batch processing completed!\n\nCheck the console log for details."
        )
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.processor and self.processor.isRunning():
            reply = QMessageBox.question(
                self,
                "Processing Active",
                "Batch processing is still running. Stop and close?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.processor.stop()
                self.processor.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    
    def _update_mixing_ui(self):
        """Update UI state for mixing options."""
        enabled = self.mixing_check.isChecked()
        self.mixing_method.setEnabled(enabled)
        self.mixing_window.setEnabled(enabled)
        
        is_weighted = self.mixing_method.currentData() == 'weighted'
        self.mixing_weights.setEnabled(enabled and is_weighted)

    def _update_default_weights(self):
        """Update default weights based on window size."""
        window = self.mixing_window.value()
        # Generate symmetric weights
        weights = []
        mid = window // 2
        for i in range(window):
            dist = abs(i - mid)
            weights.append(str(mid + 1 - dist))
        self.mixing_weights.setText(", ".join(weights))


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = BatchvectorizationWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
