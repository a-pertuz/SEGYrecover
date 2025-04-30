"""ROI selection logic for SEGYRecover application."""

import os
import numpy as np
import cv2
import math
from scipy.ndimage import zoom
from ..utils.console_utils import info_message, error_message, success_message

class ROIProcessor:
    """Handles ROI processing, transformations, and file operations."""
    
    def __init__(self, console, work_dir):
        self.console = console
        self.work_dir = work_dir
        self.points = []
        self.image_path = None
        self.img_array = None
        self.display_image = None
        self.rectified_image = None
        self.binary_rectified_image = None
        self.downsample_factor = 1
        
        # Maximum image dimension for display (pixels)
        self.MAX_DISPLAY_DIMENSION = 2000
    
    def set_image(self, image_path, img_array):
        """Set the image to process."""
        self.image_path = image_path
        self.img_array = img_array
        self.downsample_factor = self._calculate_adaptive_downsample_factor()
        self.display_image = self._downsample_image(self.img_array, self.downsample_factor)
        self.points = []
        self.rectified_image = None
        self.binary_rectified_image = None
    
    def _calculate_adaptive_downsample_factor(self):
        """Calculate an adaptive downsampling factor based on image size."""
        if self.img_array is None:
            return 1
            
        # Get dimensions of image
        height, width = self.img_array.shape
        max_dim = max(height, width)
        
        # No downsampling needed for small images
        if max_dim <= self.MAX_DISPLAY_DIMENSION:
            return 1
            
        # Calculate factor to make the largest dimension fit within MAX_DISPLAY_DIMENSION
        factor = max(1, math.ceil(max_dim / self.MAX_DISPLAY_DIMENSION))
        
        # Cap the factor at 4 for quality
        return min(factor, 4)
    
    def _downsample_image(self, image, factor):
        """Downsample image using a high-quality method."""
        if factor <= 1:
            return image
            
        try:
            # Use zoom for better quality downsampling
            scale_factor = 1.0 / factor
            return zoom(image, scale_factor, order=1, prefilter=True)
        except MemoryError:
            # Fallback to simpler method if memory error occurs
            return image[::factor, ::factor]
    
    def display_to_original(self, x, y):
        """Convert coordinates from display to original image space."""
        if x is None or y is None:
            return None, None
            
        # Scale coordinates
        orig_x = round(x * self.downsample_factor)
        orig_y = round(y * self.downsample_factor)
        
        # Ensure coordinates are within bounds
        if self.img_array is not None:
            height, width = self.img_array.shape
            orig_x = max(0, min(orig_x, width - 1))
            orig_y = max(0, min(orig_y, height - 1))
        
        return orig_x, orig_y
    
    def original_to_display(self, x, y):
        """Convert coordinates from original to display space."""
        if x is None or y is None:
            return None, None
            
        # Scale coordinates
        display_x = round(x / self.downsample_factor)
        display_y = round(y / self.downsample_factor)
        
        # Ensure coordinates are within bounds
        if self.display_image is not None:
            height, width = self.display_image.shape
            display_x = max(0, min(display_x, width - 1))
            display_y = max(0, min(display_y, height - 1))
        
        return display_x, display_y
    
    def calculate_fourth_point(self):
        """Calculate the fourth point based on the first three points."""
        if len(self.points) == 3:
            # Calculate fourth point: p4 = p2 + (p3 - p1)
            p1, p2, p3 = self.points
            p4_x = p2[0] + (p3[0] - p1[0])
            p4_y = p3[1] + (p2[1] - p1[1])
            p4 = (p4_x, p4_y)
            self.points.append(p4)
            return p4
        return None
    
    def process_roi(self):
        """Process the selected ROI and generate rectified image."""
        if len(self.points) != 4 or self.img_array is None:
            error_message(self.console, "Invalid ROI or missing image")
            return False
        
        try:
            info_message(self.console, "Calculating perspective transformation")
            
            # Apply perspective transform using original coordinates
            pts1 = np.float32(self.points)
            width = int(np.linalg.norm(np.array(self.points[0]) - np.array(self.points[1])))
            height = int(np.linalg.norm(np.array(self.points[0]) - np.array(self.points[2])))
            pts2 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            self.rectified_image = cv2.warpPerspective(self.img_array, matrix, (width, height))
            
            # Explicitly check the rectified image
            if self.rectified_image is None or self.rectified_image.size == 0:
                error_message(self.console, "Failed to create rectified image")
                return False
                
            # Convert to binary image with explicit handling
            ret, self.binary_rectified_image = cv2.threshold(self.rectified_image, 128, 255, cv2.THRESH_BINARY)
            
            if not ret or self.binary_rectified_image is None or self.binary_rectified_image.size == 0:
                error_message(self.console, "Failed to create binary rectified image")
                return False
            
            info_message(self.console, f"ROI processed - Binary image created with shape: {self.binary_rectified_image.shape}")
            
            # Save ROI points
            roi_path = self._get_roi_path()
            self.save_roi_points(roi_path)
            
            success_message(self.console, "Seismic section cropped and rectified")
            info_message(self.console, f"New dimensions: {width}x{height} pixels")
            
            return True
            
        except Exception as e:
            import traceback
            error_message(self.console, f"Error processing ROI: {str(e)}")
            error_message(self.console, traceback.format_exc())
            return False
    
    def _get_roi_path(self):
        """Get the path for saving/loading ROI points."""
        if not self.image_path:
            return None
            
        return os.path.join(
            self.work_dir, 
            "ROI", 
            f"{os.path.splitext(os.path.basename(self.image_path))[0]}.roi"
        )
    
    def load_roi_points(self, roi_path=None):
        """Load ROI points from file."""
        if roi_path is None:
            roi_path = self._get_roi_path()
            
        points = []
        try:
            with open(roi_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2:
                        points.append((float(parts[0]), float(parts[1])))
            self.points = points
            return points
        except Exception as e:
            error_message(self.console, f"Error loading ROI points: {str(e)}")
            return []
    
    def save_roi_points(self, roi_path=None):
        """Save ROI points to file."""
        if roi_path is None:
            roi_path = self._get_roi_path()
            
        try:
            os.makedirs(os.path.dirname(roi_path), exist_ok=True)
            with open(roi_path, "w") as f:
                for point in self.points:
                    f.write(f"{point[0]} {point[1]}\n")
            info_message(self.console, f"ROI points saved to: {os.path.basename(roi_path)}")
            return True
        except Exception as e:
            error_message(self.console, f"Error saving ROI points: {str(e)}")
            return False
    
    def check_existing_roi(self):
        """Check if there's an existing ROI file for the current image."""
        roi_path = self._get_roi_path()
        return roi_path is not None and os.path.exists(roi_path)
    
    def clear_points(self):
        """Clear all points."""
        self.points = []
        self.rectified_image = None
        self.binary_rectified_image = None