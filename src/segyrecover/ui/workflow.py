"""Core workflow functions for SEGYRecover application."""

import os
import cv2
import numpy as np
from PySide6.QtWidgets import QMessageBox


from .app_dialogs import ParameterDialog, TimelineBaselineWindow, ROIManager
from .image_viewer import display_segy_results, display_amplitude_spectrum
from ..core.image_processor import ImageProcessor
from ..core.amplitude_extractor import AmplitudeExtractor
from ..core.data_processor import DataProcessor
from ..core.segy_writer import SegyFileWriter
from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message,
    summary_statistics
)

# Module-level variables to store processor instances
image_processor = None
amplitude_extractor = None
data_processor = None
segy_writer = None
roi_manager = None

def initialize(progress_bar, console, work_dir, image_canvas):
    """Initialize the workflow module with required components."""
    global image_processor, amplitude_extractor, data_processor, segy_writer, roi_manager
    
    # Initialize processors
    image_processor = ImageProcessor(progress_bar, console, work_dir)
    amplitude_extractor = AmplitudeExtractor(progress_bar, console, work_dir)
    data_processor = DataProcessor(progress_bar, console, work_dir)
    segy_writer = SegyFileWriter(progress_bar, console, work_dir)
    
    
    # Initialize ROI manager with default values
    roi_manager = ROIManager(
        parent=progress_bar.parent().parent(),
        console=console,
        image_canvas=image_canvas,
        work_dir=work_dir,
        trace_p1=0, trace_p2=0, trace_p3=0,
        twt_p1=0, twt_p2=0, twt_p3=0
    )
    
    return roi_manager

def load_image(main_window):
    """Handle image loading through ImageLoader."""
    section_header(main_window.console, "IMAGE LOADING")
    if main_window.image_loader.load_image():
        main_window.image_path = main_window.image_loader.image_path
        main_window.img_array = main_window.image_loader.img_array
        main_window.image_canvas = main_window.image_loader.image_canvas
        
        # Update the ROI manager with the new canvas
        global roi_manager
        roi_manager.image_canvas = main_window.image_canvas
        
        main_window.plot_location_canvas = main_window.image_loader.plot_location_canvas
        main_window.param_button.setEnabled(True)
        
        # Add image information
        height, width = main_window.img_array.shape
        file_size = os.path.getsize(main_window.image_path) / (1024 * 1024)  # Size in MB
        success_message(main_window.console, f"Image loaded: {os.path.basename(main_window.image_path)}")
        info_message(main_window.console, f"Dimensions: {width}x{height} pixels")
        info_message(main_window.console, f"File size: {file_size:.2f} MB")


