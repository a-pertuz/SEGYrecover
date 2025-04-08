"""Image loading and ROI handling for SEGYRecover."""

import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QApplication, QVBoxLayout, QMessageBox, QFileDialog
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import zoom
import seisio
import seisplot


def display_segy_results(segy_path, parent=None):
    """Display SEGY section and amplitude spectrum."""
    try:
        # Get base name
        base_name = os.path.splitext(os.path.basename(segy_path))[0]

        # 1. Display SEGY Section
        seis_window = QDialog(parent)
        seis_window.setWindowTitle('Digitized SEGY')        
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = int(screen_width * 0.3 + 10)
        pos_y = int(screen_height * 0.5)
        window_width= int(screen_width * 0.35)
        window_height = int(screen_height * 0.4)
        seis_window.setGeometry(pos_x, pos_y, window_width, window_height)  

        # Create layout and canvas
        layout = QVBoxLayout(seis_window)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        seis_canvas = FigureCanvas(fig)

        # Load and plot SEGY data
        sio = seisio.input(segy_path)
        dataset = sio.read_all_traces()
        seis = dataset["data"]
        seisplot.plot(seis, 
                    perc=99, 
                    haxis="tracf", 
                    hlabel="Trace no.", 
                    vlabel="Time (ms)",
                    ax=ax)  

        layout.addWidget(seis_canvas)
        layout.addWidget(NavigationToolbar(seis_canvas, seis_window))
        seis_window.show()
        seis_canvas.draw()

        return seis_window
    except Exception as e:
        print(f"Error displaying SEGY results: {str(e)}")
        return None

def display_amplitude_spectrum(filtered_data, dt, parent=None):
    """Display amplitude spectrum window."""
    try:
        # Display Amplitude Spectrum
        spectrum_window = QDialog(parent)
        spectrum_window.setWindowTitle('Average Amplitude Spectrum')    
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = int(screen_width * 0.65 + 20)
        pos_y = int(screen_height * 0.5)
        window_width= int(screen_width * 0.3)
        window_height = int(screen_height * 0.4)
        spectrum_window.setGeometry(pos_x, pos_y, window_width, window_height)

        # Create layout and canvas
        spectrum_layout = QVBoxLayout(spectrum_window)
        spectrum_canvas = FigureCanvas(plt.figure())
        spectrum_ax = spectrum_canvas.figure.add_subplot(111)

        # Calculate and plot spectrum
        fs = 1 / (dt / 1000)
        fs_filtered = np.zeros(filtered_data.shape, dtype=complex)
        for i in range(filtered_data.shape[1]):
            fs_filtered[:,i] = np.fft.fft(filtered_data[:,i])

        freqs = np.fft.fftfreq(filtered_data.shape[0], 1/fs)
        fsa_filtered = np.mean(np.abs(fs_filtered), axis=1)
        fsa_filtered = fsa_filtered/np.max(fsa_filtered)

        pos_freq_mask = freqs >= 1
        spectrum_ax.plot(freqs[pos_freq_mask], fsa_filtered[pos_freq_mask], 'r')
        spectrum_ax.set_xlim(0, 100)  
        spectrum_ax.set_xlabel('Frequency (Hz)')
        spectrum_ax.set_ylabel('Normalized Amplitude')
        spectrum_ax.set_title('Averaged Amplitude Spectrum') 
        spectrum_ax.grid(True)

        spectrum_layout.addWidget(spectrum_canvas)
        spectrum_layout.addWidget(NavigationToolbar(spectrum_canvas, spectrum_window))
        spectrum_window.show()
        spectrum_canvas.draw()

        return spectrum_window
    except Exception as e:
        print(f"Error displaying amplitude spectrum: {str(e)}")
        return None


