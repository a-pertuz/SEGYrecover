"""Console output utilities for SEGYRecover."""

import datetime
import os

# Global log file handle
log_file = None

def initialize_log_file(work_dir):
    """Initialize the log file for the current session."""
    global log_file
    
    # Create a timestamped filename for the log
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(work_dir, "LOG")
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"segyrecover_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    try:
        log_file = open(log_path, 'w', encoding='utf-8')
        log_file.write(f"SEGYRecover Log - Session started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"Working directory: {work_dir}\n\n")
        log_file.flush()
        return log_path
    except Exception as e:
        print(f"Error initializing log file: {e}")
        return None

def close_log_file():
    """Close the log file properly."""
    global log_file
    if log_file and not log_file.closed:
        log_file.write(f"\nSession ended at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.close()

def _write_to_log(message):
    """Write a message to the log file."""
    global log_file
    if log_file and not log_file.closed:
        try:
            log_file.write(f"{message}\n")
            log_file.flush()  # Ensure immediate write to file
        except Exception as e:
            print(f"Error writing to log file: {e}")

def timestamp():
    """Return current timestamp for console messages."""
    return datetime.datetime.now().strftime("[%H:%M:%S]")

def section_header(console, title):
    """Print a section header with formatting."""
    message = f"\n{timestamp()} === {title.upper()} ==="
    console.append(message)
    _write_to_log(message)
    
def success_message(console, message):
    """Print a success message."""
    formatted = f"{timestamp()} ✓ {message}"
    console.append(formatted)
    _write_to_log(formatted)
    
def error_message(console, message):
    """Print an error message."""
    formatted = f"{timestamp()} ❌ ERROR: {message}"
    console.append(formatted)
    _write_to_log(formatted)
    
def warning_message(console, message):
    """Print a warning message."""
    formatted = f"{timestamp()} ⚠️ WARNING: {message}"
    console.append(formatted)
    _write_to_log(formatted)
    
def info_message(console, message):
    """Print an info message."""
    formatted = f"{timestamp()} ℹ️ {message}"
    console.append(formatted)
    _write_to_log(formatted)
    
def progress_message(console, step, total, message):
    """Print a progress message with step count."""
    if total:
        formatted = f"{timestamp()} [{step}/{total}] {message}"
    else:
        formatted = f"{timestamp()} {message}"
    console.append(formatted)
    _write_to_log(formatted)
        
def summary_statistics(console, stats_dict):
    """Print summary statistics."""
    header = f"\n{timestamp()} === SUMMARY STATISTICS ==="
    console.append(header)
    _write_to_log(header)
    
    for key, value in stats_dict.items():
        item = f"  • {key}: {value}"
        console.append(item)
        _write_to_log(item)
    
    console.append("")  # Empty line after statistics
    _write_to_log("")
