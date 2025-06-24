"""Amplitude extraction functionality for SEGYRecover."""

import os
import numpy as np
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


    def extract_amplitude(self, image, baselines):
        """Extract amplitudes between consecutive baselines"""
        info_message(self.console, "Extracting trace amplitude...")
        self.progress.start("Extracting amplitude...", image.shape[0])

        try:
            black_pixel_mask = (image == 0)
            amplitude_list = []

            # Count black pixels between each pair of baselines
            for row in range(image.shape[0]):
                row_mask = black_pixel_mask[row]
                row_counts = [
                    np.sum(row_mask[baselines[i]:baselines[i + 1]]) * 100 
                    for i in range(len(baselines) - 1)
                ]
                row_counts.append(np.sum(row_mask[baselines[-1]:]) * 100)
                amplitude_list.append(row_counts)
                
                self.progress.update(row)

                if self.progress.wasCanceled():
                    return None

            amplitude = np.array(amplitude_list, dtype=float)

            #self._save_array(amplitude, "raw_amplitude")


            self.progress.finish()
            return amplitude

        except Exception as e:
            error_message(self.console, f"Error extracting amplitude: {str(e)}")
            return None

    def process_amplitudes(self, amplitude):
        """Process raw amplitude data through multiple steps"""
        try:
            # 1. Replace zeros with trace means
            processed = self._interpolate_zeros(amplitude)
            #processed = self._subtract_trace_mean(amplitude)
            #self._save_array(processed, "amplitude_zeros_interpolated")

            # 2. Handle clipped values
            processed = self._handle_clipping(processed)
            #self._save_array(processed, "amplitude_clipping_handled")

            # 3. Final smoothing
            processed = self._apply_smoothing(processed)
            #self._save_array(processed, "amplitude_final")

            
            return processed

        except Exception as e:
            error_message(self.console, f"Error processing amplitudes: {str(e)}")
            return None

    def _subtract_trace_mean(self, amplitude):
        """Subtract the trace mean from all values in the trace"""
        info_message(self.console, "Subtracting trace mean from all values...")
        self.progress.start("Subtracting trace mean...", amplitude.shape[1])

        try:
            processed = amplitude.copy()
            for i in range(processed.shape[1]):
                trace_mean = np.mean(processed[:, i])
                processed[:, i] -= trace_mean
                self.progress.update(i)

                if self.progress.wasCanceled():
                    return None

            self.progress.finish()
            return processed

        except Exception as e:
            error_message(self.console, f"Error subtracting trace mean: {str(e)}")
            return None

    def _interpolate_zeros(self, amplitude):
        """Replace zero values with trace means"""
        info_message(self.console, "Interpolating zero values...")
        self.progress.start("Interpolating zeros...", amplitude.shape[1])

        try:
            processed = amplitude.copy()
            trace_means = np.mean(processed, axis=0)

            for i in range(processed.shape[1]):
                zero_indices = processed[:, i] == 0
                processed[zero_indices, i] = -(2*trace_means[i])
                self.progress.update(i)
                
                if self.progress.wasCanceled():
                    return None

            self.progress.finish()
            return processed

        except Exception as e:
            error_message(self.console, f"Error interpolating zeros: {str(e)}")
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