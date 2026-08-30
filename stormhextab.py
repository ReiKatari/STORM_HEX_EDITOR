import os
import mmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QMessageBox
from PyQt6.QtCore import pyqtSignal

from stormhexwidget import HexWidget
from stormminimap import HexMinimap
from stormbase import LOCALE, APP_NAME

class HexTab(QWidget):
    cursorChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.mmap_obj = None
        self.read_only = False
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        # Hex View
        self.hex_view = HexWidget(self)
        self.hex_view.cursorChanged.connect(self.on_cursor_changed)
        self.hex_view.verticalScrollBar().valueChanged.connect(self.sync_minimap)
        
        # Minimap
        self.minimap = HexMinimap(self)
        self.minimap.jumpToOffset.connect(self.goto)
        
        layout.addWidget(self.hex_view)
        layout.addWidget(self.minimap)
        
    def apply_theme(self, theme):
        self.hex_view.apply_theme(theme)
        self.minimap.apply_theme(theme)
        
    def open_file(self, path):
        try:
            self.file_path = path
            f = open(path, "r+b")
            self.mmap_obj = mmap.mmap(f.fileno(), 0)
            self.hex_view.set_data(self.mmap_obj)
            self.minimap.set_data(self.mmap_obj)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
            return False
            
    def save_file(self):
        if self.mmap_obj and self.hex_view.edits:
            try:
                for off, val in self.hex_view.edits.items():
                    self.mmap_obj[off] = val
                self.mmap_obj.flush()
                self.hex_view.edits.clear()
                self.hex_view.viewport().update()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {e}")
                return False
        return True # Nothing to save
        
    def close_file(self):
        if self.mmap_obj:
            self.mmap_obj.close()
            self.mmap_obj = None
            
    def on_cursor_changed(self, offset):
        self.cursorChanged.emit(offset)
        
    def goto(self, offset):
        self.hex_view.cursor_pos = offset
        self.hex_view.selection_start = offset
        self.hex_view.selection_end = offset
        
        line = offset // self.hex_view.bytes_per_line
        self.hex_view.verticalScrollBar().setValue(line)
        self.hex_view.viewport().update()
        
    def sync_minimap(self):
        if self.minimap and self.hex_view:
           start_line = self.hex_view.verticalScrollBar().value()
           lh = max(1, self.hex_view.line_height)
           visible_lines = self.hex_view.viewport().height() // lh
           start_byte = start_line * self.hex_view.bytes_per_line
           size_byte = visible_lines * self.hex_view.bytes_per_line
           self.minimap.set_viewport(start_byte, size_byte)
