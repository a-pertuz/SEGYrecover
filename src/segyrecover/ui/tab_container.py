"""Tab container for SEGYRecover application."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QStackedWidget, QWidget, QVBoxLayout, QSplitter

class TabContainer(QWidget):
    """Container for workflow tabs."""
    
    # Signal emitted when a tab is changed
    tabChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tab_container")
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create stacked widget to handle tab switching
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("stacked_widget")
        layout.addWidget(self.stacked_widget)
        
        # Keep track of tab indices
        self.tab_indices = {}
    
    def add_tab(self, identifier, widget):
        """Add a new tab to the container."""
        widget.setObjectName(f"{identifier}_tab")
        index = self.stacked_widget.addWidget(widget)
        self.tab_indices[identifier] = index
        return index
    
    def switch_to(self, identifier):
        """Switch to a specific tab by identifier."""
        if identifier in self.tab_indices:
            self.stacked_widget.setCurrentIndex(self.tab_indices[identifier])
            self.tabChanged.emit(identifier)
    
    def current_tab_identifier(self):
        """Get the identifier of the current tab."""
        current_index = self.stacked_widget.currentIndex()
        for identifier, index in self.tab_indices.items():
            if index == current_index:
                return identifier
        return None

    def widget(self, index):
        """Get the widget at the specified index."""
        return self.stacked_widget.widget(index)


class ConsoleContainer(QWidget):
    """Container for console output that can be shared across tabs."""
    
    def __init__(self, console, parent=None):
        super().__init__(parent)
        self.console = console
        
        # Set up the layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(console)
