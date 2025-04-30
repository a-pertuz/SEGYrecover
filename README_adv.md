# SEGYRecover - Advanced Developer Documentation

## Table of Contents

1. [Program Overview](#program-overview)
2. [Architecture](#architecture)
   - [Code Organization](#code-organization)
3. [Entry Point and Initialization](#entry-point-and-initialization)
4. [Core Components](#core-components)
   - [UI Module](#1-ui-module-ui)
   - [Core Module](#2-core-module-core)
   - [Utils Module](#3-utils-module-utils)
5. [Workflow Process and Data Flow](#workflow-process-and-data-flow)
6. [File Structure Details](#file-structure-details)
   - [UI Components](#ui-components)
   - [Core Processing Components](#core-processing-components)
   - [Utility Components](#utility-components)
7. [Import Scheme](#import-scheme)
8. [External Dependencies](#external-dependencies)
9. [Directory Structure](#directory-structure)
10. [Styling System](#styling-system)
11. [Key UI Features](#key-ui-features)
12. [Detailed UI Tab Components](#detailed-ui-tab-components)
    - [Welcome Tab](#welcome-tab-_0_welcome_tabpy)
    - [Load Image Tab](#load-image-tab-_1_load_image_tabpy)
    - [Parameters Tab](#parameters-tab-_2_parameters_tabpy)
    - [ROI Selection Tab](#roi-selection-tab-_3_roi_selection_tabpy-and-_3_1_roi_selection_logicpy)
    - [Digitization Tab](#digitization-tab-_4_digitization_tabpy-_4_1_digitization_logicpy-_4_2_coords_dialogspy)
    - [Results Tab](#results-tab-_5_results_tabpy)
13. [File Details and Dependencies](#file-details-and-dependencies)
    - [UI Files](#ui-files)
    - [Core Files](#core-files)
    - [Utility Files](#utility-files)

## Program Overview

SEGYRecover is a specialized Python application for digitizing scanned seismic sections and converting them to standard SEGY format. It provides an intuitive Qt-based GUI interface that guides users through a step-by-step workflow for processing seismic images, from loading raw images to creating properly formatted SEGY files with appropriate header information and coordinate data.

## Architecture

SEGYRecover follows a modular architecture with clear separation between the user interface, processing logic, and utility functions. The codebase is organized using the following high-level structure:

```
segyrecover/
├── __init__.py        # Package initialization with version
├── __main__.py        # Application entry point
├── core/              # Core processing functionality
├── ui/                # User interface components
└── utils/             # Utility functions
```

### Code Organization

The application is structured following a layered architecture pattern:

1. **UI Layer**: All user interface components using PySide6 (Qt for Python)
2. **Core Layer**: Image processing, data extraction, and SEGY file creation
3. **Utility Layer**: Helper functions for console output, resource management, etc.

## Entry Point and Initialization

The application's entry point is in `__main__.py`, which sets up the Qt application, configures styling, and displays the main window. It handles:

- Setting up the QApplication with Fusion style
- Loading the QSS theme stylesheet
- Setting up a timer for dynamic stylesheet reloading during development
- Setting appropriate window dimensions based on the screen size
- Initializing the main window

The main application window (`SegyRecover` class) is instantiated from `main_window.py` and forms the container for all other UI components.

## Core Components

### 1. UI Module (`ui/`)

The UI module contains all graphical interface components, implemented using PySide6 (Qt for Python):

- **main_window.py**: Main application window, status bar, console, menu bar
- **navigation_panel.py**: Side panel for workflow navigation
- **tab_container.py**: Container for step-based workflow tabs
- **_0_welcome_tab.py** through **_5_results_tab.py**: Individual workflow step tabs
- **help_dialogs.py**: Help and about dialogs
- **theme.qss**: Qt Style Sheet file for UI styling

The UI follows a tab-based workflow with a navigation panel for switching between workflow steps.

### 2. Core Module (`core/`)

The core module contains processing logic for:

- **image_processor.py**: Image processing algorithms for timeline detection and removal
- **amplitude_extractor.py**: Extracts amplitude data from processed images
- **data_processor.py**: Processes and filters extracted data
- **segy_writer.py**: Creates SEGY files with proper headers and coordinates

### 3. Utils Module (`utils/`)

The utils module provides helper functions:

- **console_utils.py**: Handles console output formatting and logging
  - Contains functions like section_header, success_message, error_message, warning_message, info_message
  - Manages log file creation and handling
- **resource_utils.py**: Manages resource files and tutorial data
  - Handles copying tutorial files to user workspace

## Workflow Process and Data Flow

SEGYRecover implements a step-by-step workflow that follows a logical data flow from image loading to SEGY file creation:

1. **Welcome**: 
   - Introduction and project selection
   - User creates a new project or loads an existing one
   - Project configuration and workspace initialization

2. **Load Image**: 
   - Loading and displaying the source seismic image
   - Binary image data is loaded into memory
   - Image is displayed for inspection using Matplotlib
   - Image properties (dimensions, color depth) are extracted

3. **Parameters**: 
   - Setting processing parameters and ROI points
   - User configures parameters for timeline detection, amplitude extraction, and SEGY file creation
   - Parameters are validated and saved for later use
   - Parameters affect all subsequent processing steps

4. **ROI Selection**: 
   - Selecting region of interest on the image
   - User defines the exact area to be processed
   - ROI coordinates are collected and transformed to image coordinates
   - ROI may be rectangular or polygonal depending on the image and user preference

5. **Digitization**: 
   - Processing image and extracting data
   - The system performs image processing using the defined parameters
   - Timeline detection algorithms identify time markers
   - Amplitude extraction converts pixel intensity to amplitude values
   - Coordinate assignment maps traces to real-world coordinates
   - This is the most computation-intensive step in the workflow

6. **Results**: 
   - Displaying results and saving SEGY file
   - Processed data is visualized for quality assessment
   - SEGY file is created with proper headers and coordinate information
   - User can adjust parameters and reprocess if needed
   - Final SEGY file is saved to the project directory

Each step builds upon the previous one, with data flowing through the application in a sequential manner. The user interface guides the user through this workflow, ensuring that each step is completed correctly before proceeding to the next.

The key data transformations in this flow are:
- Image data → ROI selection → Processed image → Amplitude data → Coordinate assignment → SEGY file

Each transformation is handled by specific components in the core module, with the UI providing the interface for user interaction and visualization of the results.

## File Structure Details

### UI Components

- **main_window.py**: Creates the main application window and the `SegyRecover` class
  - Contains `ProgressStatusBar` class for progress indication
  - Sets up the main layout with navigation panel and tab container
  - Manages console output and logging
  - Handles user preferences and configuration

- **navigation_panel.py**: Implements the `NavigationPanel` class
  - Provides navigation buttons for each step of the workflow
  - Handles step navigation and progress tracking
  - Controls tab enabling/disabling based on workflow state

- **tab_container.py**: Implements the `TabContainer` class
  - Contains and manages all workflow tab widgets
  - Controls tab switching and data passing between tabs

- **_0_welcome_tab.py** through **_5_results_tab.py**: Implement individual workflow steps
  - Each tab represents one step in the processing workflow
  - Contains UI components specific to each step

- **help_dialogs.py**: Contains help and information dialogs
  - `HelpDialog`: Shows application usage instructions
  - `AboutDialog`: Shows application information
  - `FirstRunDialog`: First-run configuration dialog

### Core Processing Components

- **image_processor.py**: Contains the `ImageProcessor` class
  - Implements algorithms for timeline detection and removal
  - Detects vertical baselines in processed images
  - Uses morphological operations for image enhancement

- **amplitude_extractor.py**: Contains the `AmplitudeExtractor` class
  - Extracts amplitude data from processed images
  - Converts pixel data to amplitude values

- **data_processor.py**: Contains the `DataProcessor` class
  - Applies resampling and filtering to extracted data
  - Prepares data for SEGY file creation

- **segy_writer.py**: Contains the `SegyFileWriter` class
  - Creates properly formatted SEGY files
  - Handles coordinate assignment using geometry files
  - Writes SEGY headers and data traces
  - Manages trace header information and coordinates

### Utility Components

- **console_utils.py**: Contains console output utilities
  - Provides formatted output to the application console with different message types
  - Handles log file creation and management
  - Includes functions for section headers and summary statistics

- **resource_utils.py**: Contains resource management functions
  - Handles copying and management of tutorial files
  - Manages application resources

## Import Scheme

The application follows a consistent import scheme to ensure modularity and maintainability. Each module imports only the necessary components from other modules, and relative imports are used within the package.

Key patterns in the import structure:
- UI modules import utility modules for console output and resource management
- Core modules are imported by UI tabs that use their functionality
- Cross-module references are minimized to avoid circular dependencies

## External Dependencies

SEGYRecover relies on several external libraries:

- **PySide6**: Qt for Python, providing the GUI framework
- **NumPy**: For numerical computations and array handling
- **Matplotlib**: For visualization and plotting of seismic data and images
  - Using the QtAgg backend for integration with PySide6
- **SciPy**: For signal processing, interpolation, and filtering
- **Seisio**: For SEGY file format handling and manipulation
- **appdirs**: For determining appropriate platform-specific paths for user data

## Directory Structure

The application has a well-organized directory structure that follows Python package conventions. The main source code is under `src/segyrecover/` with separate directories for different components:

```
segyrecover/
├── LICENSE.txt                 # License information
├── pyproject.toml              # Python project configuration for packaging
├── README_adv.md               # Advanced documentation (this file)
├── README.md                   # Basic usage documentation
├── TUTORIAL.md                 # Tutorial guide for new users
│
├── src/                        # Source code root
│   └── segyrecover/            # Main package
│       ├── __init__.py         # Package initialization with version
│       ├── __main__.py         # Application entry point
│       │
│       ├── core/               # Core processing functionality
│       │   ├── __init__.py     # Core package initialization
│       │   ├── amplitude_extractor.py  # Amplitude data extraction
│       │   ├── data_processor.py       # Data processing and filtering
│       │   ├── image_processor.py      # Image processing algorithms
│       │   └── segy_writer.py          # SEGY file creation
│       │
│       ├── examples/           # Example data for tutorials
│       │   ├── GEOMETRY/       # Example geometry files
│       │   │   └── RIV6.geometry
│       │   ├── IMAGES/         # Example source images
│       │   │   └── RIV6.tif
│       │   └── PARAMETERS/     # Example parameter files
│       │       └── RIV6.par
│       │
│       ├── ui/                 # User interface components
│       │   ├── __init__.py     # UI package initialization
│       │   ├── _0_welcome_tab.py               # Welcome screen
│       │   ├── _1_load_image_tab.py            # Image loading
│       │   ├── _2_parameters_tab.py            # Parameter configuration
│       │   ├── _3_1_roi_selection_logic.py     # ROI selection logic
│       │   ├── _3_roi_selection_tab.py         # ROI selection interface
│       │   ├── _4_1_digitization_logic.py      # Digitization processing logic
│       │   ├── _4_2_coords_dialogs.py          # Coordinate dialogs
│       │   ├── _4_digitization_tab.py          # Digitization interface
│       │   ├── _5_results_tab.py               # Results display
│       │   ├── help_dialogs.py                 # Help and about dialogs
│       │   ├── main_window.py                  # Main application window
│       │   ├── navigation_panel.py             # Navigation panel
│       │   ├── tab_container.py                # Tab container
│       │   └── theme.qss                       # UI styling
│       │
│       └── utils/              # Utility functions
│           ├── __init__.py     # Utils package initialization
│           ├── console_utils.py      # Console output utilities
│           └── resource_utils.py     # Resource management
│
├── tests/                      # Test scripts and utilities
    ├── cleanup.py              # Cleanup script for test data
    ├── display_npy.py          # Utility to display NumPy arrays
    ├── run_src_segyrecover.py  # Script to run from source
    ├── test_coordinate_dialog.py     # Test for coordinate dialog
    ├── test_roi_dialog.py            # Test for ROI selection
    └── test_windows_sizes.py         # Test for window sizing
```

When the application is installed, the package structure is preserved, and the following additional directories are created in the user's working directory for project data:

```
[Project Directory]/
├── IMAGES/        # Source seismic images uploaded by the user
├── GEOMETRY/      # Geometry files containing trace coordinates
├── PARAMETERS/    # Saved processing parameters
├── ROI/           # Region of interest data
├── SEGY/          # Output SEGY files
├── LOG/           # Application log files
└── raw/           # Intermediate processing files and temporary data
```

The application uses the `appdirs` library to determine the appropriate user data directory based on the operating system:
- On Windows: `%APPDATA%\SEGYRecover`
- On macOS: `~/Library/Application Support/SEGYRecover`
- On Linux: `~/.local/share/SEGYRecover`

## Styling System

The application uses Qt Style Sheets (QSS) for UI styling:

- **theme.qss**: Contains all styling definitions for the application's visual appearance
- A dynamic stylesheet reloading mechanism in `__main__.py` that checks for file modifications every second
- Styling follows a consistent color scheme and design language across all components
- The application uses the Fusion style as a baseline, enhanced with custom styling

## Key UI Features

The application provides several key UI features to enhance user experience:

- **Navigation Panel**: Allows users to navigate through different workflow steps
- **Progress Status Bar**: Displays the progress of the current operation with cancel functionality
- **Integrated Console**: Provides real-time feedback with color-coded messages
- **Help Dialogs**: Provide usage instructions and application information
- **Real-time Updates**: Dynamic updates to the UI based on user actions
- **Matplotlib Integration**: Embedded plots for visualization

## Detailed UI Tab Components

### Welcome Tab (`_0_welcome_tab.py`)

The Welcome tab serves as the entry point for the user interaction flow. Key features include:

- **Project Selection**: Allows users to create a new project or open an existing one
- **Tutorial Access**: Provides access to built-in tutorial resources
- **Application Information**: Displays application information and version
- **First-run Configuration**: Configures initial application settings on first run

The tab is implemented as a `WelcomeTab` class and includes:
- Project creation dialog with directory selection
- Project loading mechanism that restores previous session state
- Tutorial resources management that copies example files to user workspace

### Load Image Tab (`_1_load_image_tab.py`)

The Load Image tab handles the loading and display of seismic section images. Key features include:

- **Image Loading**: Provides file browser for selecting seismic images
- **Image Display**: Displays the loaded image using Matplotlib
- **Image Information**: Shows image metadata (dimensions, color depth)
- **Image Format Conversion**: Automatically converts various image formats to supported formats

The tab uses a Matplotlib figure canvas embedded in a Qt widget for high-quality image display. It supports:
- Zooming and panning within the image
- Image rotation and flipping if needed
- Basic contrast and brightness adjustments
- Mouse position tracking for coordinate display

### Parameters Tab (`_2_parameters_tab.py`)

The Parameters tab allows users to configure processing parameters. Key features include:

- **Processing Parameters**: Input fields for setting various processing parameters
- **Parameter Presets**: Save and load parameter presets
- **Parameter Validation**: Real-time validation of parameter values
- **Advanced Settings**: Access to advanced processing options

Key parameter groups include:
- Image processing parameters (threshold values, morphological operation sizes)
- Amplitude extraction parameters (sampling rate, trace spacing)
- Timeline detection parameters (detection threshold, minimum length)
- SEGY output parameters (format version, endianness)

### ROI Selection Tab (`_3_roi_selection_tab.py` and `_3_1_roi_selection_logic.py`)

The ROI Selection tab provides an interactive interface for selecting the region of interest on the seismic image. Key features include:

- **Interactive Selection**: Click-and-drag selection of region of interest
- **Corner Point Editing**: Fine-tuning of corner point positions
- **Zoom Controls**: Zoom in/out for precise selection
- **Rectangle/Polygon Selection**: Support for both rectangular and polygonal ROI

The ROI selection tab makes use of:
- `_3_1_roi_selection_logic.py`: Implements the actual selection logic and coordinate transformations
- Matplotlib's interactive features for selecting and manipulating regions
- Coordinate system transformations between image and world coordinates

### Digitization Tab (`_4_digitization_tab.py`, `_4_1_digitization_logic.py`, `_4_2_coords_dialogs.py`)

The Digitization tab manages the core processing of the seismic image. Key features include:

- **Process Control**: Start, pause, and reset processing
- **Progress Display**: Real-time progress visualization
- **Timeline Detection**: Automatic detection of timelines in the image
- **Amplitude Extraction**: Extract amplitude data from image pixels
- **Coordinate Assignment**: Assign real-world coordinates to traces
- **Intermediate Results**: Display intermediate processing results

This tab is the most complex and consists of multiple components:
- `_4_digitization_tab.py`: The main tab UI with controls and display elements
- `_4_1_digitization_logic.py`: Processing logic implementation
- `_4_2_coords_dialogs.py`: Dialogs for configuring coordinate assignments

The digitization process integrates with core processing modules:
- `image_processor.py` for image enhancement and timeline detection
- `amplitude_extractor.py` for extracting amplitude data from processed images
- `data_processor.py` for filtering and resampling extracted data

### Results Tab (`_5_results_tab.py`)

The Results tab displays the final processed data and allows for saving the SEGY file. Key features include:

- **Result Visualization**: Display of extracted traces and amplitudes
- **SEGY File Creation**: Interface for creating the final SEGY file
- **SEGY Header Editing**: Tools for configuring SEGY file headers
- **Quality Assessment**: Tools for assessing the quality of the results
- **Export Options**: Various options for exporting the results

The tab makes use of:
- Matplotlib plots for visualizing the extracted seismic data
- Integration with `segy_writer.py` for creating the SEGY file
- Header editing dialogs for configuring SEGY file headers
- Export functionality for various file formats

