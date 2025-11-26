"""Image processing functionality for SEGYRecover."""

import os
import numpy as np
from PySide6.QtCore import Qt
from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message
)
class ImageProcessor:
    """Class for processing seismic images."""
    
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir

    def remove_timelines(self, image_input, HE, HLT, TPT):
        """Timeline removal algorithm """

        info_message(self.console, "Detecting and removing timelines...")
        self.progress.start("Detecting timelines...", 6)

        try:
            #self._save_image_array(image_input, "image_input")
            
            image_eroded_left = image_input.copy()
            self._erosion_left(image_eroded_left, HE)
            #self._save_image_array(image_eroded_left, "image_eroded_left")
            self.progress.update(1)

            image_no_short_segments = image_eroded_left.copy()
            self._remove_vertical_segments(image_no_short_segments, HLT)
            #self._save_image_array(image_no_short_segments, "image_no_short_segments")
            self.progress.update(2)

            image_eroded_both = image_no_short_segments.copy()
            self._erosion_right(image_eroded_both, HE)
            #self._save_image_array(image_eroded_both, "image_eroded_both")
            self.progress.update(3)

            # Detect timelines using histogram and extend them
            threshold_percentage = TPT / 100.0  
            image_timelines = self._detect_and_extend_timelines(image_eroded_both, threshold_percentage)
            
            #image_timelines = image_no_short_segments.copy()

            # Apply vertical dilation to make lines slightly thicker
            self._dilation_top(image_timelines, max(1, int(HLT/2)))
            self._dilation_bottom(image_timelines, max(1, int(HLT/2)))
            #self._save_image_array(image_timelines, "image_timelines")
            self.progress.update(4)

            image_input_no_segments = image_input.copy()
            self._remove_vertical_segments(image_input_no_segments, HLT)
            #self._save_image_array(image_input_no_segments, "image_input_no_segments")
            self.progress.update(5)

            image_clean = image_input.copy()
            image_clean[(image_input_no_segments == 0) & (image_timelines == 0)] = 255
            self._save_image_array(image_clean, "image_clean")

            self.progress.finish()
            return image_clean, image_timelines
        
        except Exception as e:
            error_message(self.console, f"Error removing timelines: {e}")
            return None, None

    def detect_baselines(self, image_clean, TLT, BDB, BDE, BFT):
        """Detect vertical baselines in image"""
        info_message(self.console, "Detecting baselines...")
        self.progress.start("Detecting baselines...", 10)

        try:
            #self._save_image_array(image_clean, "image_clean_baseline_input")
            
            # 1. Enhance baselines through morphological operations
            image_baseline_eroded_left = image_clean.copy()
            self._erosion_left(image_baseline_eroded_left, TLT)  
            #self._save_image_array(image_baseline_eroded_left, "image_baseline_eroded_left")
            self.progress.update(1)

            image_baseline_eroded_top = image_baseline_eroded_left.copy()
            self._erosion_top(image_baseline_eroded_top, TLT)  
            #self._save_image_array(image_baseline_eroded_top, "image_baseline_eroded_top")
            self.progress.update(2)

            image_baseline_dilated_top = image_baseline_eroded_top.copy()
            self._dilation_top(image_baseline_dilated_top, TLT) 
            #self._save_image_array(image_baseline_dilated_top, "image_baseline_dilated_top")
            self.progress.update(3)

            image_baseline_dilated_left = image_baseline_dilated_top.copy()
            self._dilation_left(image_baseline_dilated_left, TLT)  
            #self._save_image_array(image_baseline_dilated_left, "image_baseline_dilated_left")
            self.progress.update(4)

            image_baselines = image_baseline_dilated_left.copy()
            self._dilation_left(image_baselines, TLT)              
            image_baselines[(image_baseline_dilated_left == 0)] = 255 
            #self._save_image_array(image_baselines, "image_baselines")
            self.progress.update(5)

            image_processed = image_baselines.copy()

            # 2. Find transitions
            height, width = image_processed.shape
            transitions = []
            for y in range(BDB, BDE):
                row = image_processed[y, :]
                bl = np.where((row[:-1] == 255) & (row[1:] == 0))[0] + 1
                transitions.extend([(x, y) for x in bl])
            self.progress.update(6)

            # 3. Count transitions per column
            tr_per_col = np.zeros(width, dtype=int)
            for x, y in transitions:
                tr_per_col[x] += 1
            self.progress.update(7)

            # 4. Detect initial baselines
            raw_baselines = self._detect_peaks(tr_per_col)
            self.progress.update(8)

            # 5. Filter close baselines
            clean_baselines = self._filter_baselines(raw_baselines, tr_per_col, BFT)
            self.progress.update(9)

            # 6. Add synthetic baselines
            final_baselines = self._add_synthetic_baselines(clean_baselines)
            self.progress.update(10)

            #self._save_baselines(raw_baselines, "raw_baselines")
            #self._save_baselines(clean_baselines, "clean_baselines")
            self._save_baselines(final_baselines, "final_baselines")

            self.progress.finish()
            return image_baselines, raw_baselines, clean_baselines, final_baselines

        except Exception as e:
            error_message(self.console, f"Error in baseline detection: {str(e)}")
            return None, None, None, None

    # Helper methods
    def _detect_peaks(self, tr_per_col):
        """Detect peaks in transition counts"""
        baselines = set()
        for col in range(2, len(tr_per_col) - 2):
            # Check if column is a local maximum
            if (tr_per_col[col] > max(tr_per_col[col-1], tr_per_col[col-2]) and 
                tr_per_col[col] > max(tr_per_col[col+1], tr_per_col[col+2])):
                baselines.add(col)
            # Check for plateau maximum
            elif (tr_per_col[col] == max(tr_per_col[col+1], tr_per_col[col+2]) and 
                  tr_per_col[col] != 0):
                baselines.add(col + 1)
                
        # Add isolated peaks
        for col in range(1, len(tr_per_col) - 1):
            if (tr_per_col[col] > 0 and 
                tr_per_col[col-1] == 0 and 
                tr_per_col[col+1] == 0):
                baselines.add(col)
                
        return sorted(list(baselines))
    
    def _filter_baselines(self, baselines, tr_per_col, BFT):
        """Filter out baselines that are too close together"""
        if not baselines:
            return []
            
        distances = np.diff(baselines)
        median_distance = np.median(distances)
        threshold = (BFT / 100) * median_distance
        
        clean_baselines = [baselines[0]]
        for i in range(1, len(baselines)):
            if baselines[i] - clean_baselines[-1] >= threshold:
                clean_baselines.append(baselines[i])
            else:
                # Keep the one with higher transition count
                if tr_per_col[baselines[i]] > tr_per_col[clean_baselines[-1]]:
                    clean_baselines[-1] = baselines[i]
                    
        return clean_baselines

    def _add_synthetic_baselines(self, baselines):
        """Add synthetic baselines in large gaps"""
        if not baselines:
            return []
            
        distances = np.diff(baselines)
        median_distance = np.median(distances)
        gap_threshold = 1.5 * median_distance
        
        interpolated = [baselines[0]]
        for i in range(1, len(baselines)):
            current_gap = baselines[i] - interpolated[-1]
            if current_gap > gap_threshold:
                # Add synthetic baselines
                n_synthetic = int(round(current_gap / median_distance)) - 1
                spacing = current_gap / (n_synthetic + 1)
                
                for j in range(n_synthetic):
                    new_baseline = int(round(interpolated[-1] + spacing * (j + 1)))
                    interpolated.append(new_baseline)
                    
            interpolated.append(baselines[i])
            
        return interpolated

    # Morphological operations
    def _erosion_left(self, image, px):
        for row in image:
            transitions = np.where((row[:-1] == 255) & (row[1:] == 0))[0]
            if len(transitions) > 0:
                for i in transitions[1:]:  # Process all except the first one
                    row[i:i+px+1] = 255

    def _erosion_right(self, image, px):
        width = image.shape[1]
        for row in image:
            transitions = np.where((row[1:] == 255) & (row[:-1] == 0))[0]
            if len(transitions) > 0:
                for i in transitions[:-1]:  # Process all except the last one
                    row[max(0, i-px+1):i+1] = 255

    def _erosion_top(self, image, px):
        for col in range(image.shape[1]):
            transitions = np.where((image[:-1, col] == 255) & (image[1:, col] == 0))[0]
            for i in transitions:
                image[i+1:i+px+1, col] = 255

    def _dilation_right(self, image, px):
        for row in image:
            transitions = np.where((row[:-1] == 0) & (row[1:] == 255))[0]
            for i in transitions:
                row[i:i+px+1] = 0
    
    def _dilation_left(self, image, px):
        for row in image:
            transitions = np.where((row[1:] == 0) & (row[:-1] == 255))[0]
            for i in transitions:
                row[max(0, i-px+1):i+1] = 0

    def _dilation_top(self, image, px):
        for col in range(image.shape[1]):
            transitions = np.where((image[1:, col] == 0) & (image[:-1, col] == 255))[0]
            for i in transitions:
                image[max(0, i-px+1):i+1, col] = 0

    def _dilation_bottom(self, image, px):
        for col in range(image.shape[1]):
            transitions = np.where((image[:-1, col] == 0) & (image[1:, col] == 255))[0]
            for i in transitions:
                image[i+1:i+px+1, col] = 0

    def _remove_vertical_segments(self, image, px):
        black_pixels = image == 0

        for col in range(image.shape[1]):
            col_data = black_pixels[:, col]
            
            # Find the start and end of each segment of black pixels (0)
            transitions = np.diff(np.concatenate(([0], col_data.astype(int), [0])))
            segment_starts = np.where(transitions == 1)[0]
            segment_ends = np.where(transitions == -1)[0]

            # Verify that the segment is longer than the threshold
            for start, end in zip(segment_starts, segment_ends):
                if (end - start) > px:
                    image[start:end, col] = 255  # Convert the segment to white

    def _detect_and_extend_timelines(self, image, threshold_percentage):
        """
        Detect timeline rows using horizontal histogram and extend them fully.
        """
        height, width = image.shape
        
        # 1. Create horizontal histogram (count black pixels per row)
        black_pixels_per_row = np.sum(image == 0, axis=1)
        
        # 2. Calculate threshold (rows with at least X% of black pixels)
        threshold = width * threshold_percentage
        
        # 3. Detect timeline rows
        timeline_rows = black_pixels_per_row >= threshold
        
        # 4. Create output image with extended timelines
        result = np.ones_like(image) * 255  # Start with white image


        # 5. For each detected timeline row, fill the entire row with black
        for row_idx in np.where(timeline_rows)[0]:
            result[row_idx, :] = 0

    
        return result


