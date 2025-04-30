"""SEGY file creation functionality for SEGYRecover."""

import os
import numpy as np
from scipy.interpolate import interp1d
import seisio
from PySide6.QtWidgets import QDialog

from ..ui._4_2_coords_dialogs import CoordinateAssignmentDialog

class SegyFileWriter:
    """Handles SEGY file creation, coordinate assignment, and writing"""
    def __init__(self, progress_bar, console, work_dir):
        self.progress = progress_bar
        self.console = console
        self.work_dir = work_dir

    def assign_coordinates(self, base_name, baselines):
        """Assign coordinates to baselines using geometry file"""
        self.console.append("Assigning coordinates to traces...\n")
        self.progress.start("Assigning coordinates...", 3)

        try:
            # Load geometry file
            geometry_file = os.path.join(self.work_dir, 'GEOMETRY', f'{base_name}.geometry')
            if not os.path.exists(geometry_file):
                raise FileNotFoundError("Geometry file not found")

            # Read geometry data
            cdp, x, y = [], [], []
            with open(geometry_file, 'r') as file:
                for line in file:
                    parts = line.strip().split()
                    cdp.append(int(parts[0]))
                    x.append(float(parts[1]))
                    y.append(float(parts[2]))
            self.progress.update(1)

            # Get coordinate input from user
            coords = self._get_coordinate_input(cdp, x, y)
            if coords is None:
                return None
            CDP_coord_i, CDP_coord_f = coords
            self.progress.update(2)

            # Interpolate coordinates
            baseline_coords = self._interpolate_coordinates(
                CDP_coord_i, CDP_coord_f, cdp, x, y, len(baselines)
            )
            self.progress.update(3)

            self.progress.finish()
            return baseline_coords

        except Exception as e:
            self.console.append(f"Error assigning coordinates: {str(e)}\n")
            return None

    def _get_coordinate_input(self, cdp, x, y):
        """Get user input for coordinate assignment"""
        
        dialog = CoordinateAssignmentDialog(cdp)
        
        if dialog.exec() == QDialog.Accepted:
            coords = dialog.get_coordinates()
            if coords and coords[0] in cdp and coords[1] in cdp:
                return coords
        return None

    def _interpolate_coordinates(self, cdp_i, cdp_f, cdp, x, y, n_baselines):
        """Interpolate coordinates between two CDP points"""
        # Get indices for start and end CDPs
        start_idx = cdp.index(cdp_i)
        end_idx = cdp.index(cdp_f)
        
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        # Extract coordinate arrays
        geom_x = np.array(x[start_idx:end_idx + 1])
        geom_y = np.array(y[start_idx:end_idx + 1])

        # Calculate cumulative distances
        distances = [0]
        total_distance = 0
        for i in range(1, len(geom_x)):
            dx = geom_x[i] - geom_x[i-1]
            dy = geom_y[i] - geom_y[i-1]
            total_distance += np.sqrt(dx*dx + dy*dy)
            distances.append(total_distance)
        distances = np.array(distances)

        # Create interpolation points
        baseline_params = np.linspace(0, total_distance, n_baselines)
        
        # Interpolate X and Y coordinates
        f_x = interp1d(distances, geom_x, kind='linear', bounds_error=False, fill_value='extrapolate')
        f_y = interp1d(distances, geom_y, kind='linear', bounds_error=False, fill_value='extrapolate')
        
        baseline_x = f_x(baseline_params)
        baseline_y = f_y(baseline_params)

        return np.column_stack((baseline_x, baseline_y))

    def write_segy(self, data, baselines, image_path, DT, F1, F2, F3, F4):
        """Create and write SEGY file"""
        self.console.append("Creating SEGY file...\n")
        self.progress.start("Creating SEGY file...", 5)

        try:
            # Get dimensions and paths
            ns, nt = data.shape
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            segy_dir = os.path.join(self.work_dir, "SEGY")
            segy_path = os.path.join(segy_dir, f"{base_name}.segy")

            # Get baseline coordinates
            from ..utils.console_utils import info_message, error_message, success_message
            
            info_message(self.console, "Assigning coordinates to traces")
            baseline_coords = self.assign_coordinates(base_name, baselines)
            if baseline_coords is None:
                error_message(self.console, "Failed to assign coordinates")
                return False
            self.progress.update(1)

            # Create SEGY file
            info_message(self.console, "Creating SEGY container")
            out = seisio.output(
                segy_path, 
                ns=ns, 
                vsi=int(DT * 1000), 
                endian=">", 
                format=5, 
                txtenc="ebcdic"
            )
            self.progress.update(2)

            # SEGY TEXTUAL FILE HEADER        
            info_message(self.console, "Writing SEGY headers")
            txt_header = []
            for i in range(40):  # SEGY standard: 40 lines of 80 characters
                txt_header.append(' ' * 80)  # Initialize with spaces

            txt_header[0] = f'{"SEGY FILE CREATED BY SEGYRECOVER":<80}'
            txt_header[1] = f'{"FILENAME: " + os.path.basename(image_path):<80}'
            txt_header[2] = f'{"SAMPLE INTERVAL: " + str(DT) + " MS":<80}'
            txt_header[3] = f'{"TRACES: " + str(nt) + ", SAMPLES: " + str(ns):<80}'
            txt_header[4] = f'{"FILTER: " + str(F1) + "-" + str(F2) + "-" + str(F3) + "-" + str(F4) + " HZ":<80}'
            txt_header[5] = f'{"COORDINATE SYSTEM: UTM":<80}'
            txt_header[6] = f'{"ALL OTHER VALUES ARE DEFAULT":<80}'

            txthead = ''.join(txt_header)

            # SEGY BINARY FILE HEADER
            binhead = out.binhead_template
            binhead["nt"] = float(nt)  # Number of traces
            binhead["ns"] = float(ns)  # Number of samples per trace
            binhead["dt"] = float(DT * 1000)  # Sample interval in microseconds
            out.log_binhead(binhead=binhead)

            # SEGY TRACE HEADER
            trchead = out.headers_template(nt=nt)
            trchead["tracl"] = np.arange(1, nt + 1, dtype=float)  # Trace sequence number
            trchead["dt"] = float(DT * 1000)  # Sample interval in microseconds
            trchead["ns"] = float(ns)  # Number of samples per trace
            trchead["trid"] = 1  # Trace identification code (1 for seismic data)
            trchead["duse"] = 2  # Data use (2 for standard)
            trchead["delrt"] = 0  # Delay time for the first trace (optional)
            trchead["cdp"] = np.arange(1, nt + 1)  # Common depth point
            trchead["sx"] = baseline_coords[:, 0]  # Source X coordinate
            trchead["sy"] = baseline_coords[:, 1]  # Source Y coordinate
            trchead["gx"] = trchead["sx"]  # Receiver X coordinate (same as source for now)
            trchead["gy"] = trchead["sy"]  # Receiver Y coordinate (same as source for now)
            out.log_txthead(txthead=txthead)

            self.progress.update(3)

            # Initialize and write data
            out.init(textual=txthead, binary=binhead)
            out.write_traces(data=data.T, headers=trchead)
            self.progress.update(4)

            # Finalize file
            info_message(self.console, "Finalizing SEGY file")
            out.finalize()
            self.progress.update(5)
            
            success_message(self.console, f"SEGY file created: {segy_path}")
            info_message(self.console, f"File size: {os.path.getsize(segy_path) / (1024*1024):.2f} MB")
            return True

        except Exception as e:
            error_message(self.console, f"Error creating SEGY file: {str(e)}")
            return False
            
        finally:
            self.progress.finish()
