import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QColor

def create_window(title, x, y, width, height, color):
    """Create a window with specified position, size, title and background color."""
    window = QMainWindow()
    window.setWindowTitle(title)
    window.setGeometry(x, y, width, height)
    
    # Set background color to make windows distinguishable
    palette = window.palette()
    palette.setColor(window.backgroundRole(), color)
    window.setPalette(palette)
    window.setAutoFillBackground(True)
    
    window.show()
    return window

def main():
    """Create and display all windows."""
    app = QApplication(sys.argv)
    
    # Get actual screen dimensions
    screen = QApplication.primaryScreen().geometry()
    
    screen_width = min(screen.width(), 1920)
    screen_height = min(screen.height(), 1080)
    
    # Create Control Panel Window (left side)
    x_control = int(screen_width * 0.05)
    y_control = int(screen_height * 0.05)
    width_control = int(screen_width * 0.25)
    height_control = int(screen_height * 0.85)
    control_window = create_window(
        "Control Panel Window", 
        x_control, y_control, 
        width_control, height_control, 
        QColor(220, 220, 220)  # Light gray
    )
        
    # Create Image Window (top-center)
    x_image = int(screen_width * 0.3+10)
    y_image = int(screen_height * 0.05)
    width_image = int(screen_width * 0.6)
    height_image = int(screen_height * 0.4)
    image_window = create_window(
        "Image Window", 
        x_image, y_image, 
        width_image, height_image, 
        QColor(200, 230, 255)  # Light blue
    )
    
    # Create Location Window (top-right)
    x_location = int(screen_width * 0.3+10)
    y_location = int(screen_height * 0.5)
    width_location = int(screen_width * 0.6)
    height_location = int(screen_height * 0.4)

    location_window = create_window(
        "Location Window", 
        x_location, y_location, 
        width_location, height_location, 
        QColor(230, 255, 200)  # Light green
    )
    
    # Create SEGY Results Window (bottom-center)
    x_segy = int(screen_width * 0.3 + 10)
    y_segy = int(screen_height * 0.5)
    width_segy = int(screen_width * 0.35)
    height_segy = int(screen_height * 0.4)
    segy_window = create_window(
        "SEGY Results Window", 
        x_segy, y_segy, 
        width_segy, height_segy, 
        QColor(255, 230, 200)  # Light orange
    )
    
    # Create Amplitude Spectrum Window (bottom-right)
    x_spectrum = int(screen_width * 0.65 + 20)
    y_spectrum = int(screen_height * 0.5)
    width_spectrum = int(screen_width * 0.3)
    height_spectrum = int(screen_height * 0.4)
    spectrum_window = create_window(
        "Amplitude Spectrum Window", 
        x_spectrum, y_spectrum, 
        width_spectrum, height_spectrum, 
        QColor(255, 200, 230)  # Light pink
    )
    
    # Print out the actual positions and sizes for verification
    print(f"Control Panel Window: x={control_window.x()}, y={control_window.y()}, width={control_window.width()}, height={control_window.height()}")
    print(f"Image Window: x={image_window.x()}, y={image_window.y()}, width={image_window.width()}, height={image_window.height()}")
    print(f"Location Window: x={location_window.x()}, y={location_window.y()}, width={location_window.width()}, height={location_window.height()}")
    print(f"SEGY Window: x={segy_window.x()}, y={segy_window.y()}, width={segy_window.width()}, height={segy_window.height()}")
    print(f"Spectrum Window: x={spectrum_window.x()}, y={spectrum_window.y()}, width={spectrum_window.width()}, height={spectrum_window.height()}")
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()