def input_parameters(main_window):
    """Open a dialog to input, validate and save processing parameters."""
    if not main_window.image_path:
        warning_message(main_window.console, "Please load an image first.")
        QMessageBox.warning(main_window, "Warning", "Please load an image first.")
        return

    section_header(main_window.console, "PARAMETER CONFIGURATION")

    # Setup paths
    base_name = os.path.splitext(os.path.basename(main_window.image_path))[0]
    parameters_dir = os.path.join(main_window.work_dir, "PARAMETERS")
    parameters_path = os.path.join(parameters_dir, f"{base_name}.par")

    # Create parameter dialog
    dialog = ParameterDialog(main_window)

    try:
        # Load existing parameters with defaults
        default_params = {
            "Trace_P1": "0", "TWT_P1": "0",
            "Trace_P2": "0", "TWT_P2": "0",
            "Trace_P3": "0", "TWT_P3": "0",
            "DT": "1", 
            "F1": "10", "F2": "12", "F3": "70", "F4": "80",
            "TLT": "1", "HLT": "1", "HE": "50", "BDB": "5", "BDE": "100", "BFT": "80"
        }

        params = default_params.copy()
        if os.path.exists(parameters_path):
            with open(parameters_path, "r") as f:
                file_params = dict(line.split('\t') for line in f if '\t' in line)
                params.update({k: v.strip() for k,v in file_params.items()})

        # Set dialog values
        for param, value in params.items():
            if hasattr(dialog, param):
                getattr(dialog, param).setText(value)

        if dialog.exec():
            # Validate parameters
            try:
                param_values = {
                    "Trace_P1": int(dialog.Trace_P1.text()),
                    "TWT_P1": int(dialog.TWT_P1.text()),
                    "Trace_P2": int(dialog.Trace_P2.text()), 
                    "TWT_P2": int(dialog.TWT_P2.text()),
                    "Trace_P3": int(dialog.Trace_P3.text()),
                    "TWT_P3": int(dialog.TWT_P3.text()),
                    "DT": int(dialog.DT.text()),
                    "F1": int(dialog.F1.text()),
                    "F2": int(dialog.F2.text()),
                    "F3": int(dialog.F3.text()),
                    "F4": int(dialog.F4.text()),
                    "TLT": int(dialog.TLT.text()),
                    "HLT": int(dialog.HLT.text()),
                    "HE": int(dialog.HE.text()),
                    "BDB": int(dialog.BDB.text()),
                    "BDE": int(dialog.BDE.text()),
                    "BFT": int(dialog.BFT.text())                
                }

                # Validate parameter relationships
                validations = [
                    (param_values["DT"] > 0, "Sample rate must be > 0"),
                    (param_values["F4"] > param_values["F3"], "F4 must be > F3"),
                    (param_values["F3"] > param_values["F2"], "F3 must be > F2"), 
                    (param_values["F2"] > param_values["F1"], "F2 must be > F1"),
                    (param_values["F1"] > 0, "F1 must be > 0"),
                    (param_values["TWT_P3"] > param_values["TWT_P1"], "TWT_P3 must be > TWT_P1"),
                    (param_values["BDB"] < param_values["BDE"], "BDB must be < BDE"),
                    (param_values["BDB"] >= 0, "BDB must be >= 0"),
                    (param_values["BFT"] >= 0 and param_values["BFT"] <= 100, "BFT must be between 0 and 100"),
                    (param_values["TLT"] > 0, "Timeline thickness must be > 0"),
                    (param_values["HLT"] > 0, "Horizontal line thickness must be > 0"),
                    (param_values["HE"] > 0, "Horizontal erosion must be > 0"),
                    (param_values["Trace_P1"] >= 0, "Trace_P1 must be >= 0"),
                    (param_values["Trace_P2"] >= 0, "Trace_P2 must be >= 0"),
                    (param_values["Trace_P3"] >= 0, "Trace_P3 must be >= 0")
                ]

                for condition, message in validations:
                    if not condition:
                        raise ValueError(message)

                # Save parameters
                os.makedirs(parameters_dir, exist_ok=True)
                with open(parameters_path, "w") as f:
                    for param, value in param_values.items():
                        f.write(f"{param}\t{value}\n")

                # Update main window attributes for reference
                for param, value in param_values.items():
                    setattr(main_window, param, value)

                # Update console output with formatting
                section_header(main_window.console, f"PARAMETERS FOR {base_name}")
                
                # Group parameters by category for better readability
                param_categories = {
                    "Trace & Time Mapping": ["Trace_P1", "TWT_P1", "Trace_P2", "TWT_P2", "Trace_P3", "TWT_P3", "DT"],
                    "Frequency Filter": ["F1", "F2", "F3", "F4"],
                    "Detection Settings": ["TLT", "HLT", "HE", "BDB", "BDE", "BFT"]
                }
                
                for category, params in param_categories.items():
                    main_window.console.append(f"\n• {category}:")
                    for param in params:
                        if hasattr(main_window, param):
                            value = getattr(main_window, param)
                            main_window.console.append(f"  - {param}: {value}")
                
                main_window.console.append(f"\n")
                success_message(main_window.console, f"Parameters saved: {parameters_path}")

                # Show next steps
                QMessageBox.information(main_window, "Parameters Set",
                    "<p><b>Parameters saved successfully.</b></p>")

                main_window.begin_digitization_button.setEnabled(True)
                
                # Update our module ROI manager with new parameters
                global roi_manager
                roi_manager = ROIManager(
                    main_window,
                    main_window.console, 
                    main_window.image_canvas,
                    main_window.work_dir,
                    param_values["Trace_P1"], param_values["Trace_P2"], param_values["Trace_P3"],
                    param_values["TWT_P1"], param_values["TWT_P2"], param_values["TWT_P3"]
                )

            except ValueError as e:
                error_message(main_window.console, str(e))
                QMessageBox.critical(main_window, "Invalid Parameters", str(e))
                return

    except Exception as e:
        error_message(main_window.console, f"Error processing parameters: {str(e)}")
        QMessageBox.critical(main_window, "Error", 
            f"Failed to process parameters: {str(e)}")


