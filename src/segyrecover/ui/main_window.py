"""Main window for SEGYRecover application."""
import matplotlib
matplotlib.use('QtAgg')
import os
import json
import subprocess
from PySide6.QtGui import QFont, QAction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QStatusBar, QProgressBar, 
                               QVBoxLayout, QLabel, QPushButton, QMessageBox, 
    QWidget, QTextEdit, QStyle, QDialog, QFileDialog, QMainWindow
)

import appdirs

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


from .help_dialogs import HelpDialog, FirstRunDialog, AboutDialog
from .image_viewer import ImageLoader
from .workflow import load_image, input_parameters, select_area, initialize
from ..utils.resource_utils import copy_tutorial_files
from ..utils.console_utils import (
    section_header, info_message, initialize_log_file, close_log_file
)


class ProgressStatusBar(QStatusBar):
    """Status bar with integrated progress bar."""

    def __init__(self, parent=None):
        """Initialize the progress status bar.""" 
        super().__init__(parent)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(200)
        
        # Create cancel button
        self.cancel_button = QPushButton()
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
        
        # Make window dimensions consistent - use 400x800 for both fixed size and minimum size
        self.setFixedSize(400, 800)
        
        # Get appropriate directories for user data and config
        self.app_name = "SEGYRecover"
        self.user_data_dir = appdirs.user_data_dir(self.app_name)
        self.user_config_dir = appdirs.user_config_dir(self.app_name)
        
        # Ensure config directory exists
        os.makedirs(self.user_config_dir, exist_ok=True)
        self.config_path = os.path.join(self.user_config_dir, 'config.json')
        
        self.load_config()
        
        self.image_path = None
        self.img_array = None
        self.points = []
        self.image_canvas = None
        self.plot_location_canvas = None
        
        self.create_required_folders()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.create_menu_bar()
        
        self.setup_ui()
        
        # Initialize log file
        self.log_file_path = initialize_log_file(self.work_dir)
        if self.log_file_path:
            info_message(self.console, f"Log file created: {os.path.basename(self.log_file_path)}")
        
        self.image_loader = ImageLoader(
            parent=self,
            console=self.console,
            work_dir=self.work_dir
        )
        
        figure = plt.figure()
        self.image_canvas = FigureCanvas(figure)
        
        self.roi_manager = initialize(
            self.progress, 
            self.console, 
            self.work_dir,
            self.image_canvas
        )
        
    def create_menu_bar(self):
        """Create the menu bar with file and help menus."""
        menu_bar = self.menuBar()
        
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

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 15)  # Left, top, right, bottom
        # Title with smaller font
        title_label = QLabel("SEGYRECOVER", self.central_widget)
        title_label.setFont(QFont("Arial", 18, QFont.Bold))  
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addSpacing(10)

        # Load Image button
        self.load_button = QPushButton("Load Image", self.central_widget)
        self.load_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.load_button.clicked.connect(lambda: load_image(self))
        layout.addWidget(self.load_button)

        # Parameters button
        self.param_button = QPushButton("Parameters", self.central_widget)
        self.param_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.param_button.setEnabled(False)
        self.param_button.clicked.connect(lambda: input_parameters(self))
        layout.addWidget(self.param_button)

        # Begin Digitization button
        self.begin_digitization_button = QPushButton("Begin Digitization", self.central_widget)
        self.begin_digitization_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.begin_digitization_button.setEnabled(False)
        self.begin_digitization_button.clicked.connect(lambda: select_area(self))
        layout.addWidget(self.begin_digitization_button)

        self.load_button.setToolTip("Load a seismic image file (TIF, JPEG, PNG)")
        self.param_button.setToolTip("Configure processing parameters")
        self.begin_digitization_button.setToolTip("Start digitization process") 

        layout.addSpacing(8)

        # Create the progress bar as the main window's status bar
        self.progress = ProgressStatusBar()
        layout.addWidget(self.progress)

        layout.addSpacing(8)  

        console_label = QLabel("CONSOLE OUTPUT", self.central_widget)
        console_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(console_label)

        self.console = QTextEdit(self.central_widget)
        self.console.setStyleSheet("font-family: 'Consolas', 'Courier New'; font-size: 9pt;")
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.WidgetWidth) 
        self.console.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.console)

        layout.addSpacing(10)
        
        restart_button = QPushButton("Restart Process", self.central_widget)
        restart_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        restart_button.clicked.connect(self.restart_process)
        layout.addWidget(restart_button)

        self.central_widget.setLayout(layout)
        
        # Show current directory in console with improved formatting
        section_header(self.console, "INITIALIZATION")
        info_message(self.console, f"Data directory: {self.work_dir}")
        info_message(self.console, "Application ready")
             
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
            
            # Update image loader with new directory
            if hasattr(self, 'image_loader'):
                self.image_loader.work_dir = self.work_dir
                
            # Re-initialize the workflow module with the new directory
            self.roi_manager = initialize(
                self.progress, 
                self.console, 
                self.work_dir,
                self.image_canvas
            )
            
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
            "Are you sure you want to restart?\nAll windows will be closed.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Close all popup windows
            for child in self.findChildren(QDialog):
                child.close()
                
            # Reset state
            self.image_path = None
            self.img_array = None
            self.points = []
            
            # Reset buttons
            self.param_button.setEnabled(False)
            self.begin_digitization_button.setEnabled(False)
            
            # Clear console
            self.console.clear()
            self.console.append("Application restarted. Please load a new image.\n")
            
            # Re-enable load button
            self.load_button.setEnabled(True)

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