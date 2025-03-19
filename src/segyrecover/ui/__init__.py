"""UI components for the SEGYRecover application."""

# Import main components to make them available at package level
from .main_window import SegyRecover
from .help_dialogs import AboutDialog, HelpDialog, FirstRunDialog
from .status_bar import ProgressStatusBar
from .app_dialogs import ParameterDialog, TimelineBaselineWindow, ROIManager, ROISelectionDialog
from .image_viewer import ImageLoader, display_segy_results, display_amplitude_spectrum
from .workflow import initialize, load_image, input_parameters, select_area