def select_area(main_window):
    """Handle ROI selection process."""
    if not main_window.image_path:
        warning_message(main_window.console, "Please load an image first")
        QMessageBox.warning(main_window, "Warning", "Please load an image first.")
        return

    section_header(main_window.console, "ROI SELECTION")
    info_message(main_window.console, "Select the four corner points of your seismic section")
    info_message(main_window.console, "Order: Top-Left, Top-Right, Bottom-Left")

    # Start ROI selection process using our module ROI manager
    global roi_manager
    selected = roi_manager.select_roi(main_window.image_path, main_window.img_array)
    if selected:
        main_window.points = roi_manager.get_points()
        success_message(main_window.console, "ROI selection completed successfully")
        crop_seismic_section(main_window)
    else:
        warning_message(main_window.console, "ROI selection cancelled or failed")


def crop_seismic_section(main_window):
    """Crop the seismic section based on the selected points."""
    section_header(main_window.console, "IMAGE RECTIFICATION")
    
    if len(main_window.points) == 4 and main_window.img_array is not None:
        info_message(main_window.console, "Calculating perspective transformation")
        
        pts1 = np.float32(main_window.points)
        width = int(np.linalg.norm(np.array(main_window.points[0]) - np.array(main_window.points[1])))
        height = int(np.linalg.norm(np.array(main_window.points[0]) - np.array(main_window.points[2])))
        pts2 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        main_window.rectified_image = cv2.warpPerspective(main_window.img_array, matrix, (width, height))

        # Convert the rectified image to binary (0 or 255)
        _, main_window.binary_rectified_image = cv2.threshold(main_window.rectified_image, 128, 255, cv2.THRESH_BINARY)

        ax = main_window.image_canvas.figure.axes[0]
        ax.clear()
        ax.imshow(main_window.binary_rectified_image, cmap='gray')
        main_window.image_canvas.draw()

        success_message(main_window.console, "Seismic section cropped and rectified")
        info_message(main_window.console, f"New dimensions: {width}x{height} pixels")

        main_window.load_button.setEnabled(False)
        main_window.param_button.setEnabled(False)

        digitize_segy(main_window)
    else:
        error_message(main_window.console, "Invalid ROI points for rectification")


