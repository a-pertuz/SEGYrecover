"""Data processing functionality for SEGYRecover."""

import os
import numpy as np
from scipy.interpolate import interp1d

class DataProcessor:
    """Handles data resampling and filtering"""
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir

    def resample_data(self, data, old_times, new_times):
        """
        Resample data to new time axis using linear interpolation.
        """
        self.console.append("Resampling traces...\n")        
        self.progress.start("Resampling traces...", data.shape[1])

        try:
            resampled = np.zeros((len(new_times), data.shape[1]))
            
            for i in range(data.shape[1]):
                resample_func = interp1d(
                    old_times, 
                    data[:, i], 
                    bounds_error=False, 
                    fill_value=0
                )
                resampled[:, i] = resample_func(new_times)
                self.progress.update(i)
                
                if self.progress.wasCanceled():
                    return None

            self._save_array(resampled, "resampled")

            self.progress.finish()
            return resampled
            
        except Exception as e:
            self.console.append(f"Error resampling data: {str(e)}\n")
            return None

    def filter_data(self, data, dt, f1, f2, f3, f4):
        """
        Apply bandpass filter to data using FFT. 
        Frequency values (F1, F2, F3, F4) are in Hz.
        """
        self.console.append("Filtering trace amplitude...\n")
        self.progress.start("Filtering amplitude...", data.shape[1])

        try:
            # Calculate sampling frequency
            fs = 1 / (dt / 1000)
            filtered = np.zeros_like(data)
            
            # Process each trace
            for i in range(data.shape[1]):
                signal = data[:, i]
                filtered[:, i] = self._apply_bandpass(signal, fs, f1, f2, f3, f4)
                self.progress.update(i)
                
                if self.progress.wasCanceled():
                    return None
                    
            # Fix NaN traces by interpolating from neighbors
            filtered = self._fix_nan_traces(filtered)
            
            self._save_array(filtered, "filtered")

            self.progress.finish()
            return filtered
            
        except Exception as e:
            self.console.append(f"Error filtering data: {str(e)}\n")
            return None

    def _apply_bandpass(self, signal, fs, f1, f2, f3, f4):
        """Apply bandpass filter to single trace"""
        # Calculate frequency components
        freqs = np.fft.fftfreq(len(signal), 1/fs)
        fft_signal = np.fft.fft(signal)
        
        # Create filter response
        filter_response = np.zeros_like(freqs)
        
        # High-pass filter
        for j in range(len(freqs)):
            if freqs[j] < f1:
                filter_response[j] = 0
            elif f1 <= freqs[j] <= f2:
                filter_response[j] = (freqs[j] - f1) / (f2 - f1)
            else:
                filter_response[j] = 1
                
        # Low-pass filter
        for j in range(len(freqs)):
            if freqs[j] > f4:
                filter_response[j] = 0
            elif f3 <= freqs[j] <= f4:
                filter_response[j] *= (f4 - freqs[j]) / (f4 - f3)
        
        # Apply filter and inverse FFT
        filtered_fft = fft_signal * filter_response
        return np.fft.ifft(filtered_fft).real

    def _fix_nan_traces(self, data):
        """Interpolate NaN traces from neighboring traces"""
        for i in range(data.shape[1]):
            if np.isnan(data[:, i]).any():
                # Find nearest non-NaN traces
                left_idx = i - 1
                right_idx = i + 1
                
                while left_idx >= 0 and np.isnan(data[:, left_idx]).any():
                    left_idx -= 1
                while right_idx < data.shape[1] and np.isnan(data[:, right_idx]).any():
                    right_idx += 1
                
                # Interpolate if valid neighbors found
                if left_idx >= 0 and right_idx < data.shape[1]:
                    data[:, i] = (data[:, left_idx] + data[:, right_idx]) / 2
                elif left_idx >= 0:  # Only left neighbor available
                    data[:, i] = data[:, left_idx]
                elif right_idx < data.shape[1]:  # Only right neighbor available
                    data[:, i] = data[:, right_idx]
                    
        return data

    def _save_array(self, array, name):
            """Save intermediate amplitude data as NumPy array (.npy file)
            
            Args:
                array: NumPy array containing the amplitude data
                name: File name for the array
            """
            try:
                # Save the NumPy array to the raw folder
                save_dir = os.path.join(self.work_dir, "raw")
                os.makedirs(save_dir, exist_ok=True)

                file_path = os.path.join(save_dir, f"{name}.npy")
                np.save(file_path, array)
                
                self.console.append(f"Saved {name} to {file_path}\n")
            except Exception as e:
                self.console.append(f"Error saving array {name}: {str(e)}\n")