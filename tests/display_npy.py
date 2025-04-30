import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout, 
                             QWidget, QLabel, QPushButton, QFileDialog)
from PySide6.QtCore import Qt

class NpyViewerApp(QMainWindow):
    def __init__(self, raw_folder=None):
        super().__init__()
        self.setWindowTitle("NPY File Viewer")
        self.setMinimumSize(800, 600)
        
        # Create a central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create a tab widget
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)
        
        # Add a button for selecting folder if no folder is provided
        if not raw_folder or not os.path.exists(raw_folder):
            self.folder_button = QPushButton("Select Folder with NPY Files")
            self.folder_button.clicked.connect(self.select_folder)
            self.layout.addWidget(self.folder_button)
            self.status_label = QLabel("No folder selected")
            self.layout.addWidget(self.status_label)
        else:
            self.load_npy_files(raw_folder)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder with NPY Files")
        if folder_path:
            self.load_npy_files(folder_path)
    
    def load_npy_files(self, folder_path):
        # Clear any existing tabs
        self.tab_widget.clear()
        
        # Find all NPY files that start with 'image'
        npy_files = sorted([f for f in os.listdir(folder_path) 
                           if f.startswith('image') and f.endswith('.npy')])
        
        if not npy_files:
            self.tab_widget.addTab(QLabel("No .npy files starting with 'image' found"), "No Files")
            return
        
        # Create a tab for each NPY file
        for npy_file in npy_files:
            file_path = os.path.join(folder_path, npy_file)
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            
            # Create matplotlib figure
            fig = Figure(figsize=(10, 8))
            canvas = FigureCanvas(fig)
            
            # Add navigation toolbar
            toolbar = NavigationToolbar(canvas, tab)
            tab_layout.addWidget(toolbar)
            tab_layout.addWidget(canvas)
            
            # Load and display the NPY data
            data = np.load(file_path)
            ax = fig.add_subplot(111)
            im = ax.imshow(data, aspect='auto', cmap='grey', interpolation='none')
            
            # Add a colorbar
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Amplitude')
            
            # Add title and labels
            ax.set_title(f"{npy_file}")
            ax.set_xlabel('Trace')
            ax.set_ylabel('Sample')
            
            fig.tight_layout()
            canvas.draw()
            
            # Add the tab with a cleaned up name
            tab_name = npy_file.replace('image', '').replace('.npy', '')
            self.tab_widget.addTab(tab, tab_name)
        
        # If we previously had the folder selection button, remove it
        if hasattr(self, 'folder_button'):
            self.folder_button.setVisible(False)
            self.status_label.setText(f"Loaded {len(npy_files)} files from {folder_path}")

def display_npy_files(raw_folder):
    """Display .npy files starting with 'image' in the specified folder in a PySide6 GUI."""
    app = QApplication.instance() or QApplication(sys.argv)
    viewer = NpyViewerApp(raw_folder)
    viewer.show()
    app.exec()

if __name__ == "__main__":
    # Default folder path, will prompt to select if not found
    raw_folder = r'C:\Users\Alex\Documents\SEGYRecover\raw'
    display_npy_files(raw_folder)