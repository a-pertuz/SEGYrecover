# SegyRecover Core Module

This document provides an overview of the core components in the SegyRecover package, which is designed for processing seismic image data and converting it back to SEGY format.

## Module Structure

The core module contains the following main classes:

- **ImageProcessor**: Processes seismic section images through various algorithms.

- **AmplitudeExtractor**: Extracts and processes amplitude information from seismic images.

- **DataProcessor**: Handles data resampling and filtering operations.

- **SegyFileWriter**: Creates and writes SEGY format files from processed data.

## ImageProcessor

The `ImageProcessor` class provides tools for processing seismic images, particularly focusing on detecting and manipulating baselines and timelines in seismic data visualizations.

### Key Methods

#### Main Processing Methods

- **remove_timelines(image_a, HE, HLT)**: Removes horizontal timeline elements from seismic images.
  - Parameters:
    - `image_a`: Input image array
    - `HE`: Erosion parameter
    - `HLT`: Horizontal line thickness
  - Returns: Processed image with timelines removed and mask of timeline positions

- **detect_baselines(image_g, TLT, BDB, BDE, BFT)**: Detects vertical baselines in the image.
  - Parameters:
    - `image_g`: Input image (typically output from remove_timelines)
    - `TLT`: Timeline thickness parameter
    - `BDB`: Baseline detection begin row
    - `BDE`: Baseline detection end row
    - `BFT`: Baseline filtering threshold
  - Returns: Processed image and lists of raw, cleaned, and final baselines

#### Helper Methods

- **_detect_peaks(tr_per_col)**: Detects peaks in transition counts for baseline identification
- **_filter_baselines(baselines, tr_per_col, BFT)**: Filters out baselines that are too close together
- **_add_synthetic_baselines(baselines)**: Adds synthetic baselines in large gaps to maintain consistent spacing

#### Morphological Operations

- **_erosion_left(image, px)**: Applies erosion from left side
- **_erosion_right(image, px)**: Applies erosion from right side
- **_erosion_top(image, px)**: Applies erosion from top
- **_dilation_left(image, px)**: Applies dilation from left side
- **_dilation_right(image, px)**: Applies dilation from right side
- **_dilation_top(image, px)**: Applies dilation from top
- **_dilation_bottom(image, px)**: Applies dilation from bottom
- **_remove_vertical_segments(image, px)**: Removes vertical line segments

#### Utility Methods

- **_save_image_array(image, name)**: Saves processed image arrays for debugging/review
- **_save_baselines(baselines, name)**: Saves detected baseline positions


## AmplitudeExtractor

The `AmplitudeExtractor` class is responsible for extracting and processing amplitude information from seismic images.

### Key Methods

- **extract_amplitude(image, baselines)**: Extracts amplitude data between baseline positions.
  - Parameters:
    - `image`: Input processed image array
    - `baselines`: List of baseline positions
  - Returns: Array containing extracted amplitude data

- **process_amplitudes(amplitude)**: Processes raw amplitude data through multiple enhancement steps.
  - Parameters:
    - `amplitude`: Raw amplitude data array
  - Returns: Processed amplitude data array

#### Helper Methods

- **_subtract_trace_mean(amplitude)**: Subtracts the trace mean from all values in each trace
- **_interpolate_zeros(amplitude)**: Replaces zero values with interpolated ones
- **_handle_clipping(amplitude)**: Handles clipped amplitude values using Akima interpolation
- **_get_unclipped_indices(positive_mask)**: Identifies unclipped points for interpolation
- **_apply_smoothing(amplitude)**: Applies final smoothing using moving average
- **_save_array(array, name)**: Saves intermediate amplitude data as NumPy arrays


## DataProcessor

The `DataProcessor` class handles operations related to signal processing of seismic data.

### Key Methods

- **resample_data(data, old_times, new_times)**: Resamples data to new time axis using linear interpolation.
  - Parameters:
    - `data`: Input data array
    - `old_times`: Original time axis values
    - `new_times`: New time axis values to resample to
  - Returns: Resampled data array

- **filter_data(data, dt, f1, f2, f3, f4)**: Applies frequency filtering to seismic data.
  - Parameters:
    - `data`: Input data array
    - `dt`: Time sampling interval in milliseconds
    - `f1`, `f2`, `f3`, `f4`: Filter frequency corner points (for bandpass filter)
  - Returns: Filtered data array

#### Helper Methods

- **_apply_bandpass(signal, fs, f1, f2, f3, f4)**: Applies bandpass filter to a single trace
- **_fix_nan_traces(data)**: Interpolates NaN traces from neighboring traces
- **_save_array(array, name)**: Saves intermediate data as NumPy array files

## SegyFileWriter

The `SegyFileWriter` class manages the creation and writing of SEGY format seismic data files.

### Key Methods

- **assign_coordinates(base_name, baselines)**: Assigns geographic coordinates to traces.
  - Parameters:
    - `base_name`: Base name for geometry file
    - `baselines`: List of baseline positions
  - Returns: Array of interpolated coordinates for baselines

- **write_segy(data, baselines, image_path, DT, F1, F2, F3, F4)**: Creates and writes SEGY file.
  - Parameters:
    - `data`: Processed amplitude data
    - `baselines`: List of baseline positions
    - `image_path`: Path to original image
    - `DT`: Time sampling interval
    - `F1`, `F2`, `F3`, `F4`: Filter frequency corner points
  - Returns: Boolean indicating success or failure

#### Helper Methods

- **_get_coordinate_input(cdp, x, y)**: Gets user input for coordinate assignment
- **_interpolate_coordinates(cdp_i, cdp_f, cdp, x, y, n_baselines)**: Interpolates coordinates between CDP points


