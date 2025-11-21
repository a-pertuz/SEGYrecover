"""Amplitude extraction functionality for SEGYRecover."""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import Akima1DInterpolator
from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message
)
class AmplitudeExtractor:
    """Handles amplitude extraction and processing from seismic images"""
    
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir
        # Store intermediate results for visualization
        self.intermediate_results = {}

    def extract_amplitude(self, image, baselines):
        """
        Extract amplitudes between consecutive baselines with negative amplitude handling:
        - If baseline is on WHITE pixel:
          - Check next pixel to the right
          - If next is also WHITE: count WHITE pixels to the LEFT until black or previous baseline
          - If next is BLACK: count black pixels to the right until white or next baseline
        - If baseline is on BLACK pixel: count black pixels to the right as before
        """
        info_message(self.console, "Extracting trace amplitude with full white pixel handling...")
        self.progress.start("Extracting amplitude...", image.shape[0])

        try:
            black_pixel_mask = (image == 0)
            amplitude_list = []

            # Count pixels between consecutive baselines
            for row in range(image.shape[0]):
                row_counts = []
                
                for i in range(len(baselines) - 1):
                    baseline_col = baselines[i]
                    next_baseline_col = baselines[i + 1]
                    prev_baseline_col = baselines[i - 1] if i > 0 else 0
                    
                    if baseline_col >= image.shape[1]:
                        row_counts.append(0)
                        continue
                    
                    # Check if baseline is on BLACK or WHITE pixel
                    if image[row, baseline_col] == 0:  # BLACK pixel
                        # Count black pixels between baselines (positive amplitude)
                        count = np.sum(black_pixel_mask[row, baseline_col:next_baseline_col]) * 100
                        row_counts.append(count)
                    else:  # WHITE pixel
                        # Check next pixel to the right
                        if baseline_col + 1 < image.shape[1]:
                            next_pixel = image[row, baseline_col + 1]
                            
                            if next_pixel == 255:  # Next is also WHITE (negative amplitude)
                                # Count WHITE pixels to the LEFT until black or previous baseline
                                count = 0
                                col = baseline_col
                                
                                while col > prev_baseline_col and col >= 0:
                                    if image[row, col] == 255:  # WHITE pixel
                                        count += 1
                                        col -= 1
                                    else:  # BLACK pixel found
                                        # Check if black is followed by white to the left
                                        if col - 1 >= prev_baseline_col and image[row, col - 1] == 255:
                                            # Black followed by white, continue counting
                                            col -= 1
                                        else:
                                            # Black not followed by white, stop counting
                                            break
                                
                                # Negative amplitude for white pixels
                                row_counts.append(-count * 100)
                            else:  # Next is BLACK (positive amplitude)
                                # Count black pixels to the RIGHT until white or next baseline
                                count = 0
                                col = baseline_col + 1
                                
                                while col < next_baseline_col and col < image.shape[1]:
                                    if image[row, col] == 0:  # BLACK pixel
                                        count += 1
                                        col += 1
                                    else:  # WHITE pixel found
                                        # Check if white is followed by black
                                        if col + 1 < image.shape[1] and image[row, col + 1] == 0:
                                            # White followed by black, continue counting
                                            col += 1
                                        else:
                                            # White not followed by black, stop counting
                                            break
                                
                                row_counts.append(count * 100)
                        else:
                            row_counts.append(0)
                
                # Duplicate the last trace to maintain original trace count
                if len(row_counts) > 0:
                    row_counts.append(row_counts[-1])
                
                amplitude_list.append(row_counts)
                
                self.progress.update(row)

                if self.progress.wasCanceled():
                    return None

            amplitude = np.array(amplitude_list, dtype=float)
            info_message(self.console, f"Extracted amplitude shape: {amplitude.shape}")

            self.progress.finish()
            return amplitude

        except Exception as e:
            error_message(self.console, f"Error extracting amplitude: {str(e)}")
            return None


    def process_amplitudes(self, amplitude):
        """Process raw amplitude data through multiple steps"""
        try:
            # Store raw amplitude for visualization
            #self.intermediate_results['raw'] = amplitude.copy()

            processed = amplitude.copy()

            # 1. Handle clipped values
            processed = self._handle_clipping(processed)
            #self._save_array(processed, "amplitude_clipping_handled")
            #self.intermediate_results['clipping_handled'] = processed.copy()

            # 2. Final smoothing
            processed = self._apply_smoothing(processed)
            #self._save_array(processed, "amplitude_final")
            #self.intermediate_results['final'] = processed.copy() 
            
            return processed

        except Exception as e:
            error_message(self.console, f"Error processing amplitudes: {str(e)}")
            return None


    def _handle_clipping(self, amplitude):
        """Handle clipped values using Akima interpolation"""
        info_message(self.console, "Interpolating clipped values...")
        self.progress.start("Handling clipping...", amplitude.shape[1])

        try:
            processed = amplitude.copy()
            akima_count = 0
            original_count = 0

            for i in range(amplitude.shape[1]):
                amp = amplitude[:, i]
                sample = np.arange(len(amp))
                positive_mask = (amp >= np.max(amp) * 0.99)
                
                if np.any(positive_mask):
                    unclipped_indices = self._get_unclipped_indices(positive_mask)
                    f_akima = Akima1DInterpolator(sample[unclipped_indices], amp[unclipped_indices])
                    akima_values = f_akima(sample)
                    
                    if not np.any(np.isnan(akima_values)):
                        processed[:, i] = akima_values
                        akima_count += 1
                    else:
                        original_count += 1

                self.progress.update(i)
                if self.progress.wasCanceled():
                    return None

            info_message(self.console, f"Traces interpolated using Akima: {akima_count}")
            info_message(self.console, f"Traces kept original: {original_count}\n")

            self.progress.finish()
            return processed

        except Exception as e:
            error_message(self.console, f"Error handling clipping: {str(e)}")
            return None

    def _get_unclipped_indices(self, positive_mask):
        """Helper method to get indices for unclipped values"""
        transitions = np.where(np.diff(positive_mask.astype(int)) != 0)[0]
        unclipped_indices = []
        
        # Handle edge cases
        if positive_mask[0]:
            transitions = np.insert(transitions, 0, 0)
        if positive_mask[-1]:
            transitions = np.append(transitions, len(positive_mask)-1)
            
        # Add points around transitions
        for idx in transitions:
            if idx > 0:
                unclipped_indices.append(idx)
            if idx < len(positive_mask)-1:
                unclipped_indices.append(idx+1)
        
        # Add all unclipped points
        unclipped_indices.extend(np.where(~positive_mask)[0])
        return np.unique(unclipped_indices)

    def _apply_smoothing(self, amplitude):
        """Apply final smoothing using moving average"""
        window_size = 5
        kernel = np.ones(window_size) / window_size
        processed = amplitude.copy()

        for i in range(amplitude.shape[1]):
            processed[:, i] = np.convolve(amplitude[:, i], kernel, mode='same')

        info_message(self.console, "Applying final smoothing...")

        return processed

 
    def _save_array(self, array, name):
        """Save intermediate amplitude data as NumPy array (.npy file)        """
        try:
            # Save the NumPy array to the raw folder
            save_dir = os.path.join(self.work_dir, "raw")
            os.makedirs(save_dir, exist_ok=True)

            file_path = os.path.join(save_dir, f"{name}.npy")
            np.save(file_path, array)
            
            info_message(self.console, f"Saved {name} to {file_path}")
        except Exception as e:
            error_message(self.console, f"Error saving array {name}: {str(e)}")

    