"""Parameters tab for SEGYRecover application."""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QLineEdit, QFormLayout, QFrame, QMessageBox,
    QScrollArea, QDialog, QApplication, QSizePolicy, QCheckBox, QGridLayout
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
        self.image_path = None
        self.param_widgets = {}  # Central registry of parameter widgets
        
        # Define all parameters with their metadata
        self.PARAMETERS = {
            # Point parameters
            "Trace_P1": {"group": "Points", "default": 0, "validator": QIntValidator()},
            "TWT_P1": {"group": "Points", "default": 0, "validator": QIntValidator()},
            "Trace_P2": {"group": "Points", "default": 0, "validator": QIntValidator()},
            "TWT_P2": {"group": "Points", "default": 0, "validator": QIntValidator()},
            "Trace_P3": {"group": "Points", "default": 0, "validator": QIntValidator()},
            "TWT_P3": {"group": "Points", "default": 0, "validator": QIntValidator()},
            
            # Acquisition parameters
            "DT": {"group": "Acquisition", "default": 4, "validator": QIntValidator(), 
                  "label": "Sample Rate (ms)", "tooltip": "Time interval between samples in milliseconds"},
            
            # Frequency parameters
            "F1": {"group": "Frequency", "default": 10, "validator": QIntValidator(), "tooltip": "Low cut-off"},
            "F2": {"group": "Frequency", "default": 12, "validator": QIntValidator(), "tooltip": "Low pass"},
            "F3": {"group": "Frequency", "default": 50, "validator": QIntValidator(), "tooltip": "High pass"},
            "F4": {"group": "Frequency", "default": 60, "validator": QIntValidator(), "tooltip": "High cut-off"},
            
            # Detection parameters
            "TLT": {"group": "Detection", "default": 1, "validator": QIntValidator(), 
                   "label": "Traceline Thickness", "tooltip": "Thickness of vertical trace lines"},
            "HLT": {"group": "Detection", "default": 5, "validator": QIntValidator(), 
                   "label": "Timeline Thickness", "tooltip": "Thickness of horizontal time lines"},
            "HE": {"group": "Detection", "default": 50, "validator": QIntValidator(), 
                  "label": "Horizontal Erode", "tooltip": "Erosion size for horizontal features"},
            "BDB": {"group": "Detection", "default": 20, "validator": QIntValidator(), 
                   "label": "Baseline Detection Beginning", "tooltip": "Start of baseline detection range (pixels from top)"},
            "BDE": {"group": "Detection", "default": 500, "validator": QIntValidator(), 
                   "label": "Baseline Detection End", "tooltip": "End of baseline detection range (pixels from top)"},
            "BFT": {"group": "Detection", "default": 80, "validator": QIntValidator(), 
                   "label": "Baseline Filter Threshold", "tooltip": "Threshold value (0-100) for baseline filtering"},
                   
            # TVBP parameters - explicitly define all interval fields
            "TVF_1_T1": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 1, "field": "T1"},
            "TVF_1_T2": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 1, "field": "T2"},
            "TVF_1_F1": {"group": "TVBP", "default": 10, "validator": QIntValidator(), "interval": 1, "field": "F1"},
            "TVF_1_F2": {"group": "TVBP", "default": 12, "validator": QIntValidator(), "interval": 1, "field": "F2"},
            "TVF_1_F3": {"group": "TVBP", "default": 50, "validator": QIntValidator(), "interval": 1, "field": "F3"},
            "TVF_1_F4": {"group": "TVBP", "default": 60, "validator": QIntValidator(), "interval": 1, "field": "F4"},
            
            "TVF_2_T1": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 2, "field": "T1"},
            "TVF_2_T2": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 2, "field": "T2"},
            "TVF_2_F1": {"group": "TVBP", "default": 10, "validator": QIntValidator(), "interval": 2, "field": "F1"},
            "TVF_2_F2": {"group": "TVBP", "default": 12, "validator": QIntValidator(), "interval": 2, "field": "F2"},
            "TVF_2_F3": {"group": "TVBP", "default": 50, "validator": QIntValidator(), "interval": 2, "field": "F3"},
            "TVF_2_F4": {"group": "TVBP", "default": 60, "validator": QIntValidator(), "interval": 2, "field": "F4"},
            
            "TVF_3_T1": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 3, "field": "T1"},
            "TVF_3_T2": {"group": "TVBP", "default": 0, "validator": QIntValidator(), "interval": 3, "field": "T2"},
            "TVF_3_F1": {"group": "TVBP", "default": 10, "validator": QIntValidator(), "interval": 3, "field": "F1"},
            "TVF_3_F2": {"group": "TVBP", "default": 12, "validator": QIntValidator(), "interval": 3, "field": "F2"},
            "TVF_3_F3": {"group": "TVBP", "default": 50, "validator": QIntValidator(), "interval": 3, "field": "F3"},
            "TVF_3_F4": {"group": "TVBP", "default": 60, "validator": QIntValidator(), "interval": 3, "field": "F4"}
        }
        
        # Define visual information for point inputs
        self.POINT_CONFIGS = [
            ("P1", "Top Left", (0, 0), "Top left corner coordinates"),
            ("P2", "Top Right", (1, 0), "Top right corner coordinates"), 
            ("P3", "Bottom Left", (0, 1), "Bottom left corner coordinates")
        ]
        
        # Define linked parameter relationships (target -> source)
        self.LINKED_PARAMS = {
            "Trace_P3": "Trace_P1",
            "TWT_P2": "TWT_P1",
            "TVF_1_T1": "TWT_P1",
            "TVF_2_T1": "TVF_1_T2",
            "TVF_3_T1": "TVF_2_T2",
            "TVF_3_T2": "TWT_P3"
        }
        
        # Store TVBP interval widgets
        self.tvf_intervals = []
        
        # Setup UI
        self._setup_ui()
        
    def _create_parameter_input(self, param_id, width=60):
        """Factory method to create parameter input with consistent styling."""
        param_info = self.PARAMETERS.get(param_id, {})
        
        input_field = QLineEdit(self)
        input_field.setFixedWidth(width)
        input_field.setValidator(param_info.get("validator", QIntValidator()))
        input_field.setAlignment(Qt.AlignCenter)
        input_field.setObjectName(f"input_{param_id}")
        input_field.setToolTip(param_info.get("tooltip", ""))
        
        # Register in central widget registry
        self.param_widgets[param_id] = input_field
        
        # Store as an attribute for backward compatibility
        setattr(self, param_id, input_field)
        
        return input_field
    
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
        main_layout.addWidget(scroll_area, 1)  
        
        # Button section with improved styling
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        
        # Add spacer to push buttons to the right
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save Parameters") 
        self.save_button.clicked.connect(self.save_parameters)
        button_layout.addWidget(self.save_button)
        
        self.next_button = QPushButton("Next") 
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.next_button)
        
        main_layout.addWidget(button_container)
        
        # Setup linked parameters after all widgets are created
        self._setup_linked_parameter_handlers()
    
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
            point_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            
            point_layout = QVBoxLayout(point_container)
            point_layout.setSpacing(5)
            
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
            
            # Create and add trace input field
            trace_param = f"Trace_{point_id}"
            trace_input = self._create_parameter_input(trace_param)
            
            trace_label = QLabel("Trace:", self)
            trace_label.setObjectName("input_label")
            trace_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            inputs_layout.addRow(trace_label, trace_input)
            
            # Create and add TWT input field
            twt_param = f"TWT_{point_id}"
            twt_input = self._create_parameter_input(twt_param)
            
            twt_label = QLabel("TWT (ms):", self)
            twt_label.setObjectName("input_label")
            twt_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            inputs_layout.addRow(twt_label, twt_input)
            
            horizontal_layout.addWidget(inputs_container)
            point_layout.addLayout(horizontal_layout)
            all_points_layout.addWidget(point_container)
        
        all_points_layout.addStretch()
        parent_layout.addLayout(all_points_layout)
    
    def _create_acquisition_params(self, parent_layout):
        """Create acquisition parameter inputs."""
        section_label = QLabel("Acquisition Parameters")
        section_label.setObjectName("section_label")
        parent_layout.addWidget(section_label)

        # --- Sample Rate QFrame ---
        sample_container = QFrame()
        sample_container.setObjectName("parameter_frame")
        sample_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sample_layout = QHBoxLayout(sample_container)
        sample_layout.setContentsMargins(10, 10, 10, 10)

        sample_label = QLabel("Sample Rate (ms):", self)
        sample_label.setObjectName("parameter_label")

        dt_input = self._create_parameter_input("DT")

        sample_description = QLabel("Time interval between samples in milliseconds", self)
        sample_description.setObjectName("parameter_description")
        sample_description.setWordWrap(True)

        sample_layout.addWidget(sample_label)
        sample_layout.addWidget(dt_input)
        sample_layout.addWidget(sample_description, 1)

        sample_wrapper_layout = QHBoxLayout()
        sample_wrapper_layout.addWidget(sample_container)
        sample_wrapper_layout.addStretch()
        parent_layout.addLayout(sample_wrapper_layout)

        # --- Frequency Band QFrame ---
        freq_container = QFrame()
        freq_container.setObjectName("parameter_frame")
        freq_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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
        freq_input_layout.setSpacing(5)

        freq_inputs_container = QHBoxLayout()
        for param_id in ["F1", "F2", "F3", "F4"]:
            param_container = QHBoxLayout()
            
            input_field = self._create_parameter_input(param_id, width=40)
            
            param_label = QLabel(param_id, self)
            param_label.setObjectName("freq_param_label")
            param_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            param_container.addWidget(param_label)
            param_container.addWidget(input_field)
            freq_inputs_container.addLayout(param_container)

        freq_input_layout.addLayout(freq_inputs_container)
        freq_diagram = self._create_freq_band_icon()
        freq_input_layout.addWidget(freq_diagram)
        freq_input_layout.addStretch(1)
        freq_layout.addLayout(freq_input_layout)
        
        # Add the frequency container to the parent layout
        parent_layout.addWidget(freq_container)

        # --- Time-Variant Bandpass Filter QFrame ---
        tvf_container = QFrame()
        tvf_container.setObjectName("parameter_frame")
        tvf_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        tvf_layout = QVBoxLayout(tvf_container)
        tvf_layout.setContentsMargins(10, 10, 10, 10)
        tvf_layout.setSpacing(10)

        self._create_time_variant_bandpass_ui(tvf_layout)
        
        parent_layout.addWidget(tvf_container)

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
        painter.drawText(60, 105, "Frequency")  
        painter.save()
        painter.translate(10, 60)
        painter.rotate(-90)
        painter.drawText(20, 0, "Amplitude")          
        painter.restore()
        
        # Draw filter shape
        painter.setPen(QPen(QColor(231, 76, 60), 2)) 
        painter.setBrush(QColor(231, 76, 60, 60))  
        
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
            painter.drawLine(x, 80, x, 75)  
            painter.drawText(x - 7, 90, label) 

        painter.end()
        icon.setPixmap(pixmap)
        icon.setFixedSize(140, 100)  
        return icon
    
    def _create_detection_params(self, parent_layout):
        """Create timeline/baseline detection parameter inputs."""
        section_label = QLabel("Detection Parameters")
        section_label.setObjectName("section_label")
        parent_layout.addWidget(section_label)
        
        # Create a single QFrame for all detection parameters
        detection_container = QFrame()
        detection_container.setObjectName("detection_params_frame")
        detection_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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
        detection_params = [param_id for param_id, info in self.PARAMETERS.items() 
                           if info.get("group") == "Detection"]
                           
        for param_id in detection_params:
            param_info = self.PARAMETERS[param_id]
            input_layout = QHBoxLayout()
            input_layout.setSpacing(10)
            
            # Create input field
            input_field = self._create_parameter_input(param_id)
            
            # Create help text
            help_text = QLabel(param_info.get("tooltip", ""), self)
            help_text.setObjectName("parameter_help")
            help_text.setWordWrap(True)
            
            input_layout.addWidget(input_field)
            input_layout.addWidget(help_text, 1)  # 1 = stretch factor
            
            # Add row to form layout
            param_label = QLabel(f"{param_info.get('label', param_id)}:", self)
            param_label.setObjectName("parameter_label")
            
            detection_layout.addRow(param_label, input_layout)
        
        parent_layout.addWidget(detection_container)
    
    def _create_time_variant_bandpass_ui(self, parent_layout):
        """Create the time-variant bandpass filter UI and logic."""
        # Create title and enable checkbox
        tvf_header = QLabel("Time-Variant Bandpass Filter:", self)
        tvf_header.setObjectName("parameter_label")
        parent_layout.addWidget(tvf_header)

        # Description
        tvf_description = QLabel(
            "Define different frequency filters for different time ranges of the seismic data",
            self
        )
        tvf_description.setObjectName("parameter_description")
        tvf_description.setWordWrap(True)
        parent_layout.addWidget(tvf_description)

        # Enable/disable checkbox
        tvf_hbox = QHBoxLayout()
        self.tvf_enable_checkbox = QCheckBox("Enable Time-Variant Bandpass", self)
        tvf_hbox.addWidget(self.tvf_enable_checkbox)
        tvf_hbox.addStretch()
        parent_layout.addLayout(tvf_hbox)

        # Create main container for intervals
        self.tvf_container = QFrame()
        self.tvf_container.setObjectName("tvf_container")
        self.tvf_grid = QGridLayout(self.tvf_container)
        self.tvf_grid.setContentsMargins(0, 10, 0, 0)
        self.tvf_grid.setHorizontalSpacing(8)
        self.tvf_grid.setVerticalSpacing(8)

        # Add header row with labels
        header_labels = ["Start (ms)", "End (ms)", "F1 (Hz)", "F2 (Hz)", "F3 (Hz)", "F4 (Hz)"]
        for col, label in enumerate(header_labels):
            header = QLabel(label, self)
            header.setAlignment(Qt.AlignCenter)
            header.setObjectName("tvf_header_label")
            self.tvf_grid.addWidget(header, 0, col)
        
        # Create all TVBP parameter fields upfront
        self.tvf_intervals = []
        for interval in range(1, 4):
            row = interval
            fields = []
            
            # Create all fields for this interval
            for col, field in enumerate(["T1", "T2", "F1", "F2", "F3", "F4"]):
                param_id = f"TVF_{interval}_{field}"
                input_field = self._create_parameter_input(param_id, width=60)
                self.tvf_grid.addWidget(input_field, row, col)
                fields.append(input_field)
            
            self.tvf_intervals.append(fields)

        parent_layout.addWidget(self.tvf_container)

        # Connect signals
        self.tvf_enable_checkbox.toggled.connect(self._on_tvf_enable_toggled)

        # Initially hide the container
        self.tvf_container.setVisible(False)

    def _on_tvf_enable_toggled(self, checked):
        """Handle enabling/disabling the time-variant bandpass filter."""
        # Simply show/hide the container - parameters always exist
        self.tvf_container.setVisible(checked)
        
    def _add_tvf_interval(self, values=None):
        """Add a new interval row. Optionally populate with values dict."""
        row = len(self.tvf_intervals) + 1  # +1 for header row
        fields = []
        
        # Create input fields consistently using the parameter factory
        # Though we don't register them immediately as they need special handling
        
        # Create Start time field (t1)
        t1 = QLineEdit(self)
        t1.setValidator(QIntValidator())
        t1.setAlignment(Qt.AlignCenter)
        t1.setFixedWidth(60)
        self.tvf_grid.addWidget(t1, row, 0)
        fields.append(t1)
        
        # Create End time field (t2)
        t2 = QLineEdit(self)
        t2.setValidator(QIntValidator())
        t2.setAlignment(Qt.AlignCenter)
        t2.setFixedWidth(60)
        self.tvf_grid.addWidget(t2, row, 1)
        fields.append(t2)
        
        # Create F1-F4 fields
        for i in range(4):
            f = QLineEdit(self)
            f.setValidator(QIntValidator())
            f.setAlignment(Qt.AlignCenter)
            f.setFixedWidth(60)
            self.tvf_grid.addWidget(f, row, i + 2)
            fields.append(f)
            
        self.tvf_intervals.append(fields)
        
        # Populate if values provided (for loading from file)
        if values:
            t1.setText(str(values.get("T1", "")))
            t2.setText(str(values.get("T2", "")))
            for i in range(4):
                fields[i+2].setText(str(values.get(f"F{i+1}", "")))
                
        return fields
        
    def _setup_linked_parameter_handlers(self):
        """Set up event handlers to synchronize linked parameter values."""
        # Connect signals for all linked parameters
        for target, source in self.LINKED_PARAMS.items():
            if source in self.param_widgets and target in self.param_widgets:
                source_widget = self.param_widgets[source]
                target_widget = self.param_widgets[target]
                
                # Create a function to update target value
                def make_updater(tw):
                    return lambda text: tw.setText(text)
                
                # Connect signal
                source_widget.textChanged.connect(make_updater(target_widget))
                
                # Set initial value and mark as read-only
                if source_widget.text():
                    target_widget.setText(source_widget.text())
                target_widget.setReadOnly(True)
                target_widget.setStyleSheet("background-color: #EFF6FF; border: 1px solid #3B82F6;")
                target_widget.setToolTip(f"Auto-filled from {source}")

    def _initialize_default_values(self):
        """Initialize all parameters with default values."""
        for param_id, param_info in self.PARAMETERS.items():
            if param_id in self.param_widgets:
                self.param_widgets[param_id].setText(str(param_info.get("default", "")))
    
    def _validate_parameters(self, param_values):
        """Validate parameter values and return a list of validation errors."""
        errors = []
        
        # Basic parameter validations
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
        
        # Check each validation
        for condition, message in validations:
            if not condition:
                errors.append(message)
                
        # TVBP-specific validations if enabled
        tvf_enabled = "TVF_ENABLED" in param_values and param_values["TVF_ENABLED"] == 1
        if tvf_enabled:
            # Get number of TVBP intervals
            interval_numbers = set()
            for key in param_values:
                if key.startswith("TVF_") and len(key.split("_")) >= 3:
                    interval_numbers.add(int(key.split("_")[1]))
            
            for i in sorted(interval_numbers):
                # Check for missing fields
                required_fields = [f"TVF_{i}_{field}" for field in ["T1", "T2", "F1", "F2", "F3", "F4"]]
                for field in required_fields:
                    if field not in param_values:
                        errors.append(f"Missing TVBP parameter: {field}")
                        
                # Skip further validations if fields are missing
                if any(field not in param_values for field in required_fields):
                    continue
                
                # Validate interval time range
                t1 = param_values[f"TVF_{i}_T1"]
                t2 = param_values[f"TVF_{i}_T2"]
                if t2 <= t1:
                    errors.append(f"TVBP interval {i}: End time must be > Start time")
                
                # Validate frequency order
                f_values = [param_values[f"TVF_{i}_F{j}"] for j in range(1, 5)]
                if not all(f_values[j] > f_values[j-1] for j in range(1, 4)) or f_values[0] <= 0:
                    errors.append(f"TVBP interval {i}: Frequencies must be in order F4 > F3 > F2 > F1 > 0")
        
        return errors

    def load_parameters(self, image_path=None):
        """Load parameters from file if available."""
        if image_path:
            self.image_path = image_path
            
        if not self.image_path:
            return
            
        # Setup paths
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        parameters_dir = os.path.join(self.work_dir, "PARAMETERS")
        parameters_path = os.path.join(parameters_dir, f"{base_name}.par")
        
        # Initialize with default values
        params = {}
        for param_id, param_info in self.PARAMETERS.items():
            params[param_id] = str(param_info.get("default", ""))
        
        tvf_enabled = False
        tvf_intervals = []
        
        # Try to load parameters from file
        if os.path.exists(parameters_path):
            try:
                with open(parameters_path, "r") as f:
                    file_params = dict(line.split('\t') for line in f if '\t' in line)
                    params.update({k: v.strip() for k, v in file_params.items()})
                
                # TVF support
                tvf_enabled = params.get("TVF_ENABLED", "0") == "1"
                if tvf_enabled:
                    # Find all TVF_* keys and group by interval index
                    tvf_keys = [k for k in params if k.startswith("TVF_")]
                    interval_indices = set();
                    for k in tvf_keys:
                        parts = k.split("_")
                        if len(parts) >= 3 and parts[1].isdigit():
                            interval_indices.add(int(parts[1]))
                    for idx in sorted(interval_indices):
                        interval = {}
                        for field in ["T1", "T2", "F1", "F2", "F3", "F4"]:
                            key = f"TVF_{idx}_{field}"
                            if key in params:
                                interval[field] = params[key]
                        tvf_intervals.append(interval)
                
                info_message(self.console, f"Loaded parameters from {parameters_path}")
            except Exception as e:
                error_message(self.console, f"Error loading parameters: {str(e)}")

        # Set dialog values for regular parameters
        for param_id, value in params.items():
            if param_id in self.param_widgets:
                self.param_widgets[param_id].setText(value)

        # Setup TVF UI
        has_tvf_params = tvf_enabled or any(k.startswith("TVF_") for k in params)
        
        # Block signals to prevent autofill during loading
        self.tvf_enable_checkbox.blockSignals(True)
        self.tvf_enable_checkbox.setChecked(has_tvf_params)
        self.tvf_enable_checkbox.blockSignals(False)
        
        # Set up TVF intervals if enabled
        if has_tvf_params:
            # Clear any existing intervals
            for field in self.tvf_intervals:
                for f in field:
                    self.tvf_grid.removeWidget(f)
                    f.deleteLater()
            self.tvf_intervals.clear()
            
            # Create exactly three intervals
            for i in range(3):
                interval = tvf_intervals[i] if i < len(tvf_intervals) else {}
                self._add_tvf_interval(interval)
                
            # Register TVF fields in parameter registry
            for i in range(3):
                interval_id = i + 1
                self.param_widgets[f"TVF_{interval_id}_T1"] = self.tvf_intervals[i][0]
                self.param_widgets[f"TVF_{interval_id}_T2"] = self.tvf_intervals[i][1]
                for j in range(4):
                    self.param_widgets[f"TVF_{interval_id}_F{j+1}"] = self.tvf_intervals[i][j+2]
            
            self.tvf_container.setVisible(True)
            self._setup_linked_parameter_handlers()

        self.next_button.setEnabled(False)
    
    def save_parameters(self):
        """Validate and save parameters to file."""
        if not self.image_path:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        # Setup paths
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        parameters_dir = os.path.join(self.work_dir, "PARAMETERS")
        parameters_path = os.path.join(parameters_dir, f"{base_name}.par")

        try:
            # Collect all parameter values
            param_values = {}
            
            # Get values from all registered parameter widgets
            for param_id, widget in self.param_widgets.items():
                try:
                    param_values[param_id] = int(widget.text()) if widget.text() else 0
                except ValueError:
                    raise ValueError(f"Invalid value for {param_id}")
            
            # Handle TVF enabled flag
            tvf_enabled = self.tvf_enable_checkbox.isChecked()
            if tvf_enabled:
                param_values["TVF_ENABLED"] = 1
            else:
                # If TVF is disabled, remove TVF parameters from output
                for param_id in list(param_values.keys()):
                    if param_id.startswith("TVF_"):
                        del param_values[param_id]

            # Validate all parameters
            errors = self._validate_parameters(param_values)
            if errors:
                raise ValueError("\n".join(errors))

            # Save parameters
            os.makedirs(parameters_dir, exist_ok=True)
            with open(parameters_path, "w") as f:
                for param, value in param_values.items():
                    f.write(f"{param}\t{value}\n")

            # Update our saved parameters
            self.parameters = param_values

            # Display in console with formatting
            self._display_parameters_in_console(base_name, param_values)

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
    
    def _display_parameters_in_console(self, base_name, param_values):
        """Display parameters in the console with nice formatting."""
        info_message(self.console, f"PARAMETERS FOR {base_name}")

        # Group parameters by category for better readability
        param_categories = {
            "Trace & Time Mapping": ["Trace_P1", "TWT_P1", "Trace_P2", "TWT_P2", "Trace_P3", "TWT_P3", "DT"],
            "Frequency Filter": ["F1", "F2", "F3", "F4"],
            "Detection Settings": ["TLT", "HLT", "HE", "BDB", "BDE", "BFT"]
        }

        for category, params in param_categories.items():
            self.console.insertHtml(f'<br><b>{category}:</b><br>')
            for param in params:
                if param in param_values:
                    value = param_values[param]
                    self.console.insertHtml(f'&nbsp;&nbsp;&bull; <b>{param}:</b> {value}<br>')

        # TVF output
        tvf_enabled = "TVF_ENABLED" in param_values and param_values["TVF_ENABLED"] == 1
        if tvf_enabled:
            self.console.insertHtml("<br><b>Time-Variant Bandpass Intervals:</b><br>")
            for idx in range(1, 4):
                if all(f"TVF_{idx}_{field}" in param_values for field in ["T1", "T2", "F1", "F2", "F3", "F4"]):
                    self.console.insertHtml(
                        f'&nbsp;&nbsp;&bull; <b>Interval {idx}:</b> '
                        f'{param_values[f"TVF_{idx}_T1"]}–{param_values[f"TVF_{idx}_T2"]} ms, '
                        f'F1={param_values[f"TVF_{idx}_F1"]}, '
                        f'F2={param_values[f"TVF_{idx}_F2"]}, '
                        f'F3={param_values[f"TVF_{idx}_F3"]}, '
                        f'F4={param_values[f"TVF_{idx}_F4"]}<br>'
                    )

        # Create the parameters path for the success message
        parameters_dir = os.path.join(self.work_dir, "PARAMETERS")
        parameters_path = os.path.join(parameters_dir, f"{base_name}.par")
        success_message(self.console, f"Parameters saved: {parameters_path}")
    
    def get_parameters(self):
        """Return all parameters as a dictionary."""
        params = {}
        
        # Get values from all registered parameter widgets
        for param_id, widget in self.param_widgets.items():
            try:
                params[param_id] = int(widget.text() or 0)
            except ValueError:
                params[param_id] = 0
        
        # Handle TVF enabled flag
        tvf_enabled = self.tvf_enable_checkbox.isChecked()
        if tvf_enabled:
            params["TVF_ENABLED"] = 1
        else:
            # If TVF is disabled, remove TVF parameters from output
            for param_id in list(params.keys()):
                if param_id.startswith("TVF_"):
                    del params[param_id]
        
        return params