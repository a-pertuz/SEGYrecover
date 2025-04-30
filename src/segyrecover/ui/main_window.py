"""Main window for SEGYRecover application."""
import matplotlib
matplotlib.use('QtAgg')
import os
import json
import subprocess
from PySide6.QtGui import QFont, QAction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QStatusBar, QProgressBar, QVBoxLayout, QLabel, 
    QPushButton, QMessageBox, QWidget, QTextEdit, QStyle, QDialog, 
    QFileDialog, QMainWindow, QSplitter, QHBoxLayout
)

import appdirs

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from .help_dialogs import HelpDialog, FirstRunDialog, AboutDialog
from ..utils.resource_utils import copy_tutorial_files
from ..utils.console_utils import (
    section_header, info_message, initialize_log_file, close_log_file, error_message
)

# Imports for the tabbed interface
from .navigation_panel import NavigationPanel
from .tab_container import TabContainer
from ._0_welcome_tab import WelcomeTab
from ._1_load_image_tab import LoadImageTab
from ._2_parameters_tab import ParametersTab
from ._3_roi_selection_tab import ROISelectionTab
from ._4_digitization_tab import DigitizationTab
from ._5_results_tab import ResultsTab

class ProgressStatusBar(QStatusBar):
    """Status bar with integrated progress bar."""

    def __init__(self, parent=None):
        """Initialize the progress status bar.""" 
        super().__init__(parent)
        self.setObjectName("status_bar")
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(200)
        
        # Create cancel button
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel)
        
        # Add widgets to status bar
        self.addPermanentWidget(self.progress_bar)
        self.addPermanentWidget(self.cancel_button)
        
        self._canceled = False
        
    def start(self, title, maximum):
        self._canceled = False
        self.showMessage(title)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        QApplication.processEvents()
        
    def update(self, value, message=None):
        if message:
            self.showMessage(message)
        self.progress_bar.setValue(value)
        QApplication.processEvents()
        
    def finish(self):
        self.clearMessage()
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
    
    def wasCanceled(self):
        """Check if the operation was canceled."""
        return self._canceled
    
    def cancel(self):
        """Cancel the current operation."""
        self._canceled = True