class ImageLoader:
    """Handles image loading and display functionality"""
    def __init__(self, parent, console, work_dir):
        self.parent = parent
        self.console = console
        self.work_dir = work_dir
        self.image_path = None
        self.img_array = None
        self.image_window = None
        self.location_window = None
        self.image_canvas = None
        self.plot_location_canvas = None

    def load_image(self):
        """Load and display image with geometry"""
        # Start in the IMAGES folder of the script directory
        images_dir = os.path.join(self.work_dir, "IMAGES")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Seismic Image File",
            images_dir,  # Now starting in IMAGES folder
            "Image Files (*.tif *.jpg *.png);;All Files (*.*)"
        )
        
        if not file_path:
            return False

        img_array = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        if img_array is None:
            QMessageBox.warning(self.parent, "Error", "Could not load image.")
            return False

        self.image_path = file_path
        self.img_array = img_array

        self.image_window = self._create_image_window()  
        self.location_window = self._create_location_window()
        
        # Load and display geometry data
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        self._load_geometry_data(base_name)
            
        self.console.append(f"Image loaded: {self.image_path}\n")
        return True

    def _create_image_window(self):
        """Create window to display seismic image"""
        image_window = QDialog(self.parent)
        image_window.setWindowTitle('Seismic Section Image')          
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = int(screen_width * 0.3 + 10)
        pos_y = int(screen_height * 0.05)
        window_width= int(screen_width * 0.35)
        window_height = int(screen_height * 0.4)
        image_window.setGeometry(pos_x, pos_y, window_width, window_height)  
       
        layout = QVBoxLayout(image_window)

        display_img = zoom(self.img_array, 0.25, order=1, prefilter=True)
         
        self.image_canvas = FigureCanvas(plt.figure())
        self.image_canvas.setFocusPolicy(Qt.StrongFocus)
        self.image_canvas.figure.add_subplot(111).imshow(display_img, cmap='gray')     

        layout.addWidget(self.image_canvas)
        layout.addWidget(NavigationToolbar(self.image_canvas, image_window))
        
        image_window.show()
        self.image_canvas.draw()

        return image_window

    def _create_location_window(self):
        """Create window to display geometry plot"""
        window = QDialog(self.parent)
        window.setWindowTitle('Seismic Line Location')      
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        pos_x = int(screen_width * 0.65 + 20)
        pos_y = int(screen_height * 0.05)
        window_width= int(screen_width * 0.3)
        window_height = int(screen_height * 0.4)
        window.setGeometry(pos_x, pos_y, window_width, window_height)

        layout = QVBoxLayout(window)

        fig = plt.figure(figsize=(12,8))
        self.plot_location_canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.set_xlabel('UTM X')
        ax.set_ylabel('UTM Y')
        ax.grid(True)
        fig.tight_layout(pad=2.0)
        fig.subplots_adjust(left=0.08, right=0.95, bottom=0.15)  # Increased bottom margin
        
        layout.addWidget(self.plot_location_canvas)
        layout.addWidget(NavigationToolbar(self.plot_location_canvas, window))
        
        window.show()
        return window
        
    def _load_geometry_data(self, base_name):
        """Load and display geometry data"""
        geometry_file = os.path.join(self.work_dir, 'GEOMETRY', f'{base_name}.geometry')
        
        if not os.path.exists(geometry_file):
            self.console.append("Geometry file not found.\n")
            return False
            
        try:
            cdp, x, y = [], [], []
            with open(geometry_file, 'r') as file:
                for line in file:
                    parts = line.strip().split()
                    cdp.append(parts[0])
                    x.append(float(parts[1]))
                    y.append(float(parts[2]))
            ax = self.plot_location_canvas.figure.get_axes()[0]        
            ax.plot(x, y, marker='o', markersize=2, color='red', linestyle='-')
            # Add labels with threshold to avoid overcrowding
            threshold = 1000
            annotated_positions = []
            for i, txt in enumerate(cdp):
                position = (x[i], y[i])
                if all(np.linalg.norm(np.array(position) - np.array(p)) > threshold 
                      for p in annotated_positions):
                    ax.annotate(txt, position)
                    annotated_positions.append(position)
            ax.set_title(f"COORDINATES \"{base_name}\"")
            ax.set_aspect('equal', adjustable='datalim')  # Changed from 'box' to 'datalim'
            # Rotate x-axis labels to prevent overlap
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            # Apply tight layout again after plotting to optimize space
            self.plot_location_canvas.figure.tight_layout()
            self.plot_location_canvas.draw()
            return True

        except Exception as e:
            self.console.append(f"<span style='color:red'>Error loading geometry: {str(e)}</span>\n")
            return False