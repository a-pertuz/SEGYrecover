## Detailed Tutorial

### Preparation

Before beginning the digitization process:

1. **Organize your files**:
   - Place all seismic image files you want to digitize in the `IMAGES` folder
   - Put corresponding geometry files in the `GEOMETRY` folder
   - Ensure geometry files have the same base name as the image files with a `.geometry` extension

2. **Check supported formats**:
   - Image files: TIF, JPG, PNG
   - Geometry files: Text files with CDP, X, Y coordinates (see format below)

3. **Verify image quality**:
   - Images should have clear trace lines and time markers
   - Higher resolution images generally yield better results
   - Minimal annotations overlapping the seismic data is preferable

Once your files are properly organized, you can proceed with the digitization process.

### Step 1: Loading an Image

1. Launch SEGYRecover by running `segyrecover`
2. Click the "Load Image" button
3. Select your seismic image file (supported formats: TIF, JPG, PNG)
4. Two windows will appear:
   - **Seismic Section Image**: Displays the loaded image
   - **Seismic Line Location**: Shows the geometry data if available

**Note**: SEGYRecover looks for a corresponding geometry file in the GEOMETRY folder. The geometry file should have the same base name as your image with a .geometry extension.

#### Geometry File Format

The geometry file should contain CDP (Common Depth Point) numbers and their corresponding X,Y coordinates in UTM format. The first and last CDP point for a seismic lines are needed in order to have a georeferenced SEGY file.
```
CDP_NUMBER X_COORDINATE Y_COORDINATE
```
For example:
```
100 500000.0 4500000.0
101 500025.0 4500020.0
102 500050.0 4500040.0
```

### Step 2: Setting Parameters

1. Click the "Parameters" button to open the parameter dialog
2. Set the following parameters:

#### ROI Points
These define the mapping between image coordinates and seismic trace/time coordinates:
- **P1 (Top Left)**: Set Trace number and TWT (Two-Way Time) value
- **P2 (Top Right)**: Set Trace number and TWT value
- **P3 (Bottom Left)**: Set Trace number and TWT value

For example, if your seismic image shows:
- Top left (P1): Trace 100 at 0 ms
- Top right (P2): Trace 500 at 0 ms
- Bottom left (P3): Trace 100 at 3000 ms

This establishes a grid where:
- The horizontal axis spans from trace 100 to 500
- The vertical axis represents time from 0 to 3000 milliseconds
- The software will calculate trace spacing and time increments accordingly

**Note**: The program can handle TWT values above datum as negative values (e.g -200 ms) but it won't be saved as such in the SEGY files to avoid post-processing errors. 

#### Acquisition Parameters
- **Sample Rate (ms)**: Time interval between samples (e.g., 1, 2, or 4 ms)
- **Frequency Band (Hz)**: Four corners of the bandpass filter (F1, F2, F3, F4)
  - F1: Low cut-off frequency
  - F2: Low pass frequency
  - F3: High pass frequency
  - F4: High cut-off frequency

Example values:
```
F1=8, F2=12, F3=60, F4=80  # For vintage seismic data
F1=3, F2=5, F3=80, F4=100  # For modern broadband data
```

#### Detection Parameters
- **TLT (Traceline Thickness)**: Width of vertical trace lines in pixels
- **HLT (Timeline Thickness)**: Width of horizontal time lines in pixels

#### Advance Detection Parameters. 
**Leave default values unless you want some experimentation**
- **HE (Horizontal Erode)**: Erosion size for horizontal features. Default value should efficiently issolate traces but some experimentation could be needed in certain seismic sections.
- **BDB (Baseline Detection Beginning)**: Starting row for baseline detection. Defines the upper boundary (in pixels from top) where the algorithm begins searching for trace baselines.
- **BDE (Baseline Detection End)**: Ending row for baseline detection. Defines the lower boundary where the algorithm stops searching for baselines. Set this to avoid noisy bottom areas.
- **BFT (Baseline Filter Threshold)**: Threshold percentage for filtering close baselines. Higher values (e.g., 90%) result in more strict baseline filtering.

3. Click "Accept" to save parameters

