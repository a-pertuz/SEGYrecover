# SEGYRecover



[![DOI](https://zenodo.org/badge/DOI/zenodo.15053412.svg)](https://doi.org/10.5281/zenodo.15053412)
[![PyPI](https://img.shields.io/pypi/v/segyrecover)](https://pypi.org/project/segyrecover/)
[![Last Commit](https://img.shields.io/github/last-commit/a-pertuz/segyrecover)](https://github.com/a-pertuz/segyrecover/commits/main)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)
[![Python Version](https://img.shields.io/badge/Python-3.12+-yellow)](https://www.python.org/downloads/)


A Python tool for digitizing scanned seismic sections and converting them to standard SEGY format. SEGYRecover automatically removes timelines, detects trace baselines, extracts amplitude information for each trace, and produces usable SEG-Y files for modern interpretation software.

SEGYRecover is part of the [REVSEIS](https://a-pertuz.github.io/REVSEIS/index.html) suite. A collection of open source tools to digitize and enhance vintage seismic sections. See [REVSEIS](https://a-pertuz.github.io/REVSEIS/index.html) for more information.


## Features

- **Digitization of seismic images** - Convert paper/raster seismic sections into SEGY files compatible with modern interpretation software
- **User-friendly GUI** - Simple interface for the entire digitization workflow
- **Perspective correction** - Handles skewed or distorted scanned images
- **Automatic trace line detection** - Identifies vertical trace lines using common image processing tecniques
- **Timeline  detection and removal** - Detects and removes horizontal timelines.
- **Amplitude extraction** - Converts pixel density to seismic amplitude values for each trace.
- **Frequency filtering** - Apply bandpass filters to clean up digitized data
- **Geospatial referencing** - Associates traces with real-world coordinates

## Citation

If you use this software in your research, please cite it as:

```
Pertuz, A. (2025). SEGYRecover: A Python-based, user-friendly tool for digitizing vintage seismic images into SEG-Y files. Zenodo. https://doi.org/10.5281/zenodo.15053412
```

Find this software in the Zenodo Archive: [https://doi.org/10.5281/zenodo.15053412](https://doi.org/10.5281/zenodo.15053412)

## Installation

### For Windows Users 

1. **Install Python** (if not already installed):
   - Download Python from [python.org](https://www.python.org/downloads/windows/)
   - During installation, make sure to check **"Add Python to PATH"**
   - Click "Install Now" and wait for installation to complete

2. **Install SEGYRecover**:
   - Open Command Prompt (search for "cmd" in Windows search)
   - Type the following command and press Enter:

   ```
   pip install segyrecover
   ```

   Alternatively, install directly from GitHub:
   ```
   python -m pip install git+https://github.com/a-pertuz/segyrecover.git
   ```

3. **Launch the program**:
   After installation, simply type:
   ```
   segyrecover
   ```

4. **First Run Setup**
   When you run velrecover for the first time:

   - You'll be prompted to choose a data storage location
   - Example files will be copied to your selected location
   - The application will create the necessary folder structure



## File Structure

SEGYRecover uses the following folder structure:

```
segyrecover/
├── IMAGES/               # Store input seismic images
├── GEOMETRY/             # Store .geometry files with trace coordinates
├── LOG/                  # Store log files 
├── ROI/                  # Store region of interest points
├── PARAMETERS/           # Store processing parameters
└── SEGY/                 # Store output SEGY files
```

The application automatically creates these folders if they don't exist.

## Quick Start

1. Run `segyrecover`
2. In the **Welcome** tab, click "Start New Line"
3. In the **Load Image** tab, select a seismic image file and click "Next"
4. In the **Parameters** tab, configure or use existing processing parameters and click "Save Parameters", then "Next"
5. In the **ROI Selection** tab, select the four corner points of your seismic section and click "Next"
6. In the **Digitization** tab, click "Start Digitization" and monitor the process through visualization tabs
7. Once complete, click "See Results" to move to the Results tab
8. In the **Results** tab, examine the resulting SEGY file and its frequency spectrum

### System Requirements
- Windows 10/11
- At least 4GB RAM

### Common Windows Issues
- **Program not found**: Ensure Python is added to your PATH
- **Missing dependencies**: Try running `pip install <package_name>`


### Creating a Desktop Shortcut
1. Right-click on your desktop
2. Select "New" → "Shortcut"
3. Type `python -m segyrecover` or just `segyrecover` (if installed via pip)
4. Click "Next" and give the shortcut a name (e.g., "SEGYRecover")
5. Click "Finish"




## References and alternative software

SEGYRecover uses several image processing and signal processing techniques. Some of them are covered by previous digitalization programs:

[1] Miles, P. R., Schaming, M., & Lovera, R. (2007). Resurrecting vintage paper seismic records. _Marine Geophysical Researches_, 28, 319-329.

[2] Farran, M. L. (2008). IMAGE2SEGY: Una aplicación informática para la conversión de imágenes de perfiles sísmicos a ficheros en formato SEGY. _Geo-Temas_, 10, 1215-1218. 

[3] Sopher, D. (2018). Converting scanned images of seismic reflection data into SEG-Y format. _Earth Science Informatics_, 11(2), 241-255.



## License

This software is licensed under the GNU General Public License v3.0 (GPL-3.0).

You may copy, distribute and modify the software as long as you track changes/dates in source files. 
Any modifications to or software including (via compiler) GPL-licensed code must also be made available 
under the GPL along with build & installation instructions.

For the full license text, see [LICENSE](LICENSE) or visit https://www.gnu.org/licenses/gpl-3.0.en.html

---

*For questions, support, or feature requests, please contact Alejandro Pertuz at apertuz@ucm.es*