def digitize_segy(main_window):
    """Process seismic data through all steps to create SEGY file."""
    section_header(main_window.console, "DIGITIZATION PROCESS")
    
    try:
        # Use our module-level processors
        global image_processor, amplitude_extractor, data_processor, segy_writer

        # 1. Remove timelines
        info_message(main_window.console, "Step 1/5: Removing timelines")

        image_g, image_f = image_processor.remove_timelines(
            main_window.binary_rectified_image,
            main_window.HE,
            main_window.HLT
        )
        if image_g is None:
            error_message(main_window.console, "Timeline removal failed")
            return
        
        # 2. Detect baselines
        info_message(main_window.console, "Step 2/5: Detecting baselines")

        image_m, raw_baselines, clean_baselines, final_baselines = image_processor.detect_baselines(
            image_g,
            main_window.TLT,
            main_window.BDB,
            main_window.BDE,
            main_window.BFT
        )
        if image_m is None:
            error_message(main_window.console, "Baseline detection failed")
            return
        
        # Add statistics for baselines
        info_message(main_window.console, f"Raw baselines detected: {len(raw_baselines)}")
        info_message(main_window.console, f"Clean baselines after filtering: {len(clean_baselines)}")
        info_message(main_window.console, f"Final baselines: {len(final_baselines)}")
        
        # Show verification window
        timeline_baseline_window = TimelineBaselineWindow(
            main_window.binary_rectified_image, 
            image_f, 
            image_g, 
            image_m, 
            raw_baselines, 
            clean_baselines,
            final_baselines,
            main_window.BDB, 
            main_window.BDE)
            
        result = timeline_baseline_window.exec()

        if result != QMessageBox.Accepted:
            warning_message(main_window.console, "Process cancelled by user")
            main_window.restart_process()
            warning_message(main_window.console, "Try setting new parameters")
            return

        # 3. Extract amplitudes
        info_message(main_window.console, "Step 3/5: Extracting amplitudes")

        raw_amplitude = amplitude_extractor.extract_amplitude(
            image_g, 
            final_baselines
        )
        if raw_amplitude is None:
            error_message(main_window.console, "Failed to extract amplitude")
            return
        
        processed_amplitude = amplitude_extractor.process_amplitudes(
            raw_amplitude
        )
        if processed_amplitude is None:
            error_message(main_window.console, "Failed to process amplitude")
            return
        
        # 4. Resample and filter
        info_message(main_window.console, "Step 4/5: Resampling and filtering data")

        old_times = np.linspace(main_window.TWT_P1, main_window.TWT_P3, processed_amplitude.shape[0])
        new_times = np.arange(main_window.TWT_P1, main_window.TWT_P3 + main_window.DT, main_window.DT)
        
        resampled = data_processor.resample_data(
            processed_amplitude,
            old_times,
            new_times
        )
        if resampled is None:
            error_message(main_window.console, "Failed to resample data")
            return

        info_message(main_window.console, f"Resampled from {processed_amplitude.shape[0]} to {resampled.shape[0]} samples")
        
        filtered = data_processor.filter_data(
            resampled,
            main_window.DT,
            main_window.F1,
            main_window.F2,
            main_window.F3,
            main_window.F4
        )
        if filtered is None:
            error_message(main_window.console, "Failed to filter data")
            return
        
        # 5. Create SEGY
        info_message(main_window.console, "Step 5/5: Creating SEGY file")
        
        base_name = os.path.splitext(os.path.basename(main_window.image_path))[0]
        segy_path = os.path.join(main_window.work_dir, "SEGY", f"{base_name}.segy")
        
        if not segy_writer.write_segy(
            filtered,
            final_baselines,
            main_window.image_path,
            main_window.DT,
            main_window.F1,
            main_window.F2,
            main_window.F3,
            main_window.F4
        ):
            error_message(main_window.console, "Failed to create SEGY file")
            return

        # 6. Display results and summary statistics
        success_message(main_window.console, "Digitization completed successfully!")
        summary_statistics(main_window.console, {
            "Traces": filtered.shape[1],
            "Samples per trace": filtered.shape[0],
            "Sample rate": f"{main_window.DT} ms",
            "Time range": f"{main_window.TWT_P1} - {main_window.TWT_P3} ms",
            "Filter applied": f"{main_window.F1}-{main_window.F2}-{main_window.F3}-{main_window.F4} Hz",
            "Output file": segy_path,
            "File size": f"{os.path.getsize(segy_path) / (1024*1024):.2f} MB"
        })
        
        display_results(main_window, filtered, segy_path)
        
    except Exception as e:
        error_message(main_window.console, f"Digitization failed: {str(e)}")
        main_window.restart_process()


def display_results(main_window, filtered_data, segy_path):
    """Display SEGY section and amplitude spectrum."""
    section_header(main_window.console, "RESULTS DISPLAY")
    
    try:
        # Display SEGY section
        info_message(main_window.console, "Displaying SEGY section")
        seis_window = display_segy_results(segy_path, main_window)
        
        # Display amplitude spectrum
        info_message(main_window.console, "Generating amplitude spectrum")
        spectrum_window = display_amplitude_spectrum(filtered_data, main_window.DT, main_window)
        
        if seis_window and spectrum_window:
            success_message(main_window.console, "Results displayed successfully")
            info_message(main_window.console, "The SEGY file can now be used in interpretation software")
        else:
            warning_message(main_window.console, "Some results could not be displayed")
            
    except Exception as e:
        error_message(main_window.console, f"Error displaying results: {str(e)}")

