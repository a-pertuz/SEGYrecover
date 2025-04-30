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
import matplotlib.pyplot as plt
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
        
        # Visualization state
        self.visualization_data = {
            'image_a': None,  # Original rectified image
            'image_f': None,  # Timeline detection 
            'image_g': None,  # Image with timelines removed
            'image_m': None,  # Baseline detection
            'raw_amplitude': None,
            'processed_amplitude': None,
            'resampled_amplitude': None,
            'filtered_data': None
        }
        
        # Create tabbed visualization system
        self.tab_canvases = {}
        self.tab_figures = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the tab's user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header = QLabel("Digitization Process")
        header.setObjectName("header_label")
        layout.addWidget(header)
        
        # Instruction text
        instruction = QLabel(
            "Start the digitization process to extract trace data from the seismic section. "
            "The process includes timeline removal, baseline detection, amplitude extraction, "
            "filtering, and SEGY file creation."
        )
        instruction.setObjectName("description_label")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
        
        # Process flow diagram
        process_flow = self._create_process_flow()
        process_flow.setObjectName("process_flow")
        layout.addWidget(process_flow)
        
        # Create visualization tabs container
        canvas_container = QGroupBox("Processing Visualization")
        canvas_container.setObjectName("processing_container")
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(15, 15, 15, 15)
        canvas_layout.setSpacing(10)
        
        # Create tab widget for visualizations
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("visualization_tabs")
        
        # Create tabs for different visualizations
        self._setup_visualization_tabs()
        
        # Add tabs to container
        canvas_layout.addWidget(self.tab_widget)
        
        # Add canvas container to main layout with 1 stretch factor
        layout.addWidget(canvas_container, 1)
        
        # Bottom button section
        button_container = QWidget()
        button_container.setObjectName("button_container")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(10, 5, 10, 5)
        button_layout.setSpacing(10)
        
        # Add spacer to push buttons to the right
        button_layout.addStretch()
        
        # Start button
        self.start_button = QPushButton("Start Digitization")
        self.start_button.setObjectName("start_digitization_button")
        self.start_button.setMinimumWidth(150)
        self.start_button.setFixedHeight(36)
        self.start_button.clicked.connect(self.start_digitization)
        button_layout.addWidget(self.start_button)
        
        # Add spacing between buttons
        button_layout.addSpacing(10)
        
        # Main next button with fixed width
        self.see_results_button = QPushButton("See Results")
        self.see_results_button.setObjectName("next_button")
        self.see_results_button.setMinimumWidth(100)
        self.see_results_button.setFixedHeight(36)
        self.see_results_button.setEnabled(False)
        self.see_results_button.clicked.connect(self.proceedRequested.emit)
        button_layout.addWidget(self.see_results_button)
        
        layout.addWidget(button_container)
    
    def _setup_visualization_tabs(self):
        """Set up the visualization tabs for different processing stages."""
        # Define the visualization tabs
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
                'id': 'baselines',
                'title': 'Baseline Detection',
                'description': 'Visualization of baseline detection (zoomed view)',
                'warning': 'This is a zoomed view showing detected baselines. Adjust BDB and BDE (detection range) or BFT if detection is poor.'
            },
            {
                'id': 'debug_baselines',
                'title': 'Full Baseline View',
                'description': 'Complete view of baselines on the processed image',
                'warning': 'Green lines show final baselines on the processed image. Check if baselines are properly placed.'
            },
            {
                'id': 'filtered_data',
                'title': 'Filtered Result',
                'description': 'Final filtered seismic data',
                'warning': 'If the filtered result has issues, adjust frequency filter parameters (F1-F4).'
            }
        ]
        
        # Create each tab with its visualization canvas
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
            # Use constrained_layout for filtered_data (which will have a colorbar)
            # Use tight_layout for other plots that won't have colorbar conflicts
            if config['id'] == 'filtered_data':
                fig = Figure(constrained_layout=True)
            else:
                fig = Figure(tight_layout=True)
                
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(300)
            
            # Create a simplified toolbar for this canvas
            toolbar = SimpleNavigationToolbar(canvas, self)
            
            # Store references to the figure and canvas
            self.tab_figures[config['id']] = fig
            self.tab_canvases[config['id']] = canvas
            
            # Add canvas and toolbar to the tab
            tab_layout.addWidget(canvas)
            tab_layout.addWidget(toolbar)
            
            # Add the tab to the tab widget
            self.tab_widget.addTab(tab_content, config['title'])
        
        # Initialize the first tab with the original image if available
        self._update_visualization_tab('original', self.visualization_data.get('image_a'))
    
    def _create_process_flow(self):
        """Create process flow widget."""
        # Container for the flow with centering
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 10, 0, 10)  # Add vertical padding
        
        # Create the flow widget
        flow_widget = QWidget()
        flow_widget.setObjectName("process_flow_widget")
        flow_layout = QHBoxLayout(flow_widget)
        flow_layout.setSpacing(10)  # Slightly increased spacing
        
        # Step widgets
        steps = [
            ("Timeline\nRemoval", False),
            ("Baseline\nDetection", False),
            ("Amplitude\nExtraction", False),
            ("Resampling &\nFiltering", False),
            ("SEGY\nCreation", False)
        ]
        
        # Create process flow steps
        self.step_widgets = []
        for i, (title, completed) in enumerate(steps):
            step_widget = self._create_step_widget(i+1, title, completed)
            flow_layout.addWidget(step_widget)
            self.step_widgets.append(step_widget)
            
            # Add arrow between steps
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setObjectName(f"step_arrow_{i+1}")
                arrow.setStyleSheet("color: #3182ce; font-size: 16pt; font-weight: bold;")
                flow_layout.addWidget(arrow)
        
        # Add the flow widget to the container with centering
        container_layout.addStretch(1)  # Left stretch for centering
        container_layout.addWidget(flow_widget)
        container_layout.addStretch(1)  # Right stretch for centering
        
        return container
    
    def _create_step_widget(self, number, title, completed=False):
        """Create a step widget for the process flow."""
        widget = QFrame()
        widget.setObjectName(f"step_widget_{number}")

        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 10, 8, 10)  # Increased vertical padding
        layout.setSpacing(10)  # Increased spacing between elements
        
        # Step title - now more prominent since we removed the step number
        title_label = QLabel(title)
        title_label.setObjectName(f"step_title_{number}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Add spacer to push status to bottom and create space
        layout.addStretch()
        
        # Status indicator
        status_label = QLabel("✓" if completed else "")
        status_label.setObjectName(f"step_status_{number}")
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        # Store reference to status label for updating later
        widget.status_label = status_label
        
        return widget
    
    def mark_step_completed(self, step_index):
        """Mark a step as completed in the process flow."""
        if 0 <= step_index < len(self.step_widgets):
            widget = self.step_widgets[step_index]
            widget.status_label.setText("✓")
            widget.status_label.setStyleSheet("color: #38a169; font-size: 16pt; font-weight: bold;")
    
    def mark_step_active(self, step_index):
        """Mark a step as active in the process flow."""
        if 0 <= step_index < len(self.step_widgets):
            widget = self.step_widgets[step_index]
            widget.status_label.setText("●")
            widget.status_label.setStyleSheet("color: #3182ce; font-size: 16pt; font-weight: bold;")
    
    def update_with_data(self, image_path, binary_rectified_image, parameters):
        """Update with data from previous tabs."""
        # Update the processor with data
        self.digitization_processor.set_data(image_path, binary_rectified_image, parameters)
        
        # Also store the original image for visualization
        self.visualization_data['image_a'] = binary_rectified_image
        
        if binary_rectified_image is not None:
            # Update the original image tab
            self._update_visualization_tab('original', binary_rectified_image)
            
            # Log that data was received
            info_message(self.console, "Rectified image loaded for digitization")
            info_message(self.console, f"Parameters loaded: {len(parameters)} parameters")
            # Enable the start button since we have valid data
            self.start_button.setEnabled(True)
        else:
            error_message(self.console, "No rectified image available")
            self.start_button.setEnabled(False)
        
        # Reset step status indicators
        for widget in self.step_widgets:
            widget.status_label.setText("")
            widget.status_label.setStyleSheet("")
        
        # Reset next button
        self.see_results_button.setEnabled(False)

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
                # Basic image visualization
                ax.imshow(data, cmap='gray')
                ax.set_title(f"{self.tab_widget.tabText(self.tab_widget.indexOf(self.tab_canvases[tab_id].parent().parent()))}")
                ax.axis('off')
            
            elif tab_id == 'baselines':
                # Zoomed view with baselines in red
                ax.imshow(data, cmap='gray')
                ax.set_title("Baseline Detection (Zoomed View)")
                
                # Display raw baselines if available
                if self.digitization_processor.final_baselines is not None:
                    for baseline in self.digitization_processor.final_baselines:
                        ax.axvline(x=baseline, color='red', linewidth=1)
                
                # Apply zoom for baseline detection
                self._apply_zoom_to_center(ax, data.shape)
            
            elif tab_id == 'debug_baselines':
                # Full view with green baselines
                if 'processed' in self.visualization_data and self.visualization_data['processed'] is not None:
                    ax.imshow(self.visualization_data['processed'], cmap='gray')
                else:
                    ax.imshow(data, cmap='gray')
                
                ax.set_title("Full Baseline View")
                
                if self.digitization_processor.final_baselines is not None:
                    for baseline in self.digitization_processor.final_baselines:
                        ax.axvline(x=baseline, color='lime', linewidth=1)
                    
                    # Add count information
                    ax.text(0.5, 0.02, f"Total detected baselines: {len(self.digitization_processor.final_baselines)}", 
                            transform=ax.transAxes, fontsize=10, ha='center', va='bottom',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='#d6e0eb', boxstyle='round,pad=0.3'))
                
                # Apply zoom for baseline detection
                self._apply_zoom_to_center(ax, data.shape)
            
            elif tab_id == 'filtered_data':
                im = ax.imshow(data, cmap='gray', aspect='auto', interpolation='none')
                
                ax.set_title("Filtered Seismic Data")
                ax.set_xlabel("Trace")
                ax.set_ylabel("Time (ms)")
                
                # Add time axis ticks for filtered data
                if self.digitization_processor.parameters:
                    time_ticks = np.linspace(0, data.shape[0]-1, 5)
                    time_labels = np.linspace(self.digitization_processor.parameters.get("TWT_P1", 0), 
                                            self.digitization_processor.parameters.get("TWT_P3", 1000), 5).astype(int)
                    ax.set_yticks(time_ticks)
                    ax.set_yticklabels(time_labels)
                
                fig.colorbar(im, ax=ax, label="Amplitude")
                # Don't call tight_layout for filtered_data tab - we're using constrained_layout instead
            else:
                # For other tabs without colorbars, we can use tight_layout
                fig.tight_layout()
                
            # Draw the updated figure
            self.tab_canvases[tab_id].draw()
            
            # If this is a new visualization, switch to its tab
            if tab_id not in ['original']:  # Don't switch on initial load
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) in [
                        "Timeline Detection" if tab_id == 'timelines' else
                        "Processed Image" if tab_id == 'processed' else
                        "Full Baseline View" if tab_id == 'debug_baselines' else
                        "Baseline Detection" if tab_id == 'baselines' else
                        "Filtered Result" if tab_id == 'filtered_data' else ""
                    ]:
                        self.tab_widget.setCurrentIndex(i)
                        break
    
    def _apply_zoom_to_center(self, ax, image_shape):
        """Apply zoom to focus on the center of the image."""
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
        # Validate inputs and prompt the user if needed
        if not self.digitization_processor.parameters or len(self.digitization_processor.parameters) == 0:
            QMessageBox.warning(self, "Warning", "Please set processing parameters first.")
            error_message(self.console, "Digitization attempted without parameters")
            return

        if self.digitization_processor.binary_rectified_image is None:
            QMessageBox.warning(self, "Warning", "Please load an image and select ROI first.")
            error_message(self.console, "Digitization attempted without rectified image")
            return
        
        # Disable start button to prevent multiple runs
        self.start_button.setEnabled(False)
        
        # Run the digitization process with step callbacks for UI updates
        success = self.digitization_processor.run_digitization(self._step_completed_callback)
        
        if success:
            # Add a success overlay on the filtered data tab
            self._add_success_overlay()
            
            # Enable next button to proceed to results
            self.see_results_button.setEnabled(True)
            
            # Emit signal with results
            self.digitizationCompleted.emit(
                self.digitization_processor.segy_path, 
                self.digitization_processor.filtered_data
            )
        
        # Re-enable start button for optional re-run
        self.start_button.setEnabled(True)
    
    def _step_completed_callback(self, step_index, step_results):
        """Callback for when a processing step is completed."""
        # Mark current step as active
        self.mark_step_active(step_index)
        
        # Update visualizations based on the step
        if step_index == 0:  # Timeline Removal
            self._update_visualization_tab('timelines', step_results.get('image_f'))
            self._update_visualization_tab('processed', step_results.get('image_g'))
        elif step_index == 1:  # Baseline Detection
            self._update_visualization_tab('debug_baselines', step_results.get('image_m'))
            self._update_visualization_tab('baselines', step_results.get('image_m'))
        elif step_index == 3:  # Data Processing
            self._update_visualization_tab('filtered_data', step_results.get('filtered_data'))
        
        # Mark step as completed
        self.mark_step_completed(step_index)
    
    def _add_success_overlay(self):
        """Add a success overlay to the filtered data tab."""
        if 'filtered_data' in self.tab_figures:
            fig = self.tab_figures['filtered_data']
            ax = fig.gca()
            
            # Add a text overlay with success message
            ax.text(0.5, 0.05, "SEGY created successfully!", 
                    ha='center', va='bottom', fontsize=14, fontweight='bold',
                    transform=ax.transAxes,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='#d1fae5', edgecolor='#10b981', alpha=0.8))
            
            # Draw the updated figure (no tight_layout call for filtered_data)
            self.tab_canvases['filtered_data'].draw()


