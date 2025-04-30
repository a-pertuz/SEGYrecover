"""Image processing functionality for SEGYRecover."""
import os
import numpy as np
from PySide6.QtCore import Qt

class ImageProcessor:
    """Class for processing seismic images."""
    
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir

    def remove_timelines(self, image_a, HE, HLT):
        """Timeline removal algorithm"""

        self.console.append("Detecting and removing timelines...\n")
        self.progress.start("Detecting timelines...", 6)

        try:
            self._save_image_array(image_a, "image_a")
            
            image_b = image_a.copy()
            self._erosion_left(image_b, HE)
            self._save_image_array(image_b, "image_b")
            self.progress.update(1)

            image_c = image_b.copy()
            self._remove_vertical_segments(image_c, HLT)
            self._save_image_array(image_c, "image_c")
            self.progress.update(2)

            image_d = image_c.copy()
            self._erosion_right(image_d, HE)
            self._save_image_array(image_d, "image_d")
            self.progress.update(3)

            image_f = image_d.copy()
            self._dilation_top(image_f, max(1, int(HLT/2)))
            self._dilation_bottom(image_f, max(1, int(HLT/2)))
            self._save_image_array(image_f, "image_f")
            self.progress.update(4)

            image_e = image_a.copy()
            self._remove_vertical_segments(image_e, HLT)
            self._save_image_array(image_e, "image_e")
            self.progress.update(5)

            image_g = image_a.copy()
            image_g[(image_e == 0) & (image_f == 0)] = 255
            self._save_image_array(image_g, "image_g")

            self.progress.finish()
            return image_g, image_f
        
        except Exception as e:
            self.console.setTextColor(Qt.red)
            self.console.append(f"Error removing timelines: {e}\n")
            self.console.setTextColor(Qt.black)
            return None, None

    def detect_baselines(self, image_g, TLT, BDB, BDE, BFT):
        """Detect vertical baselines in image"""
        self.console.append("Detecting baselines...\n")
        self.progress.start("Detecting baselines...", 10)

        try:
            self._save_image_array(image_g, "image_g_baseline_input")
            
            # 1. Enhance baselines through morphological operations
            image_i = image_g.copy()
            self._erosion_left(image_i, TLT)  
            self._save_image_array(image_i, "image_i")
            self.progress.update(1)

            image_j = image_i.copy()
            self._erosion_top(image_j, TLT)  
            self._save_image_array(image_j, "image_j")
            self.progress.update(2)

            image_k = image_j.copy()
            self._dilation_top(image_k, TLT) 
            self._save_image_array(image_k, "image_k")
            self.progress.update(3)

            image_l = image_k.copy()
            self._dilation_left(image_l, TLT)  
            self._save_image_array(image_l, "image_l")
            self.progress.update(4)

            image_m = image_l.copy()
            self._dilation_left(image_m, TLT)              
            image_m[(image_l == 0)] = 255 
            self._save_image_array(image_m, "image_m")
            self.progress.update(5)

            image_processed = image_m.copy()

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

            self._save_baselines(raw_baselines, "raw_baselines")
            self._save_baselines(clean_baselines, "clean_baselines")
            self._save_baselines(final_baselines, "final_baselines")

            self.progress.finish()
            return image_m, raw_baselines, clean_baselines, final_baselines

        except Exception as e:
            self.console.append(f"Error in baseline detection: {str(e)}\n")
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

    def _save_image_array(self, image, name):
        """Save intermediate image as NumPy array (.npy file)
        
        Args:
            image: NumPy array containing the image
            name: File name for the image
        """
        try:
            # Create raw directory if it doesn't exist
            save_dir = os.path.join(self.work_dir, "raw")
            os.makedirs(save_dir, exist_ok=True)
            
            # Save the NumPy array
            file_path = os.path.join(save_dir, f"{name}.npy")
            np.save(file_path, image)
            
            self.console.append(f"Saved {name} to {file_path}\n")
        except Exception as e:
            self.console.setTextColor(Qt.red)
            self.console.append(f"Error saving image {name}: {e}\n")
            self.console.setTextColor(Qt.black)

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
            
            self.console.append(f"Saved {name} baselines to {file_path}\n")
        except Exception as e:
            self.console.setTextColor(Qt.red)
            self.console.append(f"Error saving baselines {name}: {e}\n")
            self.console.setTextColor(Qt.black)