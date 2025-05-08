"""Digitization logic for SEGYRecover application."""

import os
import numpy as np

from ..core._1_image_processor import ImageProcessor
from ..core._2_amplitude_extractor import AmplitudeExtractor
from ..core._3_data_processor import DataProcessor
from ..core._4_segy_writer import SegyFileWriter
from ..utils.console_utils import (
    section_header, success_message, error_message, 
    warning_message, info_message, progress_message,
    summary_statistics
)

class DigitizationProcessor:
    """Handles the digitization processing workflow for seismic images."""
    
    def __init__(self, console, progress_bar, work_dir):
        """Initialize the processor with the necessary components."""
        self.console = console
        self.progress = progress_bar
        self.work_dir = work_dir
        
        # Initialize core processors
        self.image_processor = ImageProcessor(progress_bar, console, work_dir)
        self.amplitude_extractor = AmplitudeExtractor(progress_bar, console, work_dir)
        self.data_processor = DataProcessor(progress_bar, console, work_dir)
        self.segy_writer = SegyFileWriter(progress_bar, console, work_dir)
        
        # State variables
        self.image_path = None
        self.binary_rectified_image = None
        self.parameters = {}
        self.final_baselines = None
        self.filtered_data = None
        self.segy_path = None
        
        # Processing results
        self.processing_results = {
            'image_f': None,  # Timeline detection 
            'image_g': None,  # Image with timelines removed
            'image_m': None,  # Baseline detection
            'raw_amplitude': None,
            'processed_amplitude': None,
            'resampled_amplitude': None,
            'filtered_data': None
        }
    
    def set_data(self, image_path, binary_rectified_image, parameters):
        """Set the input data for processing."""
        self.image_path = image_path
        self.binary_rectified_image = binary_rectified_image
        self.parameters = parameters
        
        # Reset state
        self.final_baselines = None
        self.filtered_data = None
        self.segy_path = None
        
        # Reset processing results
        for key in self.processing_results:
            self.processing_results[key] = None
    
    def run_digitization(self, step_callback=None):
        """ Run the complete digitization process. """

        if not self._validate_inputs():
            return False
        
        section_header(self.console, "DIGITIZATION PROCESS")
        
        try:
            # Step 1: Remove timelines
            if not self._remove_timelines(step_callback):
                return False
            
            # Step 2: Detect baselines
            if not self._detect_baselines(step_callback):
                return False
            
            # Step 3: Extract amplitudes
            if not self._extract_amplitudes(step_callback):
                return False
            
            # Step 4: Process data
            if not self._process_data(step_callback):
                return False
            
            # Step 5: Create SEGY
            if not self._create_segy(step_callback):
                return False
            
            # Display completion summary
            self._display_completion_summary()
            
            return True
            
        except Exception as e:
            import traceback
            error_message(self.console, f"Digitization failed: {str(e)}")
            error_message(self.console, traceback.format_exc())
            return False
    
    def _validate_inputs(self):
        """Validate that we have all required inputs."""
        if not self.parameters or len(self.parameters) == 0:
            error_message(self.console, f"Missing parameters. Parameters dict: {self.parameters}")
            return False
            
        if self.binary_rectified_image is None:
            error_message(self.console, "Missing rectified image")
            return False
            
        return True
    
    def _remove_timelines(self, step_callback=None):
        """ Step 1: Remove timelines. """

        info_message(self.console, "Step 1/5: Removing timelines")
        
        image_g, image_f = self.image_processor.remove_timelines(
            self.binary_rectified_image,
            self.parameters["HE"],
            self.parameters["HLT"]
        )
        
        if image_g is None:
            error_message(self.console, "Timeline removal failed")
            return False
        
        # Store results
        self.processing_results['image_f'] = image_f
        self.processing_results['image_g'] = image_g
        
        # Call callback if provided
        if step_callback:
            step_callback(0, {'image_f': image_f, 'image_g': image_g})
        
        return True
    
    def _detect_baselines(self, step_callback=None):
        """ Step 2: Detect baselines."""

        info_message(self.console, "Step 2/5: Detecting baselines")
        
        # Make sure we have processed image from previous step
        if self.processing_results['image_g'] is None:
            error_message(self.console, "Can't detect baselines without processed image")
            return False
        
        image_m, raw_baselines, clean_baselines, final_baselines = self.image_processor.detect_baselines(
            self.processing_results['image_g'],
            self.parameters["TLT"],
            self.parameters["BDB"],
            self.parameters["BDE"],
            self.parameters["BFT"]
        )
        
        if image_m is None:
            error_message(self.console, "Baseline detection failed")
            return False
        
        # Add statistics for baselines
        info_message(self.console, f"Raw baselines detected: {len(raw_baselines)}")
        info_message(self.console, f"Clean baselines after filtering: {len(clean_baselines)}")
        info_message(self.console, f"Final baselines: {len(final_baselines)}")
        
        # Store results
        self.processing_results['image_m'] = image_m
        self.final_baselines = final_baselines
        
        # Call callback if provided
        if step_callback:
            step_callback(1, {'image_m': image_m, 'final_baselines': final_baselines})
        
        return True
    
    def _extract_amplitudes(self, step_callback=None):
        """ Step 3: Extract amplitudes. """

        info_message(self.console, "Step 3/5: Extracting amplitudes")
        
        # Make sure we have processed image and baselines from previous steps
        if self.processing_results['image_g'] is None or self.final_baselines is None:
            error_message(self.console, "Can't extract amplitudes without processed image and baselines")
            return False
        
        raw_amplitude = self.amplitude_extractor.extract_amplitude(
            self.processing_results['image_g'], 
            self.final_baselines
        )
        
        if raw_amplitude is None:
            error_message(self.console, "Failed to extract amplitude")
            return False
        
        processed_amplitude = self.amplitude_extractor.process_amplitudes(
            raw_amplitude
        )
        
        if processed_amplitude is None:
            error_message(self.console, "Failed to process amplitude")
            return False
        
        # Store results
        self.processing_results['raw_amplitude'] = raw_amplitude
        self.processing_results['processed_amplitude'] = processed_amplitude
        
        # Call callback if provided
        if step_callback:
            step_callback(2, {
                'raw_amplitude': raw_amplitude, 
                'processed_amplitude': processed_amplitude
            })
        
        return True
    
    def _process_data(self, step_callback=None):
        """ Step 4: Resample and filter data. """

        info_message(self.console, "Step 4/5: Resampling and filtering data")
        
        # Make sure we have processed amplitudes from previous step
        if self.processing_results['processed_amplitude'] is None:
            error_message(self.console, "Can't process data without processed amplitudes")
            return False
        
        processed_amplitude = self.processing_results['processed_amplitude']
        
        # Define time axes
        old_times = np.linspace(self.parameters["TWT_P1"], self.parameters["TWT_P3"], 
                              processed_amplitude.shape[0])
        new_times = np.arange(self.parameters["TWT_P1"], 
                            self.parameters["TWT_P3"] + self.parameters["DT"], 
                            self.parameters["DT"])
        
        # Resample data
        resampled = self.data_processor.resample_data(
            processed_amplitude,
            old_times,
            new_times
        )
        
        if resampled is None:
            error_message(self.console, "Failed to resample data")
            return False
        
        info_message(self.console, f"Resampled from {processed_amplitude.shape[0]} to {resampled.shape[0]} samples")
        
        # Filter data
        filtered_data = self.data_processor.filter_data(
            resampled,
            self.parameters["DT"],
            self.parameters["F1"],
            self.parameters["F2"],
            self.parameters["F3"],
            self.parameters["F4"]
        )
        
        if filtered_data is None:
            error_message(self.console, "Failed to filter data")
            return False
        
        # Store results
        self.processing_results['resampled_amplitude'] = resampled
        self.processing_results['filtered_data'] = filtered_data
        self.filtered_data = filtered_data
        
        # Call callback if provided
        if step_callback:
            step_callback(3, {
                'resampled_amplitude': resampled, 
                'filtered_data': filtered_data
            })
        
        return True
    
    def _create_segy(self, step_callback=None):
        """ Step 5: Create SEGY file."""

        info_message(self.console, "Step 5/5: Creating SEGY file")
        
        # Make sure we have filtered data from previous step
        if self.filtered_data is None:
            error_message(self.console, "Can't create SEGY without filtered data")
            return False
        
        # Create SEGY output path
        base_name = os.path.splitext(os.path.basename(self.image_path))[0]
        self.segy_path = os.path.join(self.work_dir, "SEGY", f"{base_name}.segy")
        
        # Write SEGY file
        if not self.segy_writer.write_segy(
            self.filtered_data,
            self.final_baselines,
            self.image_path,
            self.parameters["DT"],
            self.parameters["F1"],
            self.parameters["F2"],
            self.parameters["F3"],
            self.parameters["F4"]
        ):
            error_message(self.console, "Failed to create SEGY file")
            return False
        
        # Call callback if provided
        if step_callback:
            step_callback(4, {'segy_path': self.segy_path})
        
        success_message(self.console, "Digitization completed successfully!")
        
        return True
    
    def _display_completion_summary(self):
        """Display a summary of the digitization results."""
        if self.filtered_data is None or self.segy_path is None:
            return
            
        # Display summary statistics
        summary_statistics(self.console, {
            "Traces": self.filtered_data.shape[1],
            "Samples per trace": self.filtered_data.shape[0],
            "Sample rate": f"{self.parameters['DT']} ms",
            "Time range": f"{self.parameters['TWT_P1']} - {self.parameters['TWT_P3']} ms",
            "Filter applied": f"{self.parameters['F1']}-{self.parameters['F2']}-{self.parameters['F3']}-{self.parameters['F4']} Hz",
            "Output file": self.segy_path,
            "File size": f"{os.path.getsize(self.segy_path) / (1024*1024):.2f} MB"
        })
    
    def get_results(self):
        """Get the processing results."""
        return {
            'image_path': self.image_path,
            'segy_path': self.segy_path,
            'filtered_data': self.filtered_data,
            'final_baselines': self.final_baselines,
            'processing_results': self.processing_results
        }