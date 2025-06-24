"""SEGY Header editor dialog for SEGYRecover."""

import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QDialogButtonBox, QApplication, QMessageBox, QScrollArea,
    QWidget
)
import seisio

from ..utils.console_utils import info_message, error_message, success_message


class SEGYHeaderEditorDialog(QDialog):
    """Dialog for editing SEGY textual header."""
    
    def __init__(self, segy_path, console, work_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit SEGY Header")
        self.segy_path = segy_path
        self.console = console
        self.work_dir = work_dir
        self.output_file = segy_path  # By default, output is same as input
        
        # Fix window sizing and positioning
        screen = QApplication.primaryScreen().geometry()
        screen_width = min(screen.width(), 1920)
        screen_height = min(screen.height(), 1080)
        window_width = int(screen_width * 0.7)  # Wider for better text editing
        window_height = int(screen_height * 0.7)
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        self.setGeometry(pos_x, pos_y, window_width, window_height)
        
        # Read the SEGY file to get the current header
        try:
            info_message(self.console, "Reading current SEGY header")
            segy_in = seisio.input(self.segy_path)
            self.txt_header = segy_in.get_txthead().copy()
            self.ns = segy_in.ns
            self.vsi = segy_in.vsi
        except Exception as e:
            error_message(self.console, f"Error reading SEGY header: {str(e)}")
            self.txt_header = [""] * 40  # Initialize empty header if file cannot be read
        
        # Set up the layout
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Edit SEGY Textual Header")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Edit the SEGY textual header below. The header consists of 40 lines, "
            "each with exactly 80 characters. Lines will be automatically padded or "
            "truncated to maintain this format."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Create a scroll area for the line edits
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setSpacing(5)
        
        # Create 40 line edits
        self.line_edits = []
        for i in range(40):
            line_layout = QHBoxLayout()
            
            # Add line number
            line_num = QLabel(f"{i+1:2d}:")
            line_num.setFont(QFont("Courier New", 10))
            line_num.setFixedWidth(30)
            line_layout.addWidget(line_num)
            
            # Create line edit
            line_edit = QLineEdit()
            line_edit.setFont(QFont("Courier New", 10))  # Monospaced font
            line_edit.setFixedHeight(30)
            line_edit.setMaxLength(80)  # Limit to 80 characters
            
            # Set text from header if available
            if i < len(self.txt_header):
                line_edit.setText(self.txt_header[i])
            
            line_layout.addWidget(line_edit)
            self.line_edits.append(line_edit)
            scroll_layout.addLayout(line_layout)
        
        scroll_container.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area)
        
        # Character count label
        self.char_count_label = QLabel("40 lines × 80 characters per line")
        layout.addWidget(self.char_count_label)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def validate_and_accept(self):
        """Validate the header format and apply changes if accepted."""
        # Check if any line exceeds 80 characters (should not happen due to maxLength)
        long_lines = [i+1 for i, edit in enumerate(self.line_edits) if len(edit.text()) > 80]
        if long_lines:
            formatted = ", ".join(map(str, long_lines[:5]))
            if len(long_lines) > 5:
                formatted += f" and {len(long_lines) - 5} more"
                
            result = QMessageBox.question(
                self,
                "Line Length Warning",
                f"Lines {formatted} exceed 80 characters and will be truncated. Continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if result == QMessageBox.No:
                return
        
        # If validation passes, apply the changes
        if self.apply_changes():
            self.accept()
    
    def get_header_text(self):
        """Return the edited header as a list of strings."""
        formatted_lines = []
        for line_edit in self.line_edits:
            text = line_edit.text()
            # Only pad with spaces if the line has content, otherwise leave it empty
            if text.strip(): 
                formatted_line = text.ljust(80)[:80]
            else:  
                formatted_line = ""
            formatted_lines.append(formatted_line)
        
        return formatted_lines
        
    def apply_changes(self):
        """Apply the header changes to the SEGY file."""
        try:
            info_message(self.console, "Updating SEGY file with new header")
            
            # Get edited header
            new_header = self.get_header_text()
            new_header_text = ''.join(new_header)
            
            # Create temporary output file
            temp_segy_path = self.segy_path + ".temp.segy"
            
            try:
                segy_in = seisio.input(self.segy_path)
                
                segy_out = seisio.output(
                    temp_segy_path,
                    ns=self.ns,
                    vsi=self.vsi,
                    endian=">", 
                    format=5, 
                    txtenc="ebcdic"
                )                
                
                # Set the new textual header
                segy_out.log_txthead(txthead=new_header_text)
                
                # Copy binary header
                binhead = segy_in.get_binhead()
                segy_out.log_binhead(binhead=binhead)
                
                # Initialize output
                segy_out.init(textual=new_header_text, binary=binhead)
                
                # Read trace data and extract it correctly
                traces = segy_in.read_all_traces()
                trace_data = traces["data"].copy()
                trace_header = segy_in.read_all_headers()                    

                segy_out.write_traces(data=trace_data, headers=trace_header)
                info_message(self.console, "All traces written successfully")
                
                segy_out.finalize()

            except Exception as e:
                error_message(self.console, f"Error in SEGY output operation: {str(e)}")
                raise   

            os.replace(temp_segy_path, self.segy_path)
            
            success_message(self.console, f"SEGY file header updated successfully: {os.path.getsize(self.segy_path) / 1024:.2f} KB")
            
            return True
            
        except Exception as e:
            error_message(self.console, f"Error updating SEGY header: {str(e)}")
            return False