**Pro Tip**: Use the following rules of thumb for initial parameter settings:
- **TLT**: Typically 1 pixel unless for high resolution images with broad traces.
- **HLT**: Typically 4-8 pixels for standard timeline thickness
- **HE**: Around 20-100 depending on image quality 
- **BDB**: Set to approximately 10-20 pixels to remove residual borders
- **BDE**: Set to approximately 100-300 to account for the part where empty traces are shown. Tipically those above datum.
- **BFT**: Typically 80-90%, lower values allow might allow duplicates.

### Step 3: Selecting Region of Interest

1. Click "Begin Digitization" to start the ROI selection process
2. A window will appear showing your seismic image
3. Use the navigation toolbar to **zoom** in for accurate point selection
4. Click in each button to select three corner points in this order:
   - Point 1: Top-left corner
   - Point 2: Top-right corner
   - Point 3: Bottom-left corner
5. The fourth corner will be calculated automatically
6. Confirm each point placement in the dialog
7. After all points are selected, click "Accept"
8. Confirm the ROI selection in the final dialog

**Best Practices**:
- Zoom in to select points precisely using the magnifier button
- Reset zoom by clicking on the home button

### Step 4: Processing

After confirming the ROI, SEGYRecover performs these processing steps **automatically**:

1. **Timeline Detection and Removal**
   - Detects horizontal timeline marks
   - Removes timelines while preserving amplitude information

2. **Baseline Detection**
   - Identifies vertical trace lines
   - A verification window appears showing:
     - Original image with baselines
     - Detected timelines
     - Image with timelines removed
     - Debug view of baseline detection
   - Review the detected baselines (shown in different colors):
     - Red: Raw detected baselines
     - Lime: Final selected baselines
     - Cyan (dashed): Synthetic baselines added to fill gaps
   - Click "Continue" if the detection is acceptable, or "Restart" to try different parameters

3. **Amplitude Extraction**
   - Extracts amplitude values between detected baselines counting the number of black pixels per row
   - Processing methods after raw amplitude extraction:
     - Zero-values are asiggned a new value equal to - (median) of each trace
     - Handles clipped values using Akima interpolation for natural curve restoration
     - Smooths the curve with cubic spline interpolation

4. **Data Processing**
   - Resamples to the specified sample rate
   - Applies bandpass filtering using the specified frequency band
   - Normalizes amplitudes for each trace

5. **SEGY Creation**
   - A "Coordinates Assignment" dialog appears to select the direction of CDPs: increasing or decreasing left to right
   - The application interpolates coordinates for all traces
   - Creates a standard SEGY file with properly populated headers

### Step 5: Results

When processing is complete, two windows will appear:

1. **Digitized SEGY**: Displays the final SEGY section
2. **Average Amplitude Spectrum**: Shows the frequency spectrum of the data. Spikes can be correlated to timelines not being correctly removed

The SEGY file is saved in the SEGY folder with the same base name as the input image.

## Troubleshooting

### Common Issues

1. **Poor timeline detection**:
   - Try adjusting HLT and HE parameters

2. **Missing or extra baselines**:
   - Adjust BDB and BDE to focus on a cleaner part of the image
   - Increase BFT to filter out false detections
   - Decrease BFT if legitimate baselines are being filtered out

3. **Noisy or spiky data**:
   - Adjust frequency filter parameters (F1-F4)
   - Try a narrower frequency band
   - Check if the selected ROI includes non-seismic elements

4. **Coordinate assignment issues**:
   - Ensure geometry file is properly formatted
   - Verify CDP numbers are in the correct range
   - Make sure X/Y coordinates are in a consistent coordinate system

### Log Files

SEGYRecover automatically creates detailed log files for every session. These logs can be extremely helpful for troubleshooting issues:

1. **Location**: Log files are stored in the `LOG` folder within your data directory.
2. **Naming**: Each log file is named with a timestamp format `segyrecover_YYYYMMDD_HHMMSS.log`
3. **Contents**: Log files contain:
   - Complete console output with timestamps
   - Process steps with success/failure indicators
   - Error messages and warnings
   - Summary statistics of processed data

If you encounter issues with the software, providing these log files to the developers can help diagnose problems more quickly.