"""Amplitude processing functionality for SEGYRecover."""

import os
import numpy as np
from scipy.interpolate import interp1d
from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message
)
class DataProcessor:
    """Handles data resampling and filtering"""
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir

    def resample_data(self, data, old_times, new_times):
        """ Resample data to new time axis using linear interpolation."""
        
        info_message(self.console, "Resampling traces...")
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
                    error_message(self.console, "Resampling canceled by user.")
                    return None

            #self._save_array(resampled, "resampled")

            self.progress.finish()
            success_message(self.console, "Resampling completed successfully.")
            return resampled
            
        except Exception as e:
            error_message(self.console, f"Error resampling data: {str(e)}")
            return None

    def filter_data(self, data, params):
        """
        Apply bandpass filter to data.
        If params["TVF_ENABLED"] == 1, use time-variant bandpass with Hann taper blending.
        Otherwise, use classic F1–F4 filtering.
        """
        info_message(self.console, "Filtering trace amplitude...")
        self.progress.start("Filtering amplitude...", data.shape[1])

        try:
            dt = params["DT"]  # ms
            fs = 1 / (dt / 1000)
            n_samples, n_traces = data.shape

            if params.get("TVF_ENABLED", 0) != 1:
                info_message(self.console, "Applying bandpass filter to all traces...")
                # Classic filtering
                f1, f2, f3, f4 = params["F1"], params["F2"], params["F3"], params["F4"]
                filtered = np.zeros_like(data)
                for i in range(n_traces):
                    signal = data[:, i]
                    filtered[:, i] = self._apply_bandpass(signal, fs, f1, f2, f3, f4)
                    self.progress.update(i)
                    if self.progress.wasCanceled():
                        error_message(self.console, "Filtering canceled by user.")
                        return None
                filtered = self._fix_nan_traces(filtered)
                self.progress.finish()
                success_message(self.console, "Filtering completed successfully.")
                return filtered

            # --- Time-variant filtering ---
            intervals = self._parse_tvf_intervals(params)
            if not intervals:
                info_message(self.console, "No TVF intervals found, falling back to classic filtering.")
                # fallback to classic
                f1, f2, f3, f4 = params["F1"], params["F2"], params["F3"], params["F4"]
                filtered = np.zeros_like(data)
                for i in range(n_traces):
                    signal = data[:, i]
                    filtered[:, i] = self._apply_bandpass(signal, fs, f1, f2, f3, f4)
                    self.progress.update(i)
                    if self.progress.wasCanceled():
                        error_message(self.console, "Filtering canceled by user.")
                        return None
                filtered = self._fix_nan_traces(filtered)
                self.progress.finish()
                success_message(self.console, "Filtering completed successfully.")
                return filtered

            info_message(self.console, "Applying time-variant bandpass filter to all traces...")
            # Prepare time axis (ms)
            times = np.arange(n_samples) * dt

            # Compute midpoints for blending
            mids = [ (iv["T1"] + iv["T2"]) / 2 for iv in intervals ]

            filtered = np.zeros_like(data)
            for i in range(n_traces):
                signal = data[:, i]
                interval_filtered = []
                # Apply bandpass filter for each interval
                for iv in intervals:
                    interval_filtered.append(self._apply_bandpass(signal, fs, iv["F1"], iv["F2"], iv["F3"], iv["F4"]))
                # Blend filtered traces using Hann taper
                filtered[:, i] = self._blend_tvf(signal, times, intervals, mids, interval_filtered, classic_filt=None)
                self.progress.update(i)
                if self.progress.wasCanceled():
                    error_message(self.console, "Filtering canceled by user.")
                    return None

            filtered = self._fix_nan_traces(filtered)
            self.progress.finish()
            success_message(self.console, "Time-variant filtering completed successfully.")
            return filtered

        except Exception as e:
            error_message(self.console, f"Error filtering data: {str(e)}")
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
            """Save intermediate amplitude data as NumPy array (.npy file) """
            try:
                # Save the NumPy array to the raw folder
                save_dir = os.path.join(self.work_dir, "raw")
                os.makedirs(save_dir, exist_ok=True)

                file_path = os.path.join(save_dir, f"{name}.npy")
                np.save(file_path, array)
                
                self.console.append(f"Saved {name} to {file_path}\n")
            except Exception as e:
                self.console.append(f"Error saving array {name}: {str(e)}\n")

    def _parse_tvf_intervals(self, params):
        """Parse TVF intervals from params dict, return sorted list of dicts with T1,T2,F1,F2,F3,F4."""
        intervals = []
        i = 1
        while True:
            key_t1 = f"TVF_{i}_T1"
            key_t2 = f"TVF_{i}_T2"
            key_f1 = f"TVF_{i}_F1"
            key_f2 = f"TVF_{i}_F2"
            key_f3 = f"TVF_{i}_F3"
            key_f4 = f"TVF_{i}_F4"
            if key_t1 in params and key_t2 in params and key_f1 in params and key_f2 in params and key_f3 in params and key_f4 in params:
                intervals.append({
                    "T1": params[key_t1],
                    "T2": params[key_t2],
                    "F1": params[key_f1],
                    "F2": params[key_f2],
                    "F3": params[key_f3],
                    "F4": params[key_f4],
                })
                i += 1
            else:
                break
        # Sort by T1
        intervals.sort(key=lambda iv: iv["T1"])
        return intervals

    def _blend_tvf(self, signal, times, intervals, mids, interval_filtered, classic_filt):
        """
        Blend filtered traces using Hann taper between intervals.
        signal: original trace
        times: array of sample times (ms)
        intervals: list of interval dicts
        mids: list of midpoints
        interval_filtered: list of filtered traces for each interval
        classic_filt: classic filtered trace for uncovered regions (or None)
        Returns: blended trace (1D array)
        """
        n = len(signal)
        out = np.zeros(n)
        n_iv = len(intervals)

        # Assign each sample to a region
        for idx, t in enumerate(times):
            if n_iv == 1:
                # Only one interval: use its filter
                out[idx] = interval_filtered[0][idx]
            elif t < mids[0]:
                # Before first midpoint: use first interval
                out[idx] = interval_filtered[0][idx]
            elif t >= mids[-1]:
                # After last midpoint: use last interval
                out[idx] = interval_filtered[-1][idx]
            else:
                # Between midpoints: blend
                for j in range(n_iv - 1):
                    if mids[j] <= t < mids[j+1]:
                        x = (t - mids[j]) / (mids[j+1] - mids[j])
                        w = 0.5 * (1 - np.cos(np.pi * x))  # Hann window
                        out[idx] = (1 - w) * interval_filtered[j][idx] + w * interval_filtered[j+1][idx]
                        break
        return out