"""Parameters tab for SEGYRecover application."""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QLineEdit, QFormLayout, QFrame, QMessageBox,
    QScrollArea, QDialog, QApplication, QSizePolicy
)
from PySide6.QtGui import QIntValidator, QFont, QPixmap, QPainter, QPen, QColor, QPolygonF
from PySide6.QtCore import QPointF

from ..utils.console_utils import section_header, error_message, success_message, info_message

class ParametersTab(QWidget):
    """Tab for configuring processing parameters."""
    
    # Signals
    parametersSet = Signal(dict)
    proceedRequested = Signal()
    
    def __init__(self, console, work_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("parameters_tab")
        self.console = console
        self.work_dir = work_dir
        self.parameters = {}
        self.image_path = None  # Store image path directly in this tab
        
        # Define constants 
        self.POINT_CONFIGS = [
            ("P1", "Top Left", (0, 0), "Top left corner coordinates"),
            ("P2", "Top Right", (1, 0), "Top right corner coordinates"), 
            ("P3", "Bottom Left", (0, 1), "Bottom left corner coordinates")
        ]
        
        self.FREQUENCY_PARAMS = [
            ("F1", "Low cut-off"), ("F2", "Low pass"),
            ("F3", "High pass"), ("F4", "High cut-off")
        ]

        self.DETECTION_PARAMS = [
            ("TLT", "Traceline Thickness", "Thickness of vertical trace lines"),
            ("HLT", "Timeline Thickness", "Thickness of horizontal time lines"),
            ("HE", "Horizontal Erode", "Erosion size for horizontal features"),
            ("BDB", "Baseline Detection Beginning", "Start of baseline detection range (pixels from top)"),
            ("BDE", "Baseline Detection End", "End of baseline detection range (pixels from top)"),
            ("BFT", "Baseline Filter Threshold", "Threshold value (0-100) for baseline filtering")
        ]
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header section
        header = QLabel("Processing Parameters")
        header.setObjectName("header_label")
        main_layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel(
            "Configure the parameters used for digitization. Parameters are automatically loaded "
            "if a matching .par file exists in the PARAMETERS folder. Click 'Save Parameters' before proceeding."
        )
        instruction.setWordWrap(True)
        instruction.setObjectName("description_label")
        main_layout.addWidget(instruction)
        
        # Create scroll area with better styling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create the parameters widget with improved spacing
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setSpacing(20)  # Increased spacing between sections
        params_layout.setContentsMargins(10, 10, 10, 20)  # More consistent margins
        
        # Point inputs
        self._create_point_inputs(params_layout)
        
        # Acquisition parameters
        self._create_acquisition_params(params_layout)
        
        # Detection parameters
        self._create_detection_params(params_layout)
        
        # Add spacer
        params_layout.addStretch()
        
        # Set the parameters widget as the scroll area's widget
        scroll_area.setWidget(params_widget)
        main_layout.addWidget(scroll_area, 1)  # 1 = stretch factor
        
        # Button section with improved styling
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        
        # Add spacer to push buttons to the right
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save Parameters")
        self.save_button.setMinimumWidth(150)  
        self.save_button.setFixedHeight(36)  
        self.save_button.clicked.connect(self.save_parameters)
        button_layout.addWidget(self.save_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.setMinimumWidth(100)  
        self.next_button.setFixedHeight(36) 
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.next_button)
        
        main_layout.addWidget(button_container)
    
    def _create_point_inputs(self, parent_layout):
        """Create point input fields."""
        # Add section header
        section_label = QLabel("Region of Interest Points")
        section_label.setObjectName("section_label")
        parent_layout.addWidget(section_label)
        
        # Add description
        desc_label = QLabel("Define the seismic section coordinates by specifying trace numbers and two-way time (TWT) values for each corner point:")
        desc_label.setWordWrap(True)
        desc_label.setObjectName("parameter_description")
        parent_layout.addWidget(desc_label)
        
        # Create a horizontal layout for all three points 
        all_points_layout = QHBoxLayout()
        all_points_layout.setSpacing(10)
        
        for point_id, label, dot_rel_pos, tooltip in self.POINT_CONFIGS:
            # Create a container for each point
            point_container = QFrame()
            point_container.setObjectName(f"point_frame")
            point_container.setToolTip(tooltip)
            point_container.setFrameShape(QFrame.StyledPanel)
            point_container.setFrameShadow(QFrame.Raised)
            
            point_layout = QVBoxLayout(point_container)
            point_layout.setSpacing(10)
            
            # Add point label at the top
            point_label = QLabel(label, self)
            point_label.setAlignment(Qt.AlignCenter)
            point_label.setObjectName("point_label")
            point_layout.addWidget(point_label)
            
            
            # Create a horizontal layout for the diagram and the form
            horizontal_layout = QHBoxLayout()
            horizontal_layout.setSpacing(10)
            
            # Create diagram
            icon = QLabel(self)
            pixmap = QPixmap(60, 40)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.setBrush(QColor(245, 245, 245))
            painter.drawRect(5, 5, 50, 30)
            
            corner_x = 5 if dot_rel_pos[0] == 0 else 55
            corner_y = 5 if dot_rel_pos[1] == 0 else 35
            painter.setPen(QPen(QColor(231, 76, 60), 1))
            painter.setBrush(QColor(231, 76, 60))
            painter.drawEllipse(corner_x - 3, corner_y - 3, 6, 6)
            painter.setPen(QColor(50, 50, 50))
            painter.drawText(corner_x + (5 if dot_rel_pos[0] == 0 else -12), corner_y + (12 if dot_rel_pos[1] == 0 else -5), point_id)
            painter.end()
            
            icon.setPixmap(pixmap)
            icon.setFixedSize(60, 40)
            icon.setAlignment(Qt.AlignCenter)
            horizontal_layout.addWidget(icon)
            
            # Create inputs container
            inputs_container = QWidget()
            inputs_layout = QFormLayout(inputs_container)
            inputs_layout.setContentsMargins(5, 5, 5, 5)
            inputs_layout.setHorizontalSpacing(10)  # Fixed separation between label and input
            
            # Add Trace label and input
            trace_input = QLineEdit(self)
            trace_input.setFixedWidth(60)
            trace_input.setValidator(QIntValidator())
            trace_input.setAlignment(Qt.AlignCenter)
            trace_input.setObjectName(f"trace_input_{point_id}")
            
            trace_label = QLabel("Trace:", self)
            trace_label.setObjectName("input_label")
            trace_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Center vertically with input
            
            inputs_layout.addRow(trace_label, trace_input)
            setattr(self, f"Trace_{point_id}", trace_input)
            
            # Add TWT label and input
            twt_input = QLineEdit(self)
            twt_input.setFixedWidth(60)
            twt_input.setValidator(QIntValidator())
            twt_input.setAlignment(Qt.AlignCenter)
            twt_input.setObjectName(f"twt_input_{point_id}")
            
            twt_label = QLabel("TWT (ms):", self)
            twt_label.setObjectName("input_label")
            twt_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Center vertically with input
            
            inputs_layout.addRow(twt_label, twt_input)
            setattr(self, f"TWT_{point_id}", twt_input)
            
            horizontal_layout.addWidget(inputs_container)
            
            # Add the horizontal layout to the point layout
            point_layout.addLayout(horizontal_layout)
            
            # Add the point container to the horizontal layout
            all_points_layout.addWidget(point_container)
        
        # Add the horizontal layout with all points to the main layout
        parent_layout.addLayout(all_points_layout)
    
    def _create_acquisition_params(self, parent_layout):
        """Create acquisition parameter inputs."""
        section_label = QLabel("Acquisition Parameters")
        section_label.setObjectName("section_label")
        parent_layout.addWidget(section_label)
        
        # Sample rate input with improved layout
        sample_container = QFrame()
        sample_container.setObjectName("parameter_frame")
        sample_layout = QHBoxLayout(sample_container)
        sample_layout.setContentsMargins(10, 10, 10, 10)
        
        sample_label = QLabel("Sample Rate (ms):", self)
        sample_label.setObjectName("parameter_label")
        
        self.DT = QLineEdit(self)
        self.DT.setFixedWidth(60)
        self.DT.setValidator(QIntValidator())
        self.DT.setAlignment(Qt.AlignCenter)
        self.DT.setObjectName("dt_input")
        
        sample_description = QLabel("Time interval between samples in milliseconds", self)
        sample_description.setObjectName("parameter_description")
        sample_description.setWordWrap(True)
        
        sample_layout.addWidget(sample_label)
        sample_layout.addWidget(self.DT)
        sample_layout.addWidget(sample_description, 1)  # 1 = stretch factor
        
        parent_layout.addWidget(sample_container)
        
        # Frequency band inputs with improved layout
        freq_container = QFrame()
        freq_container.setObjectName("parameter_frame")
        freq_layout = QVBoxLayout(freq_container)
        freq_layout.setContentsMargins(10, 10, 10, 10)
        freq_layout.setSpacing(10)
        
        freq_header = QLabel("Frequency Band (Hz):", self)
        freq_header.setObjectName("parameter_label")
        freq_layout.addWidget(freq_header)
        
        freq_description = QLabel("Define the frequency filter corners (F1-F4) for processing the seismic data", self)
        freq_description.setObjectName("parameter_description")
        freq_description.setWordWrap(True)
        freq_layout.addWidget(freq_description)
        
        # Frequency inputs and diagram in a horizontal layout
        freq_input_layout = QHBoxLayout()
        freq_input_layout.setSpacing(15)  # Reduced spacing between inputs
        
        # Create inputs for each frequency parameter
        freq_inputs_container = QHBoxLayout()
        
        for param_id, tooltip in self.FREQUENCY_PARAMS:
            param_container = QHBoxLayout()
            
            input_field = QLineEdit(self)
            input_field.setFixedWidth(50)
            input_field.setValidator(QIntValidator())
            input_field.setAlignment(Qt.AlignCenter)
            input_field.setToolTip(tooltip)
            input_field.setObjectName(f"freq_input_{param_id}")
            
            param_label = QLabel(param_id, self)
            param_label.setObjectName("freq_param_label")
            param_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            param_container.addWidget(param_label)
            param_container.addWidget(input_field)
            freq_inputs_container.addLayout(param_container)
            setattr(self, param_id, input_field)
        
        freq_input_layout.addLayout(freq_inputs_container)
        
        # Add frequency band diagram
        freq_diagram = self._create_freq_band_icon()
        freq_input_layout.addWidget(freq_diagram)
        freq_input_layout.addStretch(1)
        
        freq_layout.addLayout(freq_input_layout)
        parent_layout.addWidget(freq_container)
    
    def _create_freq_band_icon(self):
        """Create frequency band diagram."""
        icon = QLabel(self)
        pixmap = QPixmap(160, 120)  # Increased size for better spacing
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw axes
        painter.setPen(QPen(QColor(100, 100, 100), 1.5))
        painter.drawLine(20, 80, 120, 80)  # X-axis
        painter.drawLine(20, 20, 20, 60)  # Y-axis
        
        # Draw labels
        painter.setPen(QColor(80, 80, 80))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(60, 105, "Frequency")  # Adjusted position for frequency label
        painter.save()
        painter.translate(10, 60)
        painter.rotate(-90)
        painter.drawText(20, 0, "Amplitude")  # Fully visible amplitude label
        painter.restore()
        
        # Draw filter shape
        painter.setPen(QPen(QColor(231, 76, 60), 2))  # Red color
        painter.setBrush(QColor(231, 76, 60, 60))  # Semi-transparent red
        
        # Create frequency filter shape
        points = [
            QPointF(20, 80),     # Start at origin
            QPointF(30, 80),     # F1: Low cut-off (no amplitude)
            QPointF(50, 40),     # F2: Low pass (full amplitude)
            QPointF(90, 40),     # F3: High pass (full amplitude)
            QPointF(120, 80),    # F4: High cut-off (no amplitude)
            QPointF(20, 80)      # Back to origin
        ]
        
        painter.drawPolygon(QPolygonF(points))
        
        # Draw frequency markers
        markers = [
            (30, "F1"), (50, "F2"), (90, "F3"), (120, "F4")
        ]
        
        painter.setPen(QColor(231, 76, 60))
        for x, label in markers:
            painter.drawLine(x, 80, x, 75)  # Tick mark
            painter.drawText(x - 7, 90, label)  # Adjusted label position for better spacing
        
        painter.end()
        icon.setPixmap(pixmap)
        icon.setFixedSize(140, 100)  # Adjusted size to match new pixmap dimensions
        return icon
    
    def _create_detection_params(self, parent_layout):
        """Create timeline/baseline detection parameter inputs."""
        section_label = QLabel("Detection Parameters")
        section_label.setObjectName("section_label")
        parent_layout.addWidget(section_label)
        
        # Create a single QFrame for all detection parameters
        detection_container = QFrame()
        detection_container.setObjectName("detection_params_frame")
        detection_layout = QFormLayout(detection_container)
        detection_layout.setVerticalSpacing(12)
        detection_layout.setHorizontalSpacing(15)
        detection_layout.setContentsMargins(15, 15, 15, 15)
        
        # Add description
        detection_description = QLabel(
            "Configure parameters for detecting trace baselines and timelines in the seismic image.\n"
            "These parameters control how the digitization algorithm identifies and processes features in the image."
        )
        detection_description.setObjectName("parameter_description")
        detection_description.setWordWrap(True)
        parent_layout.addWidget(detection_description)
        
        # Add all detection parameters
        for param_id, label, tooltip in self.DETECTION_PARAMS:
            input_layout = QHBoxLayout()
            input_layout.setSpacing(10)
            
            # Create input field
            input_field = QLineEdit(self)
            input_field.setFixedWidth(60)
            input_field.setValidator(QIntValidator())
            input_field.setAlignment(Qt.AlignCenter)
            input_field.setToolTip(tooltip)
            input_field.setObjectName(f"detection_input_{param_id}")
            
            # Create help text
            help_text = QLabel(tooltip, self)
            help_text.setObjectName("parameter_help")
            help_text.setWordWrap(True)
            
            input_layout.addWidget(input_field)
            input_layout.addWidget(help_text, 1)  # 1 = stretch factor
            
            # Add row to form layout
            param_label = QLabel(f"{label}:", self)
            param_label.setObjectName("parameter_label")
            
            detection_layout.addRow(param_label, input_layout)
            setattr(self, param_id, input_field)
        
        parent_layout.addWidget(detection_container)
    
    def load_parameters(self, image_path=None):
        """Load parameters from file if available."""
        if image_path:
            # Store the image path in this tab
            self.image_path = image_path
            
        if not self.image_path:
            return
            
        # Setup paths
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        parameters_dir = os.path.join(self.work_dir, "PARAMETERS")
        parameters_path = os.path.join(parameters_dir, f"{base_name}.par")
        
        # Load existing parameters with defaults
        default_params = {
            "Trace_P1": "0", "TWT_P1": "0",
            "Trace_P2": "0", "TWT_P2": "0",
            "Trace_P3": "0", "TWT_P3": "0",
            "DT": "1", 
            "F1": "10", "F2": "12", "F3": "70", "F4": "80",
            "TLT": "1", "HLT": "5", "HE": "50", "BDB": "5", "BDE": "100", "BFT": "80"
        }

        params = default_params.copy()
        if os.path.exists(parameters_path):
            try:
                with open(parameters_path, "r") as f:
                    file_params = dict(line.split('\t') for line in f if '\t' in line)
                    params.update({k: v.strip() for k, v in file_params.items()})
                    
                info_message(self.console, f"Loaded parameters from {parameters_path}")
            except Exception as e:
                error_message(self.console, f"Error loading parameters: {str(e)}")

        # Set dialog values
        for param, value in params.items():
            if hasattr(self, param):
                getattr(self, param).setText(value)
        
        # Always ensure Next button is disabled when parameters are loaded
        # User must explicitly save parameters to proceed
        self.next_button.setEnabled(False)
    
    def save_parameters(self):
        """Validate and save parameters to file."""
        if not self.image_path:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        section_header(self.console, "PARAMETER CONFIGURATION")

        # Setup paths
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        parameters_dir = os.path.join(self.work_dir, "PARAMETERS")
        parameters_path = os.path.join(parameters_dir, f"{base_name}.par")

        try:
            # Get parameter values
            param_values = {}
            
            # Point coordinates
            for point in ["P1", "P2", "P3"]:
                for param in ["Trace", "TWT"]:
                    key = f"{param}_{point}"
                    param_values[key] = int(getattr(self, key).text())
            
            # Acquisition parameters
            param_values["DT"] = int(self.DT.text())
            for param_id, _ in self.FREQUENCY_PARAMS:
                param_values[param_id] = int(getattr(self, param_id).text())
                
            # Detection parameters
            for param_id, _, _ in self.DETECTION_PARAMS:
                param_values[param_id] = int(getattr(self, param_id).text())
            
            # Validate parameter relationships
            validations = [
                (param_values["DT"] > 0, "Sample rate must be > 0"),
                (param_values["F4"] > param_values["F3"], "F4 must be > F3"),
                (param_values["F3"] > param_values["F2"], "F3 must be > F2"),
                (param_values["F2"] > param_values["F1"], "F2 must be > F1"),
                (param_values["F1"] > 0, "F1 must be > 0"),
                (param_values["TWT_P3"] > param_values["TWT_P1"], "TWT_P3 must be > TWT_P1"),
                (param_values["BDB"] < param_values["BDE"], "BDB must be < BDE"),
                (param_values["BDB"] >= 0, "BDB must be >= 0"),
                (param_values["BFT"] >= 0 and param_values["BFT"] <= 100, "BFT must be between 0 and 100"),
                (param_values["TLT"] > 0, "Timeline thickness must be > 0"),
                (param_values["HLT"] > 0, "Horizontal line thickness must be > 0"),
                (param_values["HE"] > 0, "Horizontal erosion must be > 0"),
                (param_values["Trace_P1"] >= 0, "Trace_P1 must be >= 0"),
                (param_values["Trace_P2"] >= 0, "Trace_P2 must be >= 0"),
                (param_values["Trace_P3"] >= 0, "Trace_P3 must be >= 0")
            ]

            for condition, message in validations:
                if not condition:
                    raise ValueError(message)

            # Save parameters
            os.makedirs(parameters_dir, exist_ok=True)
            with open(parameters_path, "w") as f:
                for param, value in param_values.items():
                    f.write(f"{param}\t{value}\n")

            # Update our saved parameters
            self.parameters = param_values

            # Update console output with formatting
            section_header(self.console, f"PARAMETERS FOR {base_name}")
            
            # Group parameters by category for better readability
            param_categories = {
                "Trace & Time Mapping": ["Trace_P1", "TWT_P1", "Trace_P2", "TWT_P2", "Trace_P3", "TWT_P3", "DT"],
                "Frequency Filter": ["F1", "F2", "F3", "F4"],
                "Detection Settings": ["TLT", "HLT", "HE", "BDB", "BDE", "BFT"]
            }
            
            for category, params in param_categories.items():
                self.console.append(f"\n• {category}:")
                for param in params:
                    if param in param_values:
                        value = param_values[param]
                        self.console.append(f"  - {param}: {value}")
            
            self.console.append(f"\n")
            success_message(self.console, f"Parameters saved: {parameters_path}")

            # Emit signal with parameters
            self.parametersSet.emit(param_values)
            
            # Enable next button
            self.next_button.setEnabled(True)
            
            QMessageBox.information(self, "Parameters Set",
                "<p><b>Parameters saved successfully.</b></p>")

        except ValueError as e:
            error_message(self.console, str(e))
            QMessageBox.critical(self, "Invalid Parameters", str(e))
        except Exception as e:
            error_message(self.console, f"Error processing parameters: {str(e)}")
            QMessageBox.critical(self, "Error", 
                f"Failed to process parameters: {str(e)}")
    
    def get_parameters(self):
        """Return all parameters as a dictionary."""
        params = {}
        
        # Get point parameters
        for point in ["P1", "P2", "P3"]:
            for param in ["Trace", "TWT"]:
                key = f"{param}_{point}"
                params[key] = int(getattr(self, key).text())
        
        # Get acquisition parameters
        params["DT"] = int(self.DT.text())
        for param_id, _ in self.FREQUENCY_PARAMS:
            params[param_id] = int(getattr(self, param_id).text())
            
        # Get detection parameters
        for param_id, _, _ in self.DETECTION_PARAMS:
            params[param_id] = int(getattr(self, param_id).text())
            
        return params
