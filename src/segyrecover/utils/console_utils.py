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
            log_file.flush()  
        except Exception as e:
            print(f"Error writing to log file: {e}")

def timestamp():
    """Return current timestamp for console messages."""
    return datetime.datetime.now().strftime("[%H:%M:%S]")

def section_header(console, title):
    """Print a section header with formatting (bold title).

    Uses HTML formatting for QTextEdit.
    """
    message = f'<br><br><b><span style="font-size:11pt;">{title.upper()}</span></b><br><br>'
    console.insertHtml(message)
    _write_to_log(f"\n\n{title.upper()} ")

def success_message(console, message):
    """Print a success message."""
    formatted = f'<br><span style="color:green;">&#10003; {message}</span><br>'
    console.insertHtml(formatted)
    _write_to_log(f"\n✓{message}")

def error_message(console, message):
    """Print an error message."""
    formatted = f'<br><span style="color:red;"><b>&#10060; ERROR:</b> {message}</span><br>'
    console.insertHtml(formatted)
    _write_to_log(f"\n❌ERROR: {message}")

def warning_message(console, message):
    """Print a warning message."""
    formatted = f'<br><span style="color:orange;"><b>&#9888; WARNING:</b> {message}</span><br>'
    console.insertHtml(formatted)
    _write_to_log(f"\n⚠️WARNING: {message}")

def info_message(console, message):
    """Print an info message."""
    formatted = f'<br>{message}<br>'
    console.insertHtml(formatted)
    _write_to_log(f"\n{message}")

def progress_message(console, step, total, message):
    """Print a progress message with step count."""
    if total:
        formatted = f'<br><span style="color:blue;">[{step}/{total}] {message}</span><br>'
    else:
        formatted = f'<br>{message}<br>'
    console.insertHtml(formatted)
    _write_to_log(f"\n[{step}/{total}] {message}" if total else f"\n{message}")

def summary_statistics(console, stats_dict):
    """Print summary statistics."""
    header = f'<br><b><span style="font-size:11pt;">SUMMARY STATISTICS</span></b><br>'
    console.insertHtml(header)
    _write_to_log("\nSUMMARY STATISTICS ")

    for key, value in stats_dict.items():
        item = f'<br>&nbsp;&nbsp;&bull; <b>{key}:</b> {value}<br>'
        console.insertHtml(item)
        _write_to_log(f"  • {key}: {value}")

    console.insertHtml("<br>")
    _write_to_log("")