class SegyRecover(QMainWindow):
    """Main application widget for SEGYRecover."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("main_window")
        
        # Make window dimensions consistent with bigger size for the tabbed UI
        self.setMinimumSize(1200, 800)
        
        # Get appropriate directories for user data and config
        self.app_name = "SEGYRecover"
        self.user_data_dir = appdirs.user_data_dir(self.app_name)
        self.user_config_dir = appdirs.user_config_dir(self.app_name)
        
        # Ensure config directory exists
        os.makedirs(self.user_config_dir, exist_ok=True)
        self.config_path = os.path.join(self.user_config_dir, 'config.json')
        
        self.load_config()
        
        # Initialize state variables
        self.image_path = None
        self.img_array = None
        self.points = []
        self.rectified_image = None
        self.binary_rectified_image = None
        self.parameters = {}
        self.image_canvas = None  # Initialize this here for the initialize call below
        
        self.create_required_folders()

        # Initialize the central widget with a horizontal layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_menu_bar()
        
        # Create navigation panel and add to main layout
        self.navigation_panel = NavigationPanel()
        self.navigation_panel.setObjectName("navigation_panel")
        self.navigation_panel.navigationChanged.connect(self.handle_navigation_change)
        main_layout.addWidget(self.navigation_panel)
        
        # Create container for main content (tabs + console)
        content_container = QWidget()
        content_container.setObjectName("content_container")
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(0)
        
        # Create tab container
        self.tab_container = TabContainer()
        self.tab_container.setObjectName("tab_container")
        content_layout.addWidget(self.tab_container, 1)  # 1 = stretch factor
        
        # Create and add console
        self.console = QTextEdit()
        self.console.setObjectName("console")  
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.WidgetWidth) 
        content_layout.addWidget(self.console)
        
        # Add content container to main layout
        main_layout.addWidget(content_container, 1)  # 1 = stretch factor
        
        # Create the progress bar as the main window's status bar
        self.progress = ProgressStatusBar()
        self.setStatusBar(self.progress)
        
        # Initialize log file
        self.log_file_path = initialize_log_file(self.work_dir)
        if self.log_file_path:
            info_message(self.console, f"Log file created: {os.path.basename(self.log_file_path)}")
        

        
        # Create matplotlib figure for the image canvas
        figure = plt.figure()
        self.image_canvas = FigureCanvas(figure)
        

        
        # Initialize tabs
        self.initialize_tabs()
        
        # Show current directory in console with improved formatting
        section_header(self.console, "INITIALIZATION")
        info_message(self.console, f"Data directory: {self.work_dir}")
        info_message(self.console, "Application ready")
        
        # Initialize with the welcome tab
        self.navigation_panel.set_active("welcome")
        self.tab_container.switch_to("welcome")
        
        # Disable tabs that require prior steps
        self.navigation_panel.enable_tabs_until("welcome")
    
    def handle_navigation_change(self, identifier):
        """Handle navigation changes from the side panel."""
        self.tab_container.switch_to(identifier)
    
    def initialize_tabs(self):
        """Initialize all the tab content."""
        # Welcome tab
        welcome_tab = WelcomeTab()
        welcome_tab.newLineRequested.connect(self.start_new_line)
        self.tab_container.add_tab("welcome", welcome_tab)
        
        # Load Image tab
        load_image_tab = LoadImageTab(self.console, self.work_dir)
        load_image_tab.imageLoaded.connect(self.handle_image_loaded)
        load_image_tab.proceedRequested.connect(lambda: self.proceed_to_tab("parameters"))
        self.tab_container.add_tab("load_image", load_image_tab)
        
        # Parameters tab
        parameters_tab = ParametersTab(self.console, self.work_dir)
        parameters_tab.parametersSet.connect(self.handle_parameters_set)
        parameters_tab.proceedRequested.connect(lambda: self.proceed_to_tab("roi_selection"))
        self.tab_container.add_tab("parameters", parameters_tab)
        
        # ROI Selection tab
        roi_selection_tab = ROISelectionTab(self.console, self.work_dir)
        roi_selection_tab.roiSelected.connect(self.handle_roi_selected)
        roi_selection_tab.proceedRequested.connect(lambda: self.proceed_to_tab("digitization"))
        self.tab_container.add_tab("roi_selection", roi_selection_tab)
        
        # Digitization tab
        digitization_tab = DigitizationTab(self.console, self.progress, self.work_dir)
        digitization_tab.digitizationCompleted.connect(self.handle_digitization_completed)
        digitization_tab.proceedRequested.connect(lambda: self.proceed_to_tab("results"))
        self.tab_container.add_tab("digitization", digitization_tab)
        
        # Results tab
        results_tab = ResultsTab(self.console, self.work_dir)
        results_tab.newLineRequested.connect(self.start_new_line)
        self.tab_container.add_tab("results", results_tab)
    
    def start_new_line(self):
        """Start a new seismic line processing workflow."""
        # Reset state
        self.image_path = None
        self.img_array = None
        self.points = []
        self.rectified_image = None
        self.binary_rectified_image = None
        self.parameters = {}
        
        # Get the LoadImageTab and explicitly reset it
        load_image_tab = self.tab_container.widget(self.tab_container.tab_indices["load_image"])
        if hasattr(load_image_tab, "reset"):
            load_image_tab.reset()
        
        # Switch to load image tab and enable only this step
        self.proceed_to_tab("load_image")
        self.navigation_panel.enable_tabs_until("load_image")
        
        # Clear console
        self.console.clear()
        section_header(self.console, "NEW LINE STARTED")
        info_message(self.console, "Please load a seismic image")
    
    def proceed_to_tab(self, tab_id):
        """Switch to specified tab and update navigation."""
        self.tab_container.switch_to(tab_id)
        self.navigation_panel.set_active(tab_id)
        
        # Special handling for specific tabs
        if tab_id == "parameters" and self.image_path:
            # Auto-load parameters if an image is loaded
            params_tab = self.tab_container.widget(self.tab_container.tab_indices["parameters"])
            if hasattr(params_tab, "load_parameters"):
                params_tab.load_parameters(self.image_path)
                # Next button should be disabled until parameters are saved
        
        elif tab_id == "roi_selection" and self.image_path is not None and self.img_array is not None:
            # Update ROI tab with image data
            roi_tab = self.tab_container.widget(self.tab_container.tab_indices["roi_selection"])
            if hasattr(roi_tab, "update_with_image"):
                roi_tab.update_with_image(self.image_path, self.img_array)
        
        elif tab_id == "digitization" and self.binary_rectified_image is not None and self.parameters:
            # Update digitization tab with necessary data
            digitization_tab = self.tab_container.widget(self.tab_container.tab_indices["digitization"])
            if hasattr(digitization_tab, "update_with_data"):
                digitization_tab.update_with_data(
                    self.image_path,
                    self.binary_rectified_image,
                    self.parameters
                )
    
    def handle_image_loaded(self, image_path, img_array):
        """Handle image loaded signal from LoadImageTab."""
        self.image_path = image_path
        self.img_array = img_array
        
        # Enable navigation to next step
        self.navigation_panel.enable_tabs_until("parameters")
    
    def handle_parameters_set(self, parameters):
        """Handle parameters set signal from ParametersTab."""
        self.parameters = parameters
        
        # Debug output to help diagnose issues
        info_message(self.console, f"Parameters set: {len(parameters)} parameters")
        
        # Enable navigation to next step
        self.navigation_panel.enable_tabs_until("roi_selection")
    
    def handle_roi_selected(self, points, binary_rectified_image=None):
        """Handle ROI selected signal from ROISelectionTab."""
        self.points = points
        
        # Get the ROI tab to access rectified image
        roi_tab = self.tab_container.widget(self.tab_container.tab_indices["roi_selection"])
        
        # Use the binary_rectified_image directly from the signal if provided
        if binary_rectified_image is not None:
            self.binary_rectified_image = binary_rectified_image
            info_message(self.console, "Received binary rectified image directly from ROI selection")
        # Fall back to the tab property if signal parameter isn't available
        elif hasattr(roi_tab, "binary_rectified_image") and roi_tab.binary_rectified_image is not None:
            self.binary_rectified_image = roi_tab.binary_rectified_image
            info_message(self.console, "Retrieved binary rectified image from ROI tab")
        else:
            error_message(self.console, "Binary rectified image is not available")
            return
            
        # Get the rectified image (not binary) if available
        if hasattr(roi_tab, "rectified_image"):
            self.rectified_image = roi_tab.rectified_image
        
        # Output debug information to console
        info_message(self.console, f"ROI selected: {len(points)} points")
        if self.binary_rectified_image is not None:
            binary_shape = self.binary_rectified_image.shape
            info_message(self.console, f"Binary rectified image shape: {binary_shape[1]}x{binary_shape[0]} pixels")
        
        # Enable navigation to next step
        self.navigation_panel.enable_tabs_until("digitization")
    
    def handle_digitization_completed(self, segy_path, filtered_data):
        """Handle digitization completed signal from DigitizationTab."""
        # Enable navigation to next step
        self.navigation_panel.enable_tabs_until("results")
        
        # Update results tab with data
        results_tab = self.tab_container.widget(self.tab_container.tab_indices["results"])
        if hasattr(results_tab, "display_results"):
            results_tab.display_results(segy_path, filtered_data, self.parameters["DT"])
    
    def create_menu_bar(self):
        """Create the menu bar with file and help menus."""
        menu_bar = self.menuBar()
        menu_bar.setObjectName("menu_bar")
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Set directory action
        set_dir_action = QAction("Set Data Directory", self)
        set_dir_action.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        set_dir_action.setShortcut("Ctrl+D")
        set_dir_action.triggered.connect(self.set_base_directory)
        file_menu.addAction(set_dir_action)
        
        # Open directory action
        open_dir_action = QAction("Open Data Directory", self)
        open_dir_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        open_dir_action.setShortcut("Ctrl+O")
        open_dir_action.triggered.connect(self.open_work_directory)
        file_menu.addAction(open_dir_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # How To action
        how_to_action = QAction("HOW TO", self)
        how_to_action.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        how_to_action.setShortcut("F1")
        how_to_action.triggered.connect(self.how_to)
        help_menu.addAction(how_to_action)

        help_menu.addSeparator()
        about_action = QAction("About", self)
        about_action.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def open_work_directory(self):
        """Open the current work directory in the file explorer."""
        try:
            if os.path.exists(self.work_dir):
                if os.name == 'nt':  # Windows
                    os.startfile(self.work_dir)
                elif os.name == 'posix':  # macOS and Linux
                    if os.uname().sysname == 'Darwin':  # macOS
                        subprocess.run(['open', self.work_dir])
                    else:  # Linux
                        subprocess.run(['xdg-open', self.work_dir])
                info_message(self.console, f"Opened data directory: {self.work_dir}")
            else:
                QMessageBox.warning(self, "Directory Not Found", 
                                   f"The directory {self.work_dir} does not exist.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open directory: {str(e)}")
            info_message(self.console, f"Error opening directory: {str(e)}")

    def load_config(self):
        """Load configuration from file or create default."""
        # Default location from appdirs
        default_base_dir = os.path.join(self.user_data_dir, 'data')
        
        # Check if this is first run (config file doesn't exist)
        is_first_run = not os.path.exists(self.config_path)
        
        if is_first_run:
            # Show first run dialog
            dialog = FirstRunDialog(self, default_base_dir)
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                base_dir = dialog.get_selected_location()
            else:
                # Use default if dialog was canceled
                base_dir = default_base_dir
                
            # Create a new config file
            config = {'base_dir': base_dir}
        else:
            # Load existing config
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    base_dir = config.get('base_dir', default_base_dir)
            except Exception as e:
                base_dir = default_base_dir
                config = {'base_dir': base_dir}
                print(f"Error loading config: {e}")
            
        # Set work_dir to base_dir
        self.base_dir = base_dir
        self.work_dir = base_dir
        
        # Create base directory if it doesn't exist
        os.makedirs(self.base_dir, exist_ok=True)
        
        self.create_required_folders()
        
        # Copy example files from the installed package to the user's data directory on first run
        if is_first_run:
            try:
                copy_tutorial_files(self.base_dir)
                print(f"Example files copied to: {self.base_dir}")
            except Exception as e:
                print(f"Error copying example files: {e}")
        
        # Save config to ensure it's created even on first run
        self.save_config()

    def save_config(self):
        """Save configuration to file."""
        config = {
            'base_dir': self.base_dir
        }
        try:
            # Ensure the config directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            if hasattr(self, 'console'):
                self.console.append(f"Error saving configuration: {str(e)}")
            else:
                print(f"Error saving configuration: {str(e)}")
             
    def set_base_directory(self):
        """Let the user choose the base directory for data storage."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Base Directory for Data Storage",
            self.base_dir
        )
        
        if directory:
            old_work_dir = self.work_dir
            self.base_dir = directory
            self.work_dir = directory
            self.save_config()
            
            # Update UI with path
            self.console.append(f"Data directory changed to: {self.work_dir}")
            
            # Create required folders in new directory
            self.create_required_folders()

            copy_tutorial_files(self.work_dir)
            
                
            # Ask if user wants to copy existing data if we had a previous directory
            if os.path.exists(old_work_dir) and old_work_dir != self.work_dir:
                reply = QMessageBox.question(
                    self, 
                    "Copy Existing Data",
                    f"Do you want to copy existing data from\n{old_work_dir}\nto the new location?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.copy_data(old_work_dir, self.work_dir)

    def copy_data(self, source_dir, target_dir):
        """Move data from old directory to new directory."""
        import shutil
        try:
            folders = ['IMAGES', 'GEOMETRY', 'SEGY', 'ROI', 'PARAMETERS']
            for folder in folders:
                src_folder = os.path.join(source_dir, folder)
                dst_folder = os.path.join(target_dir, folder)
                
                if os.path.exists(src_folder):
                    # Create target folder if it doesn't exist
                    os.makedirs(dst_folder, exist_ok=True)
                    
                    # Move all files from source to target
                    for item in os.listdir(src_folder):
                        src_item = os.path.join(src_folder, item)
                        dst_item = os.path.join(dst_folder, item)
                        if os.path.isfile(src_item):
                            shutil.move(src_item, dst_item)
            
            self.console.append("Data moved successfully to new location")
        except Exception as e:
            self.console.append(f"Error moving data: {str(e)}")
            QMessageBox.warning(self, "Move Error", f"Error moving data: {str(e)}")

    def how_to(self):
        """Show help dialog with information about the application."""
        help_dialog = HelpDialog(self)
        help_dialog.show()

    def show_about_dialog(self):
        """Show the About dialog."""
        about_dialog = AboutDialog(self)
        about_dialog.show()

    def restart_process(self):
        """Restart the application by closing windows and resetting state."""
        reply = QMessageBox.question(
            self, 
            "Restart Process",
            "Are you sure you want to restart?\nAll unsaved progress will be lost.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset state
            self.image_path = None
            self.img_array = None
            self.points = []
            self.rectified_image = None
            self.binary_rectified_image = None
            self.parameters = {}
            
            # Go back to welcome tab
            self.tab_container.switch_to("welcome")
            self.navigation_panel.set_active("welcome")
            self.navigation_panel.enable_tabs_until("welcome")
            
            # Clear console
            self.console.clear()
            info_message(self.console, "Application restarted. Please start a new line.")

    def create_required_folders(self):
        """Create the necessary folder structure for the application."""
        # Main folders needed for the application
        required_folders = ['IMAGES', 'GEOMETRY', 'SEGY', 'ROI', 'PARAMETERS', 'LOG']
        
        # Create each folder in the script directory
        for folder in required_folders:
            folder_path = os.path.join(self.work_dir, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                self.console.append(f"Folder created: {folder_path}") if hasattr(self, 'console') else None
            except Exception as e:
                if hasattr(self, 'console'):
                    self.console.append(f"Error creating folder {folder_path}: {str(e)}")
                else:
                    print(f"Error creating folder {folder_path}: {str(e)}")

    def closeEvent(self, event):
        """Handle application close event."""
        # Close log file properly before exiting
        close_log_file()
        event.accept()