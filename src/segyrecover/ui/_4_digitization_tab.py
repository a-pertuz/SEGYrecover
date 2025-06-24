"""Digitization tab for SEGYRecover application."""

import os
import numpy as np
import cv2
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPixmap, QPen, QPainter, QColor, QPolygonF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QSplitter, QProgressBar, QScrollArea, QFrame,
    QMessageBox, QDialog, QApplication, QTabWidget
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message
)
from ._4_1_digitization_logic import DigitizationProcessor

class SimpleNavigationToolbar(NavigationToolbar):
    """Simplified navigation toolbar with only Home, Pan and Zoom tools."""
    
    # Define which tools to keep
    toolitems = [t for t in NavigationToolbar.toolitems if t[0] in ('Home', 'Pan', 'Zoom', 'Save')]
    
    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class DigitizationTab(QWidget):
    """Tab for digitizing the seismic section."""
    
    # Signals
    digitizationCompleted = Signal(str, object)  # segy_path, filtered_data
    proceedRequested = Signal()
    
    def __init__(self, console, progress_bar, work_dir, parent=None):
        super().__init__(parent)
        self.setObjectName("digitization_tab")
        self.console = console
        self.progress = progress_bar
        self.work_dir = work_dir
        
        # Create the digitization processor for handling the logic
        self.digitization_processor = DigitizationProcessor(console, progress_bar, work_dir)
        
        # Visualization state for storing intermediate and final images/data
        self.visualization_data = {
            'image_a': None,  # Original rectified image
            'image_f': None,  # Timeline detection result
            'image_g': None,  # Image with timelines removed
            'image_m': None,  # Baseline detection result
            'raw_amplitude': None,
            'processed_amplitude': None,
            'resampled_amplitude': None,
            'filtered_data': None
        }
        
        # Create tabbed visualization system
        self.tab_canvases = {}
        self.tab_figures = {}
        
        self._setup_ui()
    
    def reset(self):
        """Reset the digitization tab state completely when starting a new line."""
        # Reset the processor
        self.digitization_processor.reset()
        
        # Clear all visualization data
        for key in self.visualization_data:
            self.visualization_data[key] = None
            
        # Reset UI elements for all tabs
        for tab_id in self.tab_figures:
            fig = self.tab_figures[tab_id]
            fig.clear()
            ax = fig.add_subplot(111)
            ax.set_title("No data available")
            ax.text(0.5, 0.5, "Load new data to begin", 
                    ha='center', va='center', fontsize=12, color='gray')
            ax.axis('off')
            self.tab_canvases[tab_id].draw()
            
        # Reset navigation and action buttons
        self.start_button.setEnabled(False)
        self.see_results_button.setEnabled(False)
        
        # Switch to the first tab
        self.tab_widget.setCurrentIndex(0)
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)
        
        # Header section
        header = QLabel("Digitization Process")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel("Start the digitization process to extract trace data from the seismic section.")
        instruction.setObjectName("description_label")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        
        # Create visualization tabs container
        canvas_container = QGroupBox("Processing Visualization")
        canvas_container.setObjectName("processing_container")
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(15, 15, 15, 15)
        canvas_layout.setSpacing(5)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("visualization_tabs")
        
        self._setup_visualization_tabs()
        
        canvas_layout.addWidget(self.tab_widget)
        
        layout.addWidget(canvas_container, 1)
        
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        # Add spacing between buttons for better layout
        button_layout.addSpacing(10)
        
        # Start button
        self.start_button = QPushButton("Start Digitization")
        self.start_button.setObjectName("start_digitization_button")
        self.start_button.clicked.connect(self.start_digitization)
        button_layout.addWidget(self.start_button)
        
        # Add spacing between buttons
        button_layout.addSpacing(10)
        
        # Main next button with fixed width
        self.see_results_button = QPushButton("See and Edit Results")
        self.see_results_button.setObjectName("next_button")
        self.see_results_button.setEnabled(False)
        self.see_results_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.see_results_button)
        
        layout.addWidget(button_container)
    
    def _setup_visualization_tabs(self):
        """Set up the visualization tabs for different processing stages."""
        tab_configs = [
            {
                'id': 'original',
                'title': 'Original Image',
                'description': 'The rectified input image before processing'
            },
            {
                'id': 'timelines',
                'title': 'Timeline Detection',
                'description': 'Detected timeline markings on the image',
                'warning': 'If timeline detection is incorrect, adjust the HE (Horizontal Erosion) or TLT (Timeline Line Thickness) parameter and try again.'
            },
            {
                'id': 'processed',
                'title': 'Processed Image',
                'description': 'Image after timeline removal'
            },
            {
                'id': 'debug_baselines',
                'title': 'Full Baseline View',
                'description': 'Zoomed view of baselines on the processed image',
                'warning': 'Red lines show final baselines on the processed image. Check if baselines are properly placed.'
            },
            {
                'id': 'filtered_data',
                'title': 'Filtered Result',
                'description': 'Final filtered seismic data',
                'warning': 'If the filtered result has issues, adjust frequency filter parameters (F1-F4).'
            }
        ]
        
        # Create each tab with its visualization canvas and toolbar
        for config in tab_configs:
            # Create the tab content widget
            tab_content = QWidget()
            tab_layout = QVBoxLayout(tab_content)
            tab_layout.setContentsMargins(5, 5, 5, 5)
            
            # Add customized warning label for each step if provided
            if 'warning' in config:
                warning_label = QLabel(f"⚠️ {config['warning']}")
                warning_label.setObjectName("warning_label")
                warning_label.setWordWrap(True)
                warning_label.setStyleSheet("color: #e53e3e; font-weight: bold; margin-bottom: 5px; padding: 5px;")
                tab_layout.addWidget(warning_label)
            
            # Add description label if provided
            if 'description' in config:
                desc_label = QLabel(config['description'])
                desc_label.setObjectName("tab_description")
                desc_label.setWordWrap(True)
                tab_layout.addWidget(desc_label)
            
            # Create a figure with appropriate layout strategy
            if config['id'] == 'filtered_data':
                fig = Figure(constrained_layout=True)
            else:
                fig = Figure(tight_layout=True)
                
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(300)
            
            toolbar = SimpleNavigationToolbar(canvas, self)
            
            self.tab_figures[config['id']] = fig
            self.tab_canvases[config['id']] = canvas
            
            tab_layout.addWidget(canvas)
            tab_layout.addWidget(toolbar)
            
            self.tab_widget.addTab(tab_content, config['title'])
        
        self._update_visualization_tab('original', self.visualization_data.get('image_a'))
    
    def _update_visualization_tab(self, tab_id, data):
        """Update the specified visualization tab with the given data."""
        if tab_id in self.tab_figures and data is not None:
            # Store the data in visualization state
            self.visualization_data[tab_id] = data
            
            fig = self.tab_figures[tab_id]
            fig.clear()
            ax = fig.add_subplot(111)
            
            # Different visualization methods based on tab type
            if tab_id in ['original', 'timelines', 'processed']:
                ax.imshow(data, cmap='gray')
                ax.set_title(f"{self.tab_widget.tabText(self.tab_widget.indexOf(self.tab_canvases[tab_id].parent().parent()))}")
                ax.axis('off')
            
            elif tab_id == 'debug_baselines':
                if 'processed' in self.visualization_data and self.visualization_data['processed'] is not None:
                    ax.imshow(self.visualization_data['processed'], cmap='gray')
                else:
                    ax.imshow(data, cmap='gray')
                
                ax.set_title("Baselines Detection")
                
                if self.digitization_processor.final_baselines is not None:
                    for baseline in self.digitization_processor.final_baselines:
                        ax.axvline(x=baseline, color='red', linewidth=1)
                
                self._apply_zoom_to_center(ax, data.shape)
            
            elif tab_id == 'filtered_data':
                vmin, vmax = np.percentile(data, [5, 95])
                im = ax.imshow(data, cmap='gray', aspect='auto', interpolation='none', vmin=vmin, vmax=vmax)
                
                ax.set_title("Filtered Seismic Data")
                ax.set_xlabel("Trace")
                ax.set_ylabel("Time (ms)")
                
                if self.digitization_processor.parameters:
                    time_ticks = np.linspace(0, data.shape[0]-1, 5)
                    time_labels = np.linspace(self.digitization_processor.parameters.get("TWT_P1", 0), 
                                            self.digitization_processor.parameters.get("TWT_P3", 1000), 5).astype(int)
                    ax.set_yticks(time_ticks)
                    ax.set_yticklabels(time_labels)
                
                fig.colorbar(im, ax=ax, label="Amplitude")
            else:
                fig.tight_layout()
                
            self.tab_canvases[tab_id].draw()
            
            # Switch to the relevant tab if not the original
            if tab_id not in ['original']:  
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) in [
                        "Timeline Detection" if tab_id == 'timelines' else
                        "Processed Image" if tab_id == 'processed' else
                        "Full Baseline View" if tab_id == 'debug_baselines' else
                        "Filtered Result" if tab_id == 'filtered_data' else ""
                    ]:
                        self.tab_widget.setCurrentIndex(i)
                        break
    
    def _apply_zoom_to_center(self, ax, image_shape):
        """Apply zoom to focus on the center of the image for baseline debug view."""
        height, width = image_shape
        
        # Zoom factor - smaller number means more zoom
        zoom_factor = 0.1  # Show 10% of the image
        
        # Calculate center point
        y_center = height // 2
        x_center = width // 2
        
        # Calculate zoom range
        y_half_range = int(height * zoom_factor / 2)
        x_half_range = int(width * zoom_factor / 2)
        
        # Set limits around the center
        y_min = max(0, y_center - y_half_range)
        y_max = min(height, y_center + y_half_range)
        x_min = max(0, x_center - x_half_range)
        x_max = min(width, x_center + x_half_range)
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_max, y_min)  # Reversed for image convention
    
    def start_digitization(self):
        """Start the digitization process."""
        # Validate that parameters and image are set before running
        if not self.digitization_processor.parameters or len(self.digitization_processor.parameters) == 0:
            QMessageBox.warning(self, "Warning", "Please set processing parameters first.")
            error_message(self.console, "Digitization aborted: No parameters set.")
            return

        if self.digitization_processor.binary_rectified_image is None:
            QMessageBox.warning(self, "Warning", "Please load an image and select ROI first.")
            error_message(self.console, "Digitization aborted: No rectified image.")
            return
        
        # Disable start button to prevent multiple runs
        self.start_button.setEnabled(False)
        
        # Run the digitization process with step callbacks for UI updates
        success = self.digitization_processor.run_digitization(self._step_completed_callback)
        
        if success:
            self._add_success_overlay()  # Show success message on filtered data tab
            self.see_results_button.setEnabled(True)  # Enable next button
            
            # Emit signal with results
            self.digitizationCompleted.emit(
                self.digitization_processor.segy_path, 
                self.digitization_processor.filtered_data
            )
          # Re-enable start button for optional re-run
        self.start_button.setEnabled(True)
    
    def _step_completed_callback(self, step_index, step_results):
        """Callback for when a processing step is completed. Updates visualizations."""
        # Update visualizations based on the step
        if step_index == 0:  # Timeline Removal
            self._update_visualization_tab('timelines', step_results.get('image_f'))
            self._update_visualization_tab('processed', step_results.get('image_g'))
        elif step_index == 1:  # Baseline Detection
            self._update_visualization_tab('debug_baselines', step_results.get('image_m'))
        elif step_index == 3:  # Data Processing
            self._update_visualization_tab('filtered_data', step_results.get('filtered_data'))
    
    def _add_success_overlay(self):
        """Add a success overlay to the filtered data tab after SEGY creation."""
        if 'filtered_data' in self.tab_figures:
            fig = self.tab_figures['filtered_data']
            ax = fig.gca()
            
            ax.text(0.5, 0.05, "SEGY created successfully!", 
                    ha='center', va='bottom', fontsize=14, fontweight='bold',
                    transform=ax.transAxes,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='#d1fae5', edgecolor='#10b981', alpha=0.8))
            
            self.tab_canvases['filtered_data'].draw()
    
    def update_with_data(self, image_path, binary_rectified_image, parameters):
        """Update with data from previous tabs and enable digitization if ready."""
        self.digitization_processor.set_data(image_path, binary_rectified_image, parameters)
        
        self.visualization_data['image_a'] = binary_rectified_image
        
        if binary_rectified_image is not None:
            self._update_visualization_tab('original', binary_rectified_image)
            
            info_message(self.console, "Rectified image loaded for digitization")
            info_message(self.console, f"Parameters loaded: {len(parameters)} parameters")
            self.start_button.setEnabled(True)
        else:
            error_message(self.console, "No rectified image available")
            self.start_button.setEnabled(False)
        
        self.see_results_button.setEnabled(False)