# _save_image_array and _save_baselines methods can be used to save intermediate results
# to the disk for debugging and analysis purposes. 
# These methods create a directory named "raw" in the working directory
# and save the images or baselines as NumPy arrays (.npy files).
# 

    def _save_image_array(self, image, name):
        """Save intermediate image as NumPy array (.npy file)"""
        try:
            # Create raw directory if it doesn't exist
            save_dir = os.path.join(self.work_dir, "raw")
            os.makedirs(save_dir, exist_ok=True)
            
            # Save the NumPy array
            file_path = os.path.join(save_dir, f"{name}.npy")
            np.save(file_path, image)
            
            info_message(self.console, f"Saved {name} to {file_path}")
        except Exception as e:
            error_message(self.console, f"Error saving image {name}: {e}")

    def _save_baselines(self, baselines, name):
        try:
            # Create raw directory if it doesn't exist
            save_dir = os.path.join(self.work_dir, "raw")
            os.makedirs(save_dir, exist_ok=True)
            
            # Convert to numpy array if it's not already
            baseline_array = np.array(baselines)
            
            # Save the NumPy array
            file_path = os.path.join(save_dir, f"{name}.npy")
            np.save(file_path, baseline_array)
            
            info_message(self.console, f"Saved {name} baselines to {file_path}")
        except Exception as e:
            error_message(self.console, f"Error saving baselines {name}: {e}")