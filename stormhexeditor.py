
import sys
import os
import struct
import math
import binascii
import mmap
import hashlib
import zlib
import time
import webbrowser
import urllib.request
import json
import collections
from datetime import datetime
from stormbase import StormApp, LOCALE, THEMES, resource_path, APP_NAME, CURRENT_VERSION, APP_REPOS, show_about_dialog
# from stormminimap import HexMinimap # Moved to HexTab
from storminspector import StormInspector
from stormhexwidget import (HexWidget, BookmarksWidget, SearchDialog, GoToDialog, 
                              BaseConverterDialog, BitwiseDialog, ChecksumDialog, 
                              SignatureDialog, StringsDialog)
from stormhextab import HexTab
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QMessageBox, QScrollBar, QLabel, QMenu, QDialog, 
                             QLineEdit, QPushButton, QFormLayout, QComboBox, QCheckBox, 
                             QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QToolBar, QStatusBar, QInputDialog, QListWidget, QLayout, QSizePolicy,
                             QAbstractScrollArea, QSpinBox, QTextEdit, QProgressBar, QToolTip, QAbstractButton, QTabWidget, QFrame)
from PyQt6.QtCore import Qt, QSize, QTimer, QSettings, QPoint, QPointF, QRect, pyqtSignal, QEvent, QThread, QMimeData, QByteArray
from PyQt6.QtGui import (QAction, QFont, QFontDatabase, QColor, QPainter, QKeySequence, 
                         QIcon, QPalette, QBrush, QFontMetrics, QDrag, QCursor, QMouseEvent)

# --- STORM SUITE IMPORTS ---
from stormbase import StormApp, LOCALE, THEMES, resource_path, APP_NAME, CURRENT_VERSION
# from stormsuite import LauncherDialog # Circular?
# Actually stormsuite imports everything. stormhexeditor shouldn't import stormsuite if possible?
# But it does for LauncherDialog?
# Main menu has "Program Switcher".
# If I import stormsuite, and stormsuite imports stormhexeditor -> cycle.
# Check stormsuite.py content?
# For now, I'll update the name. If cycle occurs, I'll handle it.
from stormsuite import LauncherDialog

# --- CONSTANTS ---
# --- CONSTANTS ---
# APP_NAME and CURRENT_VERSION imported from storm_base
GITHUB_REPO = "storm-hex-editor"
GITHUB_REPO = "storm-hex-editor" 

 

# --- THEMES ---


MAX_HISTORY = 100

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        # Calc height based on current width or default
        w = self.parentWidget().width() if self.parentWidget() else 800
        h = self._do_layout(QRect(0, 0, w, 0), True)
        return QSize(size.width(), h)
    
    def sizeHint(self):
        return self.minimumSize()

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self.items:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Horizontal)
            layout_spacing_y = style.layoutSpacing(QSizePolicy.ControlType.PushButton, QSizePolicy.ControlType.PushButton, Qt.Orientation.Vertical)
            actual_spacing_x = spacing if spacing >= 0 else layout_spacing_x
            actual_spacing_y = spacing if spacing >= 0 else layout_spacing_y

            next_x = x + item.sizeHint().width() + actual_spacing_x
            if next_x - actual_spacing_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + actual_spacing_y
                next_x = x + item.sizeHint().width() + actual_spacing_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class WrappingToolBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_obj = FlowLayout(self, margin=2, spacing=4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.actions_map = [] # (action, button)

    def addAction(self, action):
        btn = QPushButton(action.text())
        btn.clicked.connect(action.trigger)
        btn.setToolTip(action.toolTip() or action.text())
        btn.setStyleSheet("padding: 2px 8px; margin: 1px;")
        btn.setFixedHeight(28)
        if not action.icon().isNull():
            btn.setIcon(action.icon())
        self.layout_obj.addWidget(btn)
        self.actions_map.append((action, btn))
        return btn

    def addSeparator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout_obj.addWidget(line)

    def refresh(self):
        for action, btn in self.actions_map:
            btn.setText(action.text())
            btn.setToolTip(action.toolTip() or action.text())

class DraggableToolBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.drag_start_pos = None

    def childEvent(self, event):
        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if isinstance(child, QAbstractButton):
                child.installEventFilter(self)
        super().childEvent(event)

    def setup(self):
        """Force install event filter on all existing buttons"""
        for child in self.findChildren(QAbstractButton):
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_pos = event.pos() # Local to button
                
        elif event.type() == QEvent.Type.MouseMove:
            if (event.buttons() & Qt.MouseButton.LeftButton) and self.drag_start_pos:
                if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                    # Find action for this button
                    action = None
                    for act in self.actions():
                        if self.widgetForAction(act) == obj:
                            action = act
                            break
                    
                    if action:
                        self.start_drag(action, obj)
                        # Cancel value press state without triggering click
                        obj.setDown(False)
                        return True
                        
        return super().eventFilter(obj, event)

    def start_drag(self, action, button):
        drag = QDrag(self)
        mime = QMimeData()
        
        # We use action text as ID
        mime.setText(action.text()) 
        mime.setData("application/x-toolbar-action", QByteArray(action.text().encode("utf-8")))
        
        drag.setMimeData(mime)
        
        pixmap = button.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        drag.exec(Qt.DropAction.MoveAction)
        self.drag_start_pos = None # Reset
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-toolbar-action"):
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-toolbar-action"):
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        action_text = event.mimeData().text()
        
        # Find local action being dragged
        source_action = None
        for act in self.actions():
            if act.text() == action_text:
                source_action = act
                break
                
        if not source_action:
            event.ignore()
            return
            
        # Find target action under mouse
        target_action = self.actionAt(event.position().toPoint())
        
        if source_action != target_action:
            self.removeAction(source_action)
            if target_action:
                self.insertAction(target_action, source_action)
            else:
                self.addAction(source_action) # Append to end
                
        event.accept()

class HexWidget(QAbstractScrollArea):
    cursorChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bytes_per_line = 16
        self.line_height = 20
        self.char_width = 10
        self.margin_left = 5
        self.address_width = 80
        self.hex_width = 0
        self.ascii_width = 0
        
        self.data_source = b""
        self.file_size = 0
        
        # Theme
        self.font = QFont("Consolas", 10) # Fallback
        
        # Try to load better monospace fonts
        try:
            fonts = QFontDatabase.families()
            for f in ["JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New"]:
                 if f in fonts:
                     self.font = QFont(f, 10)
                     break
        except:
             pass
                 
        self.theme = THEMES["Dark (Default)"].copy()
        
        # Selection & Cursor
        self.cursor_pos = -1  # Byte index
        self.selection_start = -1
        self.selection_end = -1
        self.cursor_nibble_low = False # True if editing lower nibble
        self.overwrite_mode = True
        
        # Performance
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        
        # Edit Buffer for small modifications
        self.edits = {} # {offset: byte_int}
        self.max_edits_ram = 1024 * 1024 # 1MB limit for simple dict edits before warning
        
        # Undo/Redo
        self.undo_stack = []
        self.redo_stack = []
        self.macro_active = False
        self.macro_buffer = []
        
        # Hover
        self.hover_pos = -1
        self.highlights = {} # {start: (end, color, description)}
        
        # Performance: Cached colors (avoid QColor creation in paintEvent)
        self._cached_colors = {}
        self._update_cached_colors()
        
        # Performance: Debounce updates
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)  # ~60fps max
        self._update_timer.timeout.connect(self._do_viewport_update)
        self._pending_update = False
        
        # Performance: Last inspector offset to skip redundant updates
        self._last_inspector_offset = -1
        
        self.update_metrics()

    def begin_macro(self):
        self.macro_active = True
        self.macro_buffer = []

    def end_macro(self):
        self.macro_active = False
        if self.macro_buffer:
            self.undo_stack.append(self.macro_buffer)
            self.redo_stack.clear()
            if len(self.undo_stack) > MAX_HISTORY:
                self.undo_stack.pop(0)
            self.macro_buffer = []

    def push_edit(self, offset, old_val, new_val):
        edit = (offset, old_val, new_val)
        if self.macro_active:
            self.macro_buffer.append(edit)
        else:
            self.undo_stack.append(edit)
            self.redo_stack.clear()
            if len(self.undo_stack) > MAX_HISTORY:
                self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack: return
        item = self.undo_stack.pop()
        self.redo_stack.append(item)
        
        if isinstance(item, list):
            # Undo Macro (in reverse)
            for offset, old_val, new_val in reversed(item):
                if old_val is None:
                    if offset in self.edits: del self.edits[offset]
                else:
                    self.edits[offset] = old_val
        else:
            # Single Edit
            offset, old_val, new_val = item
            if old_val is None: 
                 if offset in self.edits: del self.edits[offset]
            else:
                 self.edits[offset] = old_val
                 
        self.viewport().update()
        self.cursorChanged.emit(self.cursor_pos)

    def redo(self):
        if not self.redo_stack: return
        item = self.redo_stack.pop()
        self.undo_stack.append(item)
        
        if isinstance(item, list):
            # Redo Macro
            for offset, old_val, new_val in item:
                self.edits[offset] = new_val
        else:
            # Single Edit
            offset, old_val, new_val = item
            self.edits[offset] = new_val
            
        self.viewport().update()
        self.cursorChanged.emit(self.cursor_pos)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Traverse parents to find MainWindow for locale
        mw = self.parent().parent().parent() 
        add_bm = menu.addAction(LOCALE[mw.current_lang]["add_bm"])
        action = menu.exec(self.mapToGlobal(event.pos()))
        if action == add_bm and self.cursor_pos != -1:
            mw.add_bookmark_handler(self.cursor_pos)

    def apply_theme(self, theme_dict):
        self.theme = theme_dict.copy()
        
        # Derive Hex Editor specific colors if missing
        if "hex_fg" not in self.theme: self.theme["hex_fg"] = self.theme.get("input_fg", "#00ff00")
        if "ascii_fg" not in self.theme: self.theme["ascii_fg"] = self.theme.get("fg", "#ffffff")
        if "offset_fg" not in self.theme: self.theme["offset_fg"] = self.theme.get("input_border", "#888888")
        if "sel_bg" not in self.theme: self.theme["sel_bg"] = self.theme.get("input_border", "#0044cc")
        if "sel_fg" not in self.theme: self.theme["sel_fg"] = self.theme.get("bg", "#ffffff")
        if "alt_bg" not in self.theme: self.theme["alt_bg"] = self.theme.get("tree_alt", self.theme["bg"])
        self._update_cached_colors()
        self.viewport().update()
    
    def _update_cached_colors(self):
        """Pre-create QColor objects to avoid allocation in paintEvent"""
        self._cached_colors = {
            "bg": QColor(self.theme.get("bg", "#1e1e1e")),
            "alt_bg": QColor(self.theme.get("alt_bg", "#252525")),
            "offset_fg": QColor(self.theme.get("offset_fg", "#888888")),
            "hex_fg": QColor(self.theme.get("hex_fg", "#00ff00")),
            "ascii_fg": QColor(self.theme.get("ascii_fg", "#ffffff")),
            "sel_bg": QColor(self.theme.get("sel_bg", "#0044cc")),
            "sel_fg": QColor(self.theme.get("sel_fg", "#ffffff")),
        }
    
    def _do_viewport_update(self):
        """Actual viewport update, called by debounce timer"""
        self._pending_update = False
        self.viewport().update()
    
    def schedule_update(self):
        """Debounced viewport update - coalesces multiple updates"""
        if not self._pending_update:
            self._pending_update = True
            self._update_timer.start()
            
    def set_data(self, data):
        self.data_source = data
        self.edits.clear()
        if isinstance(data, (bytes, bytearray)):
            self.file_size = len(data)
        elif isinstance(data, mmap.mmap):
            self.file_size = data.size()
        else:
            self.file_size = 0
            
        self.verticalScrollBar().setRange(0, (self.file_size + self.bytes_per_line - 1) // self.bytes_per_line)
        self.verticalScrollBar().setPageStep(self.viewport().height() // self.line_height)
        self.viewport().update()

    def update_metrics(self):
        fm = QFontMetrics(self.font)
        self.line_height = fm.height() + 2
        self.char_width = fm.horizontalAdvance("W")
        self.address_width = self.char_width * 9  # 8 chars + padding
        self.hex_width = self.char_width * (self.bytes_per_line * 3) 
        self.ascii_width = self.char_width * (self.bytes_per_line + 1)
        self.viewport().update()

    def get_byte(self, offset):
        if 0 <= offset < self.file_size:
            if offset in self.edits:
                return self.edits[offset]
            return self.data_source[offset]
        return 0

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setFont(self.font)
        
        # Backgrounds
        rect = event.rect()
        # Use cached colors
        bg_color = self._cached_colors.get("bg", QColor(0,0,0))
        painter.fillRect(rect, bg_color)
        
        first_line = self.verticalScrollBar().value()
        visible_lines = rect.height() // self.line_height + 2
        
        # Colors
        col_offset = self._cached_colors.get("offset_fg", QColor(100,100,100))
        col_hex = self._cached_colors.get("hex_fg", QColor(0,255,0))
        col_ascii = self._cached_colors.get("ascii_fg", QColor(255,255,255))
        col_sel_bg = self._cached_colors.get("sel_bg", QColor(0,0,255))
        col_sel_fg = self._cached_colors.get("sel_fg", QColor(255,255,255))
        
        # Geometry
        x_hex = self.margin_left + self.address_width + 10
        x_ascii = x_hex + self.hex_width + 20
        y = 0
        
        # Pre-calculation
        char_w = self.char_width
        hex_step = 3 * char_w
        ascii_step = char_w
        
        for line in range(first_line, first_line + visible_lines):
            offset_start = line * self.bytes_per_line
            if offset_start >= self.file_size:
                break
            
            # Draw Line Background (Alternating)
            if line % 2 == 1:
                painter.fillRect(0, y, self.viewport().width(), self.line_height, self._cached_colors.get("alt_bg"))
                
            # Get Data
            data_len = min(self.bytes_per_line, self.file_size - offset_start)
            bytes_list = []
            
            # Optimization: Batch read
            for i in range(data_len):
                off = offset_start + i
                if off in self.edits:
                    bytes_list.append(self.edits[off])
                else:
                    if 0 <= off < self.file_size:
                         bytes_list.append(self.data_source[off])
            
            # Construct Strings
            hex_parts = [f"{b:02X}" for b in bytes_list]
            hex_str = " ".join(hex_parts)
            
            ascii_chars = []
            for b in bytes_list:
                if 32 <= b <= 126:
                    ascii_chars.append(chr(b))
                else:
                    ascii_chars.append(".")
            ascii_str = "".join(ascii_chars)
            
            # --- SELECTION & HOVER CALCULATIONS ---
            sel_indices = set()
            
            # Selection Range
            if self.selection_start != -1:
                s = min(self.selection_start, self.selection_end)
                e = max(self.selection_start, self.selection_end)
                
                start_idx = max(0, s - offset_start)
                end_idx = min(data_len - 1, e - offset_start)
                
                if start_idx <= end_idx and e >= offset_start and s < offset_start + data_len:
                     for k in range(start_idx, end_idx + 1):
                         sel_indices.add(k)

            # Cursor
            if self.cursor_pos != -1:
                if offset_start <= self.cursor_pos < offset_start + data_len:
                    sel_indices.add(self.cursor_pos - offset_start)
                    
            # Hover
            if self.hover_pos != -1:
                 if offset_start <= self.hover_pos < offset_start + data_len:
                     sel_indices.add(self.hover_pos - offset_start)

            # --- PAINTING Highlights (Auto-Analysis) ---
            for start, (end, color, desc) in self.highlights.items():
                s = start
                e = end
                
                # Check intersection
                if not (s >= offset_start + data_len or e < offset_start):
                     h_start_idx = max(0, s - offset_start)
                     h_end_idx = min(data_len - 1, e - offset_start)
                     
                     bg_color = QColor(color) # Copy to avoid modifying shared object
                     bg_color.setAlpha(100) # Semi-transparent
                     
                     for k in range(h_start_idx, h_end_idx + 1):
                         # Highlighting Hex
                         rect_h = QRect(x_hex + k * hex_step, y, hex_step, self.line_height)
                         painter.fillRect(rect_h, bg_color)
                         
                         # Highlighting Ascii
                         rect_a = QRect(x_ascii + k * ascii_step, y, ascii_step, self.line_height)
                         painter.fillRect(rect_a, bg_color)

            # --- PAINTING ---
            
            # 1. Background Highlights
            if sel_indices:
                for k in sel_indices:
                    # Highlight Hex
                    rect_h = QRect(x_hex + k * hex_step, y, hex_step, self.line_height)
                    painter.fillRect(rect_h, col_sel_bg if k + offset_start != self.hover_pos else col_sel_bg.lighter(130))
                    
                    # Highlight Ascii
                    rect_a = QRect(x_ascii + k * ascii_step, y, ascii_step, self.line_height)
                    painter.fillRect(rect_a, col_sel_bg if k + offset_start != self.hover_pos else col_sel_bg.lighter(130))

            # 2. Base Text (Normal Color)
            painter.setPen(col_offset)
            painter.drawText(self.margin_left, y + self.line_height - 4, f"{offset_start:08X}")
            
            painter.setPen(col_hex)
            painter.drawText(x_hex, y + self.line_height - 4, hex_str)
            
            painter.setPen(col_ascii)
            painter.drawText(x_ascii, y + self.line_height - 4, ascii_str)
            
            # 3. Overlay Text (Selected Color)
            if sel_indices:
                painter.setPen(col_sel_fg)
                for k in sel_indices:
                    # Redraw Hex
                    rect_h = QRect(x_hex + k * hex_step, y, hex_step, self.line_height)
                    painter.drawText(rect_h, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, hex_parts[k])
                    
                    # Redraw Ascii
                    rect_a = QRect(x_ascii + k * ascii_step, y, ascii_step, self.line_height)
                    painter.drawText(rect_a, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, ascii_chars[k])

            y += self.line_height

    def mouseMoveEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()
        
        # Calculate hover pos
        line = (y // self.line_height) + self.verticalScrollBar().value()
        x_hex_start = self.margin_left + self.address_width + 10
        x_ascii_start = x_hex_start + self.hex_width + 20
        
        col = -1
        if x_hex_start <= x < x_hex_start + self.hex_width:
            col = int((x - x_hex_start) // (3 * self.char_width))
        elif x_ascii_start <= x < x_ascii_start + self.ascii_width:
            col = int((x - x_ascii_start) // self.char_width)
            
        if col != -1 and 0 <= col < self.bytes_per_line:
            offset = line * self.bytes_per_line + col
            if 0 <= offset < self.file_size:
                if self.hover_pos != offset:
                    self.hover_pos = offset
                    self.schedule_update()
                    
                # Tooltip for highlights
                tooltip_text = ""
                for start, (end, color, desc) in self.highlights.items():
                    if start <= offset <= end:
                         tooltip_text = desc
                         break
                
                if tooltip_text:
                    QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
                else:
                    QToolTip.hideText()
                    
                return

        if self.hover_pos != -1:
            self.hover_pos = -1
            self.schedule_update()
            QToolTip.hideText()
            
        # Handle dragging (selection)
        if event.buttons() & Qt.MouseButton.LeftButton:
            # Re-calculate generic hover if out of bounds (for drag scroll/select)
            line = (y // self.line_height) + self.verticalScrollBar().value()
            col = -1
            if x_hex_start <= x < x_hex_start + self.hex_width:
                col = int((x - x_hex_start) // (3 * self.char_width))
            elif x_ascii_start <= x < x_ascii_start + self.ascii_width:
                col = int((x - x_ascii_start) // self.char_width)
                 
            if col != -1:
                hover_idx = line * self.bytes_per_line + col
                if 0 <= hover_idx < self.file_size:
                    self.selection_end = hover_idx
                    self.cursor_pos = self.selection_end
                    self.viewport().update()
                    self.cursorChanged.emit(self.cursor_pos)

    def leaveEvent(self, event):
        self.hover_pos = -1
        self.viewport().update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            line = (y // self.line_height) + self.verticalScrollBar().value()
            col = -1
            
            x_hex_start = self.margin_left + self.address_width + 10
            x_ascii_start = x_hex_start + self.hex_width + 20
            
            if x_hex_start <= x < x_hex_start + self.hex_width:
                col = (x - x_hex_start) // (3 * self.char_width)
            elif x_ascii_start <= x < x_ascii_start + self.ascii_width:
                col = (x - x_ascii_start) // self.char_width
                
            if 0 <= col < self.bytes_per_line:
                offset = line * self.bytes_per_line + col
                if offset < self.file_size:
                    self.cursor_pos = offset
                    self.selection_start = offset
                    self.selection_end = offset
                    self.cursor_nibble_low = False
                    self.viewport().update()
                    self.cursorChanged.emit(self.cursor_pos)

    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key.Key_Left:
            if self.cursor_pos > 0: self.cursor_pos -= 1
        elif key == Qt.Key.Key_Right:
            if self.cursor_pos < self.file_size - 1: self.cursor_pos += 1
        elif key == Qt.Key.Key_Up:
            if self.cursor_pos >= self.bytes_per_line: self.cursor_pos -= self.bytes_per_line
        elif key == Qt.Key.Key_Down:
            if self.cursor_pos + self.bytes_per_line < self.file_size: self.cursor_pos += self.bytes_per_line
        
        # Hex input
        if (key >= Qt.Key.Key_0 and key <= Qt.Key.Key_9) or (key >= Qt.Key.Key_A and key <= Qt.Key.Key_F):
            if self.cursor_pos != -1:
                val = key - Qt.Key.Key_0 if key <= Qt.Key.Key_9 else key - Qt.Key.Key_A + 10
                self.edit_byte(val)
                
        self.selection_start = self.cursor_pos
        self.selection_end = self.cursor_pos
        self.cursorChanged.emit(self.cursor_pos)
        self.viewport().update()
        
    def edit_byte(self, nibble):
        if self.cursor_pos == -1: return
        
        current_byte = self.get_byte(self.cursor_pos)
        old_val = current_byte
        new_byte = current_byte
        
        if not self.cursor_nibble_low:
             # High nibble
             new_byte = (nibble << 4) | (current_byte & 0x0F)
             self.cursor_nibble_low = True
        else:
             # Low nibble
             new_byte = (current_byte & 0xF0) | nibble
             self.cursor_nibble_low = False
             if self.cursor_pos < self.file_size - 1:
                 self.cursor_pos += 1
         
        self.push_edit(self.cursor_pos if self.cursor_nibble_low else self.cursor_pos - 1, old_val, new_byte)
        self.edits[self.cursor_pos if self.cursor_nibble_low else self.cursor_pos - 1] = new_byte

    def verticalScrollBar(self):
        return super().verticalScrollBar()

class SearchDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Find")
        layout = QHBoxLayout(self)
        self.input_search = QLineEdit()
        self.mode = "hex"  # hex, ascii
        layout.addWidget(QLabel("Pattern:"))
        layout.addWidget(self.input_search)
        btn = QPushButton("Find")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class GoToDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Go To Offset")
        layout = QHBoxLayout(self)
        self.input_offset = QLineEdit()
        layout.addWidget(QLabel("Offset (Hex):"))
        layout.addWidget(self.input_offset)
        btn = QPushButton("Go")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class BaseConverterDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Base Converter")
        self.setWindowFlags(Qt.WindowType.Tool)
        layout = QFormLayout(self)
        
        self.inp_hex = QLineEdit()
        self.inp_dec = QLineEdit()
        self.inp_bin = QLineEdit()
        
        layout.addRow("Hex:", self.inp_hex)
        layout.addRow("Dec:", self.inp_dec)
        layout.addRow("Bin:", self.inp_bin)
        
        self.inp_hex.textChanged.connect(lambda t: self.convert("hex", t))
        self.inp_dec.textChanged.connect(lambda t: self.convert("dec", t))
        self.inp_bin.textChanged.connect(lambda t: self.convert("bin", t))
        
        self.updating = False

    def convert(self, source, text):
        if self.updating or not text: return
        self.updating = True
        try:
            val = 0
            if source == "hex": val = int(text, 16)
            elif source == "dec": val = int(text, 10)
            elif source == "bin": val = int(text, 2)
            
            if source != "hex": self.inp_hex.setText(f"{val:X}")
            if source != "dec": self.inp_dec.setText(f"{val}")
            if source != "bin": self.inp_bin.setText(f"{val:b}")
        except:
            pass
        self.updating = False

class BitwiseDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Bitwise Operations")
        layout = QVBoxLayout(self)
        
        self.combo_op = QComboBox()
        self.combo_op.addItems(["AND", "OR", "XOR", "NOT", "Shift Left", "Shift Right", "Rotate Left", "Rotate Right"])
        layout.addWidget(QLabel("Operation:"))
        layout.addWidget(self.combo_op)
        
        self.inp_operand = QLineEdit()
        self.inp_operand.setPlaceholderText("Operand (Hex)")
        layout.addWidget(QLabel("Operand (Hex):"))
        layout.addWidget(self.inp_operand)
        
        btn = QPushButton("Apply")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
        self.combo_op.currentTextChanged.connect(self.on_op_change)
        
    def on_op_change(self, text):
        self.inp_operand.setEnabled(text != "NOT")

class ChecksumDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle(LOCALE[parent.current_lang]["checksum_title"])
        self.setMinimumWidth(450)
        self.data = data_source
        
        layout = QFormLayout(self)
        
        self.res_crc16 = QLineEdit()
        self.res_crc32 = QLineEdit()
        self.res_md5 = QLineEdit()
        self.res_sha1 = QLineEdit()
        self.res_sha256 = QLineEdit()
        self.res_sha512 = QLineEdit()
        
        for w in [self.res_crc16, self.res_crc32, self.res_md5, self.res_sha1, self.res_sha256, self.res_sha512]:
            w.setReadOnly(True)
            
        layout.addRow("CRC16:", self.res_crc16)
        layout.addRow("CRC32:", self.res_crc32)
        layout.addRow("MD5:", self.res_md5)
        layout.addRow("SHA-1:", self.res_sha1)
        layout.addRow("SHA-256:", self.res_sha256)
        layout.addRow("SHA-512:", self.res_sha512)
        
        self.btn_calc = QPushButton(LOCALE[parent.current_lang]["calc"])
        self.btn_calc.clicked.connect(self.calculate)
        layout.addRow(self.btn_calc)
        
    def calculate(self):
        if not self.data: return
        
        self.btn_calc.setEnabled(False)
        
        if not hasattr(self, 'progress_bar'):
             self.progress_bar = QProgressBar()
             self.layout().addRow(self.progress_bar)
        
        self.progress_bar.setValue(0)
        self.progress_bar.show()
             
        self.worker = ChecksumWorker(self.data)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, results):
        self.res_crc16.setText(results["CRC16"])
        self.res_crc32.setText(results["CRC32"])
        self.res_md5.setText(results["MD5"])
        self.res_sha1.setText(results["SHA-1"])
        self.res_sha256.setText(results["SHA-256"])
        self.res_sha512.setText(results["SHA-512"])
        
        self.progress_bar.hide()
        self.btn_calc.setEnabled(True)
            
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

class SignatureDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.setWindowTitle("File Signature Analysis")
        self.setMinimumWidth(500)
        self.data = data_source
        
        layout = QVBoxLayout(self)
        
        # Results
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        btn_analyze = QPushButton("Analyze")
        btn_analyze.clicked.connect(self.analyze)
        layout.addWidget(btn_analyze)
        
        # Auto-analyze on open
        self.analyze()
        
    def analyze(self):
        if not self.data or len(self.data) < 4:
            self.result_text.setText("Not enough data to analyze.")
            return
            
        # Read first bytes
        header = bytes(self.data[:32])
        
        results = []
        results.append(f"First 32 bytes: {header.hex().upper()}")
        results.append("")
        
        # Signature database
        SIGNATURES = [
            (b"\x89PNG\r\n\x1a\n", "PNG Image"),
            (b"\xff\xd8\xff", "JPEG Image"),
            (b"GIF87a", "GIF Image (87a)"),
            (b"GIF89a", "GIF Image (89a)"),
            (b"PK\x03\x04", "ZIP Archive / Office Document"),
            (b"Rar!\x1a\x07", "RAR Archive"),
            (b"7z\xbc\xaf\x27\x1c", "7-Zip Archive"),
            (b"\x1f\x8b\x08", "GZIP Archive"),
            (b"BZh", "BZIP2 Archive"),
            (b"%PDF", "PDF Document"),
            (b"\x7fELF", "ELF Executable (Linux)"),
            (b"MZ", "DOS/Windows Executable"),
            (b"\xca\xfe\xba\xbe", "Mach-O Fat Binary"),
            (b"\xfe\xed\xfa\xce", "Mach-O 32-bit"),
            (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit"),
            (b"RIFF", "RIFF Container (WAV/AVI)"),
            (b"OggS", "OGG Container"),
            (b"fLaC", "FLAC Audio"),
            (b"ID3", "MP3 Audio (ID3 Tag)"),
            (b"\xff\xfb", "MP3 Audio (Frame)"),
            (b"\x00\x00\x00\x18ftypmp4", "MP4 Video"),
            (b"\x00\x00\x00\x1cftypisom", "MP4 Video (ISOM)"),
            (b"\x00\x00\x01\xba", "MPEG Video"),
            (b"\x00\x00\x01\xb3", "MPEG Video"),
            (b"\x7f\x43\x4e\x54", "PS4 CNT File"),
            (b"\x7f\x50\x4b\x47", "PS4 PKG File"),
            (b"SQLite format 3", "SQLite Database"),
            (b"\xd0\xcf\x11\xe0", "Microsoft Compound Document"),
        ]
        
        detected = []
        for sig, name in SIGNATURES:
            if header.startswith(sig):
                detected.append(name)
                
        if detected:
            results.append(LOCALE[self.parent().current_lang]["detected"])
            for d in detected:
                results.append(f"  ✓ {d}")
        else:
            results.append(LOCALE[self.parent().current_lang]["unknown"])
            results.append("")
            results.append("Common signatures not matched.")
            
        self.result_text.setText("\n".join(results))

class StringsDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.data = data_source
        self.parent_window = parent
        self.setWindowTitle(LOCALE[self.parent_window.current_lang]["strings"])
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Options
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel(LOCALE[self.parent_window.current_lang]["min_len"]))
        self.spin_min = QSpinBox()
        self.spin_min.setRange(3, 100)
        self.spin_min.setValue(4)
        opt_layout.addWidget(self.spin_min)
        
        self.chk_ascii = QCheckBox(LOCALE[self.parent_window.current_lang]["ascii"])
        self.chk_ascii.setChecked(True)
        opt_layout.addWidget(self.chk_ascii)
        
        self.chk_unicode = QCheckBox(LOCALE[self.parent_window.current_lang]["unicode"])
        self.chk_unicode.setChecked(True)
        opt_layout.addWidget(self.chk_unicode)
        
        btn_extract = QPushButton(LOCALE[self.parent_window.current_lang]["extract"])
        btn_extract.clicked.connect(self.extract)
        opt_layout.addWidget(btn_extract)
        
        layout.addLayout(opt_layout)
        
        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            LOCALE[self.parent_window.current_lang]["offset"],
            LOCALE[self.parent_window.current_lang]["type"],
            LOCALE[self.parent_window.current_lang]["string"]
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemDoubleClicked.connect(self.goto_offset)
        layout.addWidget(self.table)
        
        # Status
        self.lbl_status = QLabel(LOCALE[self.parent_window.current_lang]["ready"])
        layout.addWidget(self.lbl_status)
        
    def extract(self):
        if not self.data:
            return
            
        min_len = self.spin_min.value()
        results = []
        
        self.lbl_status.setText(LOCALE[self.parent_window.current_lang]["extracting"])
        QApplication.processEvents()
        
        data_bytes = bytes(self.data)
        
        # ASCII Strings
        if self.chk_ascii.isChecked():
            pattern = rb'[\x20-\x7E]{' + str(min_len).encode() + rb',}'
            for m in re.finditer(pattern, data_bytes):
                try:
                    s = m.group().decode('ascii')
                    results.append((m.start(), "ASCII", s))
                except:
                    pass
                    
        # Unicode (UTF-16 LE)
        if self.chk_unicode.isChecked():
            # Simple heuristic: look for sequences of printable chars followed by null
            i = 0
            current_str = []
            start_offset = 0
            while i < len(data_bytes) - 1:
                if 0x20 <= data_bytes[i] <= 0x7E and data_bytes[i+1] == 0:
                    if not current_str:
                        start_offset = i
                    current_str.append(chr(data_bytes[i]))
                    i += 2
                else:
                    if len(current_str) >= min_len:
                        results.append((start_offset, "UTF-16", "".join(current_str)))
                    current_str = []
                    i += 1
            if len(current_str) >= min_len:
                results.append((start_offset, "UTF-16", "".join(current_str)))
        
        # Populate table
        self.table.setRowCount(len(results))
        for row, (offset, stype, s) in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(f"{offset:08X}"))
            self.table.setItem(row, 1, QTableWidgetItem(stype))
            # Truncate long strings for display
            display_s = s if len(s) <= 100 else s[:100] + "..."
            self.table.setItem(row, 2, QTableWidgetItem(display_s))
            
        self.lbl_status.setText(LOCALE[self.parent_window.current_lang]["found"].format(len(results)))
        
    def goto_offset(self, item):
        row = item.row()
        offset_str = self.table.item(row, 0).text()
        try:
            offset = int(offset_str, 16)
            self.parent_window.hex_view.cursor_pos = offset
            self.parent_window.hex_view.selection_start = offset
            self.parent_window.hex_view.selection_end = offset
            
            line = offset // self.parent_window.hex_view.bytes_per_line
            self.parent_window.hex_view.verticalScrollBar().setValue(line)
            self.parent_window.hex_view.viewport().update()
        except:
            pass

class BookmarksWidget(QWidget):
    goToSignal = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to MainWindow
        
        t_layout = QVBoxLayout(self)
        t_layout.setContentsMargins(0,0,0,0)
        
        self.title = QLabel(LOCALE[self.main_window.current_lang]["bookmarks"] if self.main_window else "Bookmarks")
        self.title.setStyleSheet("font-weight: bold;")
        t_layout.addWidget(self.title)
        
        self.list = QListWidget()
        t_layout.addWidget(self.list)
        
        self.btn_remove = QPushButton(LOCALE[self.main_window.current_lang]["remove"] if self.main_window else "Remove")
        self.btn_remove.clicked.connect(self.remove_bookmark)
        t_layout.addWidget(self.btn_remove)
        
        self.list.itemDoubleClicked.connect(self.on_click)
        
    def add_bookmark(self, offset, desc):
        item = f"0x{offset:08X}: {desc}"
        self.list.addItem(item)
        
    def remove_bookmark(self):
        row = self.list.currentRow()
        if row != -1:
            self.list.takeItem(row)

    def update_ui(self):
        if self.main_window:
            self.title.setText(LOCALE[self.main_window.current_lang]["bookmarks"]) 
            self.btn_remove.setText(LOCALE[self.main_window.current_lang]["remove"])
            
    def on_click(self, item):
        text = item.text()
        offset = int(text.split(":")[0], 16)
        self.goToSignal.emit(offset)

class HotspotsWidget(QWidget):
    """Track frequently accessed offsets for quick navigation"""
    goToSignal = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.hotspots = {}  # offset -> access_count
        self.max_hotspots = 20  # Maximum tracked hotspots
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.title = QLabel(LOCALE.get(self.main_window.current_lang, {}).get("hotspots", "🔥 Hotspots") if self.main_window else "🔥 Hotspots")
        self.title.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title)
        
        self.list = QListWidget()
        layout.addWidget(self.list)
        
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton(LOCALE.get(self.main_window.current_lang, {}).get("clear", "Clear") if self.main_window else "Clear")
        self.btn_clear.clicked.connect(self.clear_hotspots)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)
        
        self.list.itemDoubleClicked.connect(self.on_click)
        
    def track_access(self, offset):
        """Track access to an offset, auto-incrementing its count"""
        # Round to nearest 16-byte boundary for grouping
        aligned_offset = (offset // 16) * 16
        
        if aligned_offset in self.hotspots:
            self.hotspots[aligned_offset] += 1
        else:
            self.hotspots[aligned_offset] = 1
            
        # Trim if too many hotspots
        if len(self.hotspots) > self.max_hotspots:
            # Remove least accessed
            min_offset = min(self.hotspots, key=self.hotspots.get)
            del self.hotspots[min_offset]
            
        self.refresh_list()
        
    def refresh_list(self):
        """Refresh the list, sorted by access count (most accessed first)"""
        self.list.clear()
        sorted_hotspots = sorted(self.hotspots.items(), key=lambda x: x[1], reverse=True)
        
        for offset, count in sorted_hotspots[:10]:  # Show top 10
            item = f"0x{offset:08X} ({count}x)"
            self.list.addItem(item)
            
    def clear_hotspots(self):
        self.hotspots.clear()
        self.list.clear()
        
    def on_click(self, item):
        text = item.text()
        # Parse "0x00001000 (5x)"
        offset_str = text.split(" ")[0]
        offset = int(offset_str, 16)
        self.goToSignal.emit(offset)
        
    def update_ui(self):
        if self.main_window:
            self.title.setText(LOCALE.get(self.main_window.current_lang, {}).get("hotspots", "🔥 Hotspots"))
            self.btn_clear.setText(LOCALE.get(self.main_window.current_lang, {}).get("clear", "Clear"))


class BitwiseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LOCALE[parent.current_lang]["bitwise"] if parent else "Bitwise Operations")
        layout = QFormLayout(self)
        
        self.combo_op = QComboBox()
        self.combo_op.addItems(["AND", "OR", "XOR", "NOT", 
                                "Shift Left", "Shift Right", 
                                "Rotate Left", "Rotate Right"])
        layout.addRow("Operation:", self.combo_op)
        
        self.inp_operand = QLineEdit("00")
        layout.addRow("Operand (Hex):", self.inp_operand)
        
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

class BaseConverterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LOCALE[parent.current_lang]["base_conv"] if parent else "Base Converter")
        layout = QFormLayout(self)
        
        self.inp_dec = QLineEdit()
        self.inp_hex = QLineEdit()
        self.inp_bin = QLineEdit()
        self.inp_oct = QLineEdit()
        
        layout.addRow("Decimal:", self.inp_dec)
        layout.addRow("Hexadecimal:", self.inp_hex)
        layout.addRow("Binary:", self.inp_bin)
        layout.addRow("Octal:", self.inp_oct)
        
        self.inp_dec.textChanged.connect(lambda t: self.convert("dec", t))
        self.inp_hex.textChanged.connect(lambda t: self.convert("hex", t))
        self.inp_bin.textChanged.connect(lambda t: self.convert("bin", t))
        self.inp_oct.textChanged.connect(lambda t: self.convert("oct", t))
        
        self.updating = False
        
    def convert(self, source, text):
        if self.updating or not text: return
        self.updating = True
        try:
            val = 0
            if source == "dec": val = int(text)
            elif source == "hex": val = int(text, 16)
            elif source == "bin": val = int(text, 2)
            elif source == "oct": val = int(text, 8)
            
            if source != "dec": self.inp_dec.setText(str(val))
            if source != "hex": self.inp_hex.setText(f"{val:X}")
            if source != "bin": self.inp_bin.setText(f"{val:b}")
            if source != "oct": self.inp_oct.setText(f"{val:o}")
        except:
            pass
        self.updating = False

class EntropyDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.setWindowTitle(LOCALE[parent.current_lang]["entropy"] if "entropy" in LOCALE[parent.current_lang] else "Entropy Analysis")
        self.resize(800, 400)
        self.data = data_source
        self.parent_window = parent
        
        layout = QVBoxLayout(self)
        
        # Canvas
        self.canvas = QWidget()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.paintEvent = self.paint_canvas
        layout.addWidget(self.canvas)
        
        # Info
        self.lbl_info = QLabel("Hover over graph to see details")
        layout.addWidget(self.lbl_info)
        
        # Calc logic
        self.blocks = []
        self.block_size = 256
        self.calculate_entropy()
        
        self.canvas.setMouseTracking(True)
        self.canvas.mouseMoveEvent = self.on_mouse_move
        
    def calculate_entropy(self):
        if not self.data: return
        
        data_len = len(self.data)
        self.blocks = []
        
        # Optimization for large files: limit points to 2000 roughly
        if data_len > 2000 * 256:
             self.block_size = data_len // 2000
             
        for i in range(0, data_len, self.block_size):
            chunk = self.data[i:i+self.block_size]
            if not chunk: break
            
            # Shannon Entropy
            counts = [0] * 256
            for b in chunk: counts[b] += 1
            
            entropy = 0
            len_chunk = len(chunk)
            for count in counts:
                if count > 0:
                    p = count / len_chunk
                    entropy -= p * math.log2(p)
            
            self.blocks.append(entropy)
            
    def paint_canvas(self, event):
        painter = QPainter(self.canvas)
        painter.fillRect(self.canvas.rect(), QColor("#1e1e1e"))
        
        if not self.blocks: return
        
        w = self.canvas.width()
        h = self.canvas.height()
        
        num_blocks = len(self.blocks)
        if num_blocks == 0: return
        
        # Draw grid
        painter.setPen(QColor("#333333"))
        for i in range(1, 9):
            y = h - (i * h / 8)
            painter.drawLine(0, int(y), w, int(y))
            
        block_w = w / num_blocks
        
        # Draw graph
        path = pyqtSignal # Just a dummy ref, actually we use QPainterPath or simple lines
        
        prev_x = 0
        prev_y = h - (self.blocks[0] / 8.0) * h
        
        painter.setPen(QColor("#00ff00"))
        
        for i in range(1, num_blocks):
            val = self.blocks[i]
            x = i * block_w
            y = h - (val / 8.0) * h
            
            # Color coding based on entropy
            if val > 7.0: painter.setPen(QColor("#ff5555")) # Red for likely compressed/encrypted
            elif val > 4.0: painter.setPen(QColor("#ffff55")) # Yellow
            else: painter.setPen(QColor("#55ff55")) # Green
            
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
            prev_x = x
            prev_y = y
            
    def on_mouse_move(self, event):
        if not self.blocks: return
        w = self.canvas.width()
        x = event.pos().x()
        
        idx = int((x / w) * len(self.blocks))
        if 0 <= idx < len(self.blocks):
            val = self.blocks[idx]
            offset = idx * self.block_size
            self.lbl_info.setText(f"Offset: {offset:08X} - {offset+self.block_size:08X} | Entropy: {val:.4f} bits/byte")

# --- WORKERS ---

class ChecksumWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.running = True
        
        # Precompute CRC16 Table (CCITT)
        self.crc16_table = []
        for i in range(256):
            crc = i << 8
            for _ in range(8):
                if crc & 0x8000: crc = (crc << 1) ^ 0x1021
                else: crc <<= 1
                crc &= 0xFFFF
            self.crc16_table.append(crc)
        
    def run(self):
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        sha512 = hashlib.sha512()
        crc32 = 0
        crc16 = 0xFFFF
        
        chunk_size = 1024 * 1024 # 1MB
        total = len(self.data)
        processed = 0
        
        try:
            for i in range(0, total, chunk_size):
                if not self.running: break
                
                chunk = self.data[i:i+chunk_size]
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
                crc32 = zlib.crc32(chunk, crc32)
                
                # Update CRC16 using binascii (fast C implementation)
                crc16 = binascii.crc_hqx(chunk, crc16)
                
                processed += len(chunk)
                self.progress.emit(int(processed * 100 / total))
                
            results = {
                "MD5": md5.hexdigest().upper(),
                "SHA-1": sha1.hexdigest().upper(),
                "SHA-256": sha256.hexdigest().upper(),
                "SHA-512": sha512.hexdigest().upper(),
                "CRC32": f"{crc32 & 0xFFFFFFFF:08X}",
                "CRC16": f"{crc16:04X}"
            }
            self.finished.emit(results)
        except Exception as e:
            pass

    def stop(self):
        self.running = False


class ByteMapWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list) 
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.running = True
        
    def run(self):
        histogram = [0] * 256
        chunk_size = 1024 * 1024 # 1MB
        total = len(self.data)
        processed = 0
        
        try:
            for i in range(0, total, chunk_size):
                if not self.running: break
                
                chunk = self.data[i:i+chunk_size]
                
                # Fast histogram calculation
                # Iterating bytes yields ints (0-255)
                for b in chunk:
                    histogram[b] += 1
                
                processed += len(chunk)
                if total > 0:
                    self.progress.emit(int(processed * 100 / total))
            
            self.finished.emit(histogram)
        except Exception as e:
            pass

    def stop(self):
        self.running = False


# --- NEW DIALOGS v1.0 ---

class DiffDialog(QDialog):
    """Compare two binary files and show differences"""
    def __init__(self, parent, data1, file1_name="File 1"):
        super().__init__(parent)
        self.parent_window = parent
        self.data1 = data1
        self.data2 = None
        self.differences = []
        self.setWindowTitle(LOCALE[parent.current_lang]["diff"])
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # File selection
        top_layout = QHBoxLayout()
        self.lbl_file1 = QLabel(LOCALE[parent.current_lang]["file_a"] + f": {file1_name}")
        top_layout.addWidget(self.lbl_file1)
        
        btn_select = QPushButton(LOCALE[parent.current_lang]["select_file"])
        btn_select.clicked.connect(self.select_file2)
        top_layout.addWidget(btn_select)
        
        self.lbl_file2 = QLabel(LOCALE[parent.current_lang]["file_b"] + ": ---")
        top_layout.addWidget(self.lbl_file2)
        
        btn_compare = QPushButton(LOCALE[parent.current_lang]["compare"])
        btn_compare.clicked.connect(self.compare)
        top_layout.addWidget(btn_compare)
        layout.addLayout(top_layout)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([LOCALE[parent.current_lang]["offset"], LOCALE[parent.current_lang]["file_a"], LOCALE[parent.current_lang]["file_b"], "Diff"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemDoubleClicked.connect(self.goto_diff)
        layout.addWidget(self.table)
        
        self.lbl_status = QLabel(LOCALE[parent.current_lang]["ready"])
        layout.addWidget(self.lbl_status)
        
    def select_file2(self):
        fname, _ = QFileDialog.getOpenFileName(self, LOCALE[self.parent_window.current_lang]["open"])
        if fname:
            try:
                with open(fname, "rb") as f:
                    self.data2 = f.read()
                self.lbl_file2.setText(LOCALE[self.parent_window.current_lang]["file_b"] + f": {os.path.basename(fname)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                
    def compare(self):
        if self.data2 is None:
            QMessageBox.warning(self, LOCALE[self.parent_window.current_lang]["warning"], LOCALE[self.parent_window.current_lang]["select_file"])
            return
            
        self.differences = []
        len1, len2 = len(self.data1), len(self.data2)
        max_len = max(len1, len2)
        
        for i in range(max_len):
            b1 = self.data1[i] if i < len1 else None
            b2 = self.data2[i] if i < len2 else None
            if b1 != b2:
                self.differences.append((i, b1, b2))
                
        if not self.differences:
            self.lbl_status.setText(LOCALE[self.parent_window.current_lang]["no_diff"])
            self.table.setRowCount(0)
            return
            
        self.table.setRowCount(len(self.differences))
        for row, (off, b1, b2) in enumerate(self.differences):
            self.table.setItem(row, 0, QTableWidgetItem(f"{off:08X}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"{b1:02X}" if b1 is not None else "---"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{b2:02X}" if b2 is not None else "---"))
            self.table.setItem(row, 3, QTableWidgetItem("≠"))
            
        self.lbl_status.setText(f"{LOCALE[self.parent_window.current_lang]['differences']}: {len(self.differences)}")
        
    def goto_diff(self, item):
        row = item.row()
        offset = self.differences[row][0]
        self.parent_window.goto(offset)

class RegexSearchDialog(QDialog):
    """Enhanced search with regex and wildcard support"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.results = []
        self.setWindowTitle(LOCALE[parent.current_lang]["regex_search"])
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Search input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(LOCALE[parent.current_lang]["pattern"] + ":"))
        self.input_pattern = QLineEdit()
        self.input_pattern.setPlaceholderText("48 65 ?? ?? 6F  or  Hello")
        input_layout.addWidget(self.input_pattern)
        layout.addLayout(input_layout)
        
        # Options
        opt_layout = QHBoxLayout()
        self.chk_hex = QCheckBox("Hex")
        self.chk_hex.setChecked(True)
        opt_layout.addWidget(self.chk_hex)
        
        self.chk_regex = QCheckBox("Regex")
        opt_layout.addWidget(self.chk_regex)
        
        opt_layout.addWidget(QLabel(LOCALE[parent.current_lang]["wildcard"]))
        opt_layout.addStretch()
        
        btn_find = QPushButton(LOCALE[parent.current_lang]["find_all"])
        btn_find.clicked.connect(self.find_all)
        opt_layout.addWidget(btn_find)
        layout.addLayout(opt_layout)
        
        # Results
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([LOCALE[parent.current_lang]["offset"], "Preview"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self.goto_result)
        layout.addWidget(self.table)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        
    def find_all(self):
        pattern_str = self.input_pattern.text().strip()
        if not pattern_str:
            return
            
        data = self.parent_window.mmap_obj if self.parent_window.mmap_obj else self.parent_window.hex_view.data_source
        if not data:
            return
            
        self.results = []
        data_bytes = bytes(data)
        
        if self.chk_hex.isChecked():
            # Hex pattern with ?? wildcards
            parts = pattern_str.split()
            pattern = b""
            mask = []
            for p in parts:
                if p == "??" or p == "?":
                    pattern += b"\x00"
                    mask.append(False)
                else:
                    try:
                        pattern += bytes.fromhex(p)
                        mask.append(True)
                    except:
                        pass
            
            # Search with mask
            plen = len(pattern)
            for i in range(len(data_bytes) - plen + 1):
                match = True
                for j in range(plen):
                    if mask[j] and data_bytes[i+j] != pattern[j]:
                        match = False
                        break
                if match:
                    self.results.append(i)
        else:
            # Text search or regex
            if self.chk_regex.isChecked():
                import re
                try:
                    for m in re.finditer(pattern_str.encode(), data_bytes):
                        self.results.append(m.start())
                except:
                    pass
            else:
                pattern = pattern_str.encode()
                idx = 0
                while True:
                    pos = data_bytes.find(pattern, idx)
                    if pos == -1:
                        break
                    self.results.append(pos)
                    idx = pos + 1
                    
        # Display results
        self.table.setRowCount(len(self.results))
        for row, off in enumerate(self.results[:1000]):  # Limit display
            self.table.setItem(row, 0, QTableWidgetItem(f"{off:08X}"))
            preview = data_bytes[off:off+16].hex(" ").upper()
            self.table.setItem(row, 1, QTableWidgetItem(preview))
            
        self.lbl_status.setText(f"Found: {len(self.results)}")
        
    def goto_result(self, item):
        row = item.row()
        if row < len(self.results):
            self.parent_window.goto(self.results[row])

class ByteMapDialog(QDialog):
    """Visual byte map and histogram"""
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.parent_window = parent
        self.data = data_source
        self.setWindowTitle(LOCALE[parent.current_lang]["byte_map"])
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Canvas for byte map
        self.canvas = QWidget()
        self.canvas.setMinimumHeight(256)
        self.canvas.paintEvent = self.paint_map
        self.canvas.mousePressEvent = self.on_click
        layout.addWidget(self.canvas)
        
        # Histogram
        self.hist_canvas = QWidget()
        self.hist_canvas.setMinimumHeight(150)
        self.hist_canvas.paintEvent = self.paint_histogram
        layout.addWidget(self.hist_canvas)
        
        self.lbl_info = QLabel(LOCALE[parent.current_lang]["histogram"])
        layout.addWidget(self.lbl_info)
        
        # Calculate histogram
        self.histogram = [0] * 256
        if self.data:
            self.progress_bar = QProgressBar()
            layout.addWidget(self.progress_bar)
            
            self.worker = ByteMapWorker(self.data)
            self.worker.progress.connect(self.progress_bar.setValue)
            self.worker.finished.connect(self.on_calculation_finished)
            self.worker.start()
            
    def on_calculation_finished(self, histogram):
        self.histogram = histogram
        self.progress_bar.hide()
        self.hist_canvas.update()
        self.canvas.update()
        
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()
                
    def paint_map(self, event):
        if not self.data:
            return
        painter = QPainter(self.canvas)
        w, h = self.canvas.width(), self.canvas.height()
        
        # Draw byte density map
        block_size = max(1, len(self.data) // (w * h // 4))
        cols = w // 2
        rows = h // 2
        
        for y in range(rows):
            for x in range(cols):
                idx = (y * cols + x) * block_size
                if idx < len(self.data):
                    val = self.data[idx]
                    # Color by value
                    r = val
                    g = (255 - val) // 2
                    b = 255 - val
                    painter.fillRect(x*2, y*2, 2, 2, QColor(r, g, b))
                    
    def paint_histogram(self, event):
        painter = QPainter(self.hist_canvas)
        painter.fillRect(self.hist_canvas.rect(), QColor("#1e1e1e"))
        
        if not self.histogram:
            return
            
        w, h = self.hist_canvas.width(), self.hist_canvas.height()
        max_val = max(self.histogram) if max(self.histogram) > 0 else 1
        bar_w = w / 256
        
        for i, count in enumerate(self.histogram):
            bar_h = (count / max_val) * (h - 10)
            color = QColor.fromHsv(i * 360 // 256, 200, 200)
            painter.fillRect(int(i * bar_w), int(h - bar_h), max(1, int(bar_w)), int(bar_h), color)
            
    def on_click(self, event):
        if not self.data:
            return
        w, h = self.canvas.width(), self.canvas.height()
        x, y = event.pos().x(), event.pos().y()
        cols = w // 2
        block_size = max(1, len(self.data) // (w * h // 4))
        idx = ((y // 2) * cols + (x // 2)) * block_size
        if 0 <= idx < len(self.data):
            self.parent_window.goto(idx)

class PatchDialog(QDialog):
    """Create and apply IPS-style patches"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(LOCALE[parent.current_lang]["patches"])
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Current edits display
        layout.addWidget(QLabel(LOCALE[parent.current_lang]["current_edits"] + ":"))
        self.edit_list = QListWidget()
        layout.addWidget(self.edit_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        btn_export = QPushButton(LOCALE[parent.current_lang]["export_patch"])
        btn_export.clicked.connect(self.export_patch)
        btn_layout.addWidget(btn_export)
        
        btn_import = QPushButton(LOCALE[parent.current_lang]["import_patch"])
        btn_import.clicked.connect(self.import_patch)
        btn_layout.addWidget(btn_import)
        
        btn_apply = QPushButton(LOCALE[parent.current_lang]["apply_patch"])
        btn_apply.clicked.connect(self.apply_patch)
        btn_layout.addWidget(btn_apply)
        
        layout.addLayout(btn_layout)
        
        self.refresh_edits()
        
    def refresh_edits(self):
        self.edit_list.clear()
        if hasattr(self.parent_window, 'hex_view') and self.parent_window.hex_view.edits:
            for off, val in self.parent_window.hex_view.edits.items():
                self.edit_list.addItem(f"0x{off:08X}: {val:02X}")
                
    def export_patch(self):
        if not self.parent_window.hex_view.edits:
            QMessageBox.warning(self, LOCALE[self.parent_window.current_lang]["warning"], LOCALE[self.parent_window.current_lang]["no_edits"])
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, "Save Patch", "", "IPS Patch (*.ips)")
        if fname:
            try:
                with open(fname, "wb") as f:
                    f.write(b"PATCH")
                    for off, val in sorted(self.parent_window.hex_view.edits.items()):
                        f.write(off.to_bytes(3, "big"))
                        f.write((1).to_bytes(2, "big"))
                        f.write(bytes([val]))
                    f.write(b"EOF")
                QMessageBox.information(self, LOCALE[self.parent_window.current_lang]["success"], LOCALE[self.parent_window.current_lang]["patch_saved"] + f": {fname}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                
    def import_patch(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Load Patch", "", "IPS Patch (*.ips)")
        if fname:
            try:
                with open(fname, "rb") as f:
                    header = f.read(5)
                    if header != b"PATCH":
                        raise ValueError("Invalid IPS header")
                    edits = []
                    while True:
                        off_bytes = f.read(3)
                        if off_bytes == b"EOF" or len(off_bytes) < 3:
                            break
                        offset = int.from_bytes(off_bytes, "big")
                        size = int.from_bytes(f.read(2), "big")
                        data = f.read(size)
                        for i, b in enumerate(data):
                            edits.append((offset + i, b))
                            
                for off, val in edits:
                    self.edit_list.addItem(f"0x{off:08X}: {val:02X}")
                self.loaded_patch = edits
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                
    def apply_patch(self):
        if hasattr(self, 'loaded_patch'):
            for off, val in self.loaded_patch:
                self.parent_window.hex_view.edits[off] = val
            self.parent_window.hex_view.viewport().update()
            QMessageBox.information(self, LOCALE[self.parent_window.current_lang]["success"], LOCALE[self.parent_window.current_lang]["patch_applied"])

# --- Auto Analysis ---

class AutoAnalysisWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict) # {offset: (end, color, desc)}
    
    def __init__(self, data, options):
        super().__init__()
        self.data = data
        self.options = options # {"sigs": bool, "strings": bool, "values": bool}
        self.running = True
        
    def run(self):
        highlights = {}
        total = len(self.data)
        
        # 1. Signatures
        if self.options.get("sigs"):
            SIGNATURES = [
                (b"\x89PNG\r\n\x1a\n", "PNG Image", "#88ff88"),
                (b"\xff\xd8\xff", "JPEG Image", "#88ff88"),
                (b"PK\x03\x04", "ZIP/Office", "#ffff88"),
                (b"MZ", "DOS/PE Executable", "#8888ff"),
                (b"\x7fELF", "ELF Executable", "#8888ff"),
                (b"RIFF", "RIFF Media", "#ff88ff"),
                (b"OggS", "OGG Audio", "#ff88ff"),
                (b"fLaC", "FLAC Audio", "#ff88ff"),
                (b"ID3", "MP3 Tag", "#ff88ff"),
                (b"%PDF", "PDF Document", "#ffaaaa"),
                (b"\x7f\x50\x4b\x47", "PS4 PKG", "#00aaff"),
            ]
            
            for sig, desc, col in SIGNATURES:
                if not self.running: break
                try:
                    start = 0
                    while True:
                        idx = self.data.find(sig, start)
                        if idx == -1: break
                        highlights[idx] = (idx + len(sig) - 1, col, desc)
                        start = idx + 1
                except:
                    pass
        
        if not self.running: return
        self.progress.emit(30)
        
        # 2. Strings
        if self.options.get("strings"):
            try:
                # Basic ASCII search
                pattern = rb'[\x20-\x7E]{5,}'
                for m in re.finditer(pattern, self.data):
                    if not self.running: break
                    s = m.group().decode('ascii', errors='ignore')
                    highlights[m.start()] = (m.end()-1, "#aaffaa", f"String: {s[:20]}")
            except: pass
            
        if not self.running: return
        self.progress.emit(60)

         # 3. Heuristic Values (Integers) - Simplified
        if self.options.get("values"):
             try:
                 step = 4
                 limit = min(total - 4, 1024*1024*10) # 10MB limit
                 for i in range(0, limit, step):
                     if not self.running: break
                     val = struct.unpack("<I", self.data[i:i+4])[0]
                     if 100 < val < 1000000:
                         highlights[i] = (i+3, "#ffcc88", f"Int32: {val}")
             except: pass

        self.progress.emit(100)
        self.finished.emit(highlights)

    def stop(self):
        self.running = False


class AutoAnalysisDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.parent_window = parent
        self.data = data_source
        self.setWindowTitle(LOCALE[parent.current_lang]["auto"])
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.chk_sigs = QCheckBox(LOCALE[parent.current_lang]["auto_sigs"])
        self.chk_sigs.setChecked(True)
        layout.addWidget(self.chk_sigs)
        
        self.chk_strings = QCheckBox(LOCALE[parent.current_lang]["auto_strings"])
        self.chk_strings.setChecked(True)
        layout.addWidget(self.chk_strings)
        
        self.chk_values = QCheckBox(LOCALE[parent.current_lang]["auto_values"])
        self.chk_values.setToolTip(LOCALE[parent.current_lang]["auto_values_tip"])
        layout.addWidget(self.chk_values)
        
        self.btn_scan = QPushButton(LOCALE[parent.current_lang]["start_analysis"])
        self.btn_scan.clicked.connect(self.scan)
        layout.addWidget(self.btn_scan)
        
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        
        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)
        
    def scan(self):
        if not self.data: return
        
        self.options = {
            "sigs": self.chk_sigs.isChecked(),
            "strings": self.chk_strings.isChecked(),
            "values": self.chk_values.isChecked()
        }
        
        self.btn_scan.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        self.lbl_status.setText(LOCALE[self.parent_window.current_lang]["scanning"])
        
        self.worker = AutoAnalysisWorker(self.data, self.options)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, results):
        self.progress.hide()
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText(LOCALE[self.parent_window.current_lang]["found_items"].format(len(results)))
        
        # Apply highlights to hex view (Convert colors to QColor for performance)
        optimized_results = {}
        for k, v in results.items():
            end, color, desc = v
            optimized_results[k] = (end, QColor(color), desc)
            
        self.parent_window.hex_view.highlights = optimized_results
        self.parent_window.hex_view.schedule_update()
        
        QMessageBox.information(self, LOCALE[self.parent_window.current_lang]["analysis_complete"], 
                              LOCALE[self.parent_window.current_lang]["analysis_msg"].format(len(results)))
        self.accept()
            
    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

class OffsetCalculatorDialog(QDialog):
    """Offset and alignment calculator"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(LOCALE[parent.current_lang]["offset_calc"])
        self.resize(400, 300)
        
        layout = QFormLayout(self)
        
        # Base + Offset
        self.inp_base = QLineEdit("0")
        layout.addRow(LOCALE[parent.current_lang]["base_addr"] + ":", self.inp_base)
        
        self.inp_offset = QLineEdit("0")
        layout.addRow(LOCALE[parent.current_lang]["offset_plus"], self.inp_offset)
        
        self.lbl_result = QLabel("= 0x00000000")
        self.lbl_result.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addRow(LOCALE[parent.current_lang]["result"] + ":", self.lbl_result)
        
        btn_calc = QPushButton(LOCALE[parent.current_lang]["calculate"])
        btn_calc.clicked.connect(self.calculate)
        layout.addRow(btn_calc)
        
        layout.addRow(QLabel(""))  # Spacer
        
        # Alignment
        layout.addRow(QLabel(LOCALE[parent.current_lang]["alignment"] + ":"))
        
        align_layout = QHBoxLayout()
        self.inp_align_val = QLineEdit("0")
        align_layout.addWidget(self.inp_align_val)
        
        self.combo_align = QComboBox()
        self.combo_align.addItems(["2", "4", "8", "16", "256", "4096"])
        align_layout.addWidget(self.combo_align)
        
        btn_align = QPushButton(LOCALE[parent.current_lang]["align"])
        btn_align.clicked.connect(self.align)
        align_layout.addWidget(btn_align)
        layout.addRow(align_layout)
        
        self.lbl_aligned = QLabel("= 0x00000000")
        layout.addRow(LOCALE[parent.current_lang]["aligned"] + ":", self.lbl_aligned)
        
    def calculate(self):
        try:
            base = int(self.inp_base.text().replace("0x", ""), 16) if "x" in self.inp_base.text().lower() else int(self.inp_base.text())
            offset_str = self.inp_offset.text().strip()
            offset = int(offset_str.replace("0x", ""), 16) if "x" in offset_str.lower() else int(offset_str)
            result = base + offset
            self.lbl_result.setText(f"= 0x{result:08X} ({result})")
        except:
            self.lbl_result.setText(LOCALE[self.parent_window.current_lang]["invalid_input"])
            
    def align(self):
        try:
            val = int(self.inp_align_val.text().replace("0x", ""), 16) if "x" in self.inp_align_val.text().lower() else int(self.inp_align_val.text())
            align_to = int(self.combo_align.currentText())
            aligned = ((val + align_to - 1) // align_to) * align_to
            self.lbl_aligned.setText(f"= 0x{aligned:08X} ({aligned})")
        except:
            self.lbl_aligned.setText(LOCALE[self.parent_window.current_lang]["invalid_input"])

class StructuresPanel(QWidget):
    """Panel showing data structures"""
    goToOffset = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.combo_template = QComboBox()
        self.combo_template.addItems(["PE Header", "ELF Header", "ZIP Local", "PNG Chunks"])
        layout.addWidget(self.combo_template)
        
        btn_parse = QPushButton(LOCALE[parent.current_lang]["analyze"] if parent else "Parse")
        btn_parse.clicked.connect(self.parse_structure)
        layout.addWidget(btn_parse)
        
        self.tree = QTableWidget()
        self.tree.setColumnCount(3)
        self.tree.setHorizontalHeaderLabels(["Field", "Offset", "Value"])
        self.tree.horizontalHeader().setStretchLastSection(True)
        self.tree.itemDoubleClicked.connect(self.on_item_click)
        layout.addWidget(self.tree)
        
    def parse_structure(self):
        if not self.main_window or not self.main_window.mmap_obj:
            return
            
        data = bytes(self.main_window.mmap_obj[:1024])
        template = self.combo_template.currentText()
        
        self.tree.setRowCount(0)
        fields = []
        
        if template == "PE Header" and data[:2] == b"MZ":
            e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
            fields = [
                ("DOS Signature", 0, data[:2].hex().upper()),
                ("PE Offset", 0x3C, f"0x{e_lfanew:X}"),
            ]
            if e_lfanew < len(data) - 4:
                pe_sig = data[e_lfanew:e_lfanew+4]
                fields.append(("PE Signature", e_lfanew, pe_sig.hex().upper()))
                
        elif template == "ELF Header" and data[:4] == b"\x7fELF":
            fields = [
                ("ELF Magic", 0, "7F 45 4C 46"),
                ("Class", 4, "64-bit" if data[4] == 2 else "32-bit"),
                ("Endian", 5, "LE" if data[5] == 1 else "BE"),
            ]
            
        elif template == "ZIP Local" and data[:4] == b"PK\x03\x04":
            fname_len = struct.unpack("<H", data[26:28])[0]
            fields = [
                ("ZIP Signature", 0, "50 4B 03 04"),
                ("Version", 4, str(struct.unpack("<H", data[4:6])[0])),
                ("Flags", 6, f"0x{struct.unpack('<H', data[6:8])[0]:04X}"),
                ("Compression", 8, str(struct.unpack("<H", data[8:10])[0])),
                ("Filename Len", 26, str(fname_len)),
            ]
            
        elif template == "PNG Chunks" and data[:8] == b"\x89PNG\r\n\x1a\n":
            fields = [("PNG Signature", 0, "89 50 4E 47 0D 0A 1A 0A")]
            offset = 8
            for _ in range(5):
                if offset + 8 > len(data):
                    break
                length = struct.unpack(">I", data[offset:offset+4])[0]
                chunk_type = data[offset+4:offset+8].decode("ascii", errors="replace")
                fields.append((f"Chunk: {chunk_type}", offset, f"Size: {length}"))
                offset += 12 + length
                
        self.tree.setRowCount(len(fields))
        for row, (name, off, val) in enumerate(fields):
            self.tree.setItem(row, 0, QTableWidgetItem(name))
            self.tree.setItem(row, 1, QTableWidgetItem(f"0x{off:X}"))
            self.tree.setItem(row, 2, QTableWidgetItem(val))
            
    def on_item_click(self, item):
        row = item.row()
        offset_item = self.tree.item(row, 1)
        if offset_item:
            try:
                offset = int(offset_item.text().replace("0x", ""), 16)
                self.goToOffset.emit(offset)
            except:
                pass

class MainWindow(StormApp):
    def __init__(self):
        super().__init__("hex_editor")
        self.current_lang = "ru"
        # self.mmap_obj = None # Property now
        self.current_file = None
        self.read_only = False
        
        self.settings = QSettings(APP_NAME, APP_NAME)
        self.auto_update = self.settings.value("auto_update", True, type=bool)
        
        self.init_ui()
        self.apply_theme() # Load from settings
        self.setAcceptDrops(True)
        

    def init_ui(self):
        self.setWindowTitle(f"STORM HEX EDITOR v{CURRENT_VERSION}")
        self.resize(1250, 800)
        
        # Set App Icon
        icon_path = resource_path("stormhexeditor.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Load Settings
        self.settings = QSettings(APP_NAME, "Config")
        self.auto_update = self.settings.value("auto_update", True, type=bool)
        
        if self.auto_update:
            QTimer.singleShot(2000, lambda: self.check_updates(silent=True))
            
        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        # Toolbar (Wrapping version)
        self.toolbar = WrappingToolBar()
        main_layout.addWidget(self.toolbar)
        
        self.btn_open = QAction("📂 " + LOCALE[self.current_lang]["open"], self)
        self.btn_open.triggered.connect(self.open_file_dialog)
        self.toolbar.addAction(self.btn_open)
        
        self.btn_save = QAction("💾 " + LOCALE[self.current_lang]["save"], self)
        self.btn_save.triggered.connect(self.save_file)
        self.toolbar.addAction(self.btn_save)
        
        self.toolbar.addSeparator()
        
        self.btn_undo = QAction("↩ " + LOCALE[self.current_lang]["undo"], self)
        self.btn_undo.triggered.connect(lambda: self.hex_view.undo())
        self.btn_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.toolbar.addAction(self.btn_undo)
 
        self.btn_redo = QAction("↪ " + LOCALE[self.current_lang]["redo"], self)
        self.btn_redo.triggered.connect(lambda: self.hex_view.redo())
        self.btn_redo.setShortcut(QKeySequence("Ctrl+Y"))
        self.toolbar.addAction(self.btn_redo)
        
        self.toolbar.addSeparator()
        
        self.btn_search = QAction("🔍 " + LOCALE[self.current_lang]["find"], self)
        self.btn_search.triggered.connect(self.show_search)
        self.btn_search.setShortcut(QKeySequence("Ctrl+F"))
        self.toolbar.addAction(self.btn_search)
        
        self.btn_goto = QAction("➡ " + LOCALE[self.current_lang]["goto"], self)
        self.btn_goto.triggered.connect(self.show_goto)
        self.btn_goto.setShortcut(QKeySequence("Ctrl+G"))
        self.toolbar.addAction(self.btn_goto)
        
        self.toolbar.addSeparator()
        
        self.btn_checksum = QAction("🔢 " + LOCALE[self.current_lang]["checksum"], self)
        self.btn_checksum.triggered.connect(self.show_checksum)
        self.toolbar.addAction(self.btn_checksum)
        
        self.btn_entropy = QAction("📊 " + LOCALE[self.current_lang]["entropy"], self)
        self.btn_entropy.triggered.connect(self.show_entropy)
        self.toolbar.addAction(self.btn_entropy)
        
        self.btn_conv = QAction("🔢 " + LOCALE[self.current_lang]["base_conv"], self)
        self.btn_conv.triggered.connect(lambda: BaseConverterDialog(self).show())
        self.toolbar.addAction(self.btn_conv)
        
        self.btn_bitwise = QAction("🔧 " + LOCALE[self.current_lang]["bitwise"], self)
        self.btn_bitwise.triggered.connect(self.show_bitwise)
        self.toolbar.addAction(self.btn_bitwise)
        
        self.btn_sig = QAction("🔍 " + LOCALE[self.current_lang]["signature"], self)
        self.btn_sig.triggered.connect(self.show_signature)
        self.toolbar.addAction(self.btn_sig)
        
        self.btn_str = QAction("📜 " + LOCALE[self.current_lang]["strings"], self)
        self.btn_str.triggered.connect(self.show_strings)
        self.toolbar.addAction(self.btn_str)
        
        self.toolbar.addSeparator()
        
        # v1.0 NEW FEATURES
        self.btn_diff = QAction("⚖ " + LOCALE[self.current_lang]["diff"], self)
        self.btn_diff.triggered.connect(self.show_diff)
        self.toolbar.addAction(self.btn_diff)
        
        self.btn_regex = QAction("🔎 " + LOCALE[self.current_lang]["regex_search"], self)
        self.btn_regex.triggered.connect(self.show_regex_search)
        self.toolbar.addAction(self.btn_regex)
        
        self.btn_bytemap = QAction("🗺 " + LOCALE[self.current_lang]["byte_map"], self)
        self.btn_bytemap.triggered.connect(self.show_bytemap)
        self.toolbar.addAction(self.btn_bytemap)
        
        self.btn_patches = QAction("🩹 " + LOCALE[self.current_lang]["patches"], self)
        self.btn_patches.triggered.connect(self.show_patches)
        self.toolbar.addAction(self.btn_patches)
        
        self.btn_offset_calc = QAction("🧮 " + LOCALE[self.current_lang]["offset_calc"], self)
        self.btn_offset_calc.triggered.connect(self.show_offset_calc)
        self.toolbar.addAction(self.btn_offset_calc)
        
        self.btn_auto = QAction("🤖 " + LOCALE[self.current_lang].get("auto", "Auto"), self)
        self.btn_auto.triggered.connect(self.show_auto_analysis)
        self.toolbar.addAction(self.btn_auto)
        
        # Main Viewer Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)
        
        # Tabs Container
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        self.splitter.addWidget(self.tabs)
        
        # Inspector (New)
        
        # Inspector (New)
        try:
            self.inspector = StormInspector()
            self.splitter.addWidget(self.inspector)
        except Exception as e:
            print(f"CRASH INSTANTIATING INSPECTOR: {e}")
            import traceback; traceback.print_exc()
        
            print(f"CRASH INSTANTIATING INSPECTOR: {e}")
            import traceback; traceback.print_exc()
        
        # Bookmarks Widget (Restored)
        try:
            # Import if not already? It's likely in same file or needs import
            # Check imports. Assuming BookmarksWidget class exists in this file or imported.
            # If not, we might need to recreate it or find where it went.
            # Assuming it was part of standard code but got deleted/hidden.
            # Let's instantiate it if class exists.
            self.bookmarks_widget = BookmarksWidget(self)
            self.bookmarks_widget.goToSignal.connect(lambda off: self.goto(off))
            self.splitter.addWidget(self.bookmarks_widget)
        except NameError:
             # Class might be missing?
             pass 
        except Exception as e:
            print(f"Error init bookmarks: {e}")
        
        # Hotspots Widget - tracks frequently accessed areas
        try:
            self.hotspots_widget = HotspotsWidget(self)
            self.hotspots_widget.goToSignal.connect(lambda off: self.goto(off))
            self.splitter.addWidget(self.hotspots_widget)
        except Exception as e:
            print(f"Error init hotspots: {e}")
        
        self.create_status_bar()
        self.retranslate_ui()
        self.load_settings()

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        self.settings.setValue("splitterState", self.splitter.saveState())
        
        # Save Toolbar Order
        toolbar = self.findChild(QToolBar, "MainToolbar")
        if toolbar:
            order = [act.text() for act in toolbar.actions() if not act.isSeparator()]
            self.settings.setValue("toolbarOrder", order)
            
        event.accept()

    def load_settings(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
            
        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        else:
            # Default sizes: Hex view (600), Inspector (250), Bookmarks (200)
            self.splitter.setSizes([600, 250, 200])
            
        # Load Toolbar Order
        order = self.settings.value("toolbarOrder")
        if order and isinstance(order, list):
            toolbar = self.findChild(QToolBar, "MainToolbar")
            if toolbar:
                current_actions = {act.text(): act for act in toolbar.actions()}
                toolbar.clear()
                
                # Add saved actions
                for text in order:
                    if text in current_actions:
                        toolbar.addAction(current_actions[text])
                        del current_actions[text]
                
                # Add remaing/new actions
                if current_actions:
                    toolbar.addSeparator()
                    for act in current_actions.values():
                        toolbar.addAction(act)


    def create_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        
        # Status labels
        self.lbl_cursor = QLabel(LOCALE[self.current_lang]["offset"] + ": 00000000")
        self.lbl_val = QLabel(LOCALE[self.current_lang]["hex"] + ": 00")
        self.lbl_sel = QLabel(LOCALE[self.current_lang].get("sel", "Sel") + ": 0")
        self.lbl_mode = QLabel("INS")
        
        # Use addPermanentWidget with stretch factors or minimum widths
        self.lbl_cursor.setMinimumWidth(120)
        self.lbl_val.setMinimumWidth(80)
        self.lbl_sel.setMinimumWidth(80)
        self.lbl_mode.setMinimumWidth(40)
        
        # Add widgets with stretch factor 0 so they take required space, and spacing in between
        self.status.addWidget(self.lbl_cursor, 0)
        self.status.addWidget(QLabel("|"), 0)
        self.status.addWidget(self.lbl_val, 0)
        self.status.addWidget(QLabel("|"), 0)
        self.status.addWidget(self.lbl_sel, 0)
        self.status.addWidget(QLabel("|"), 0)
        self.status.addWidget(self.lbl_mode, 0)
        self.status.addWidget(QLabel(""), 1) # Spacer to push everything left, or remove to left-align default
        
        # User said: "Changing width of last changes first".
        # This implies standard QHBoxLayout behavior where they share space.
        # By setting stretch=0 and maybe a spacer at the end, they should be stable.
        
    @property
    def current_tab(self):
        return self.tabs.currentWidget()
        
    @property
    def hex_view(self):
        return self.current_tab.hex_view if self.current_tab else None
        
    @property
    def mmap_obj(self):
        return self.current_tab.mmap_obj if self.current_tab else None

    def refresh_status_bar(self, offset):
        if not self.hex_view: return
        val = self.hex_view.get_byte(offset)
        self.lbl_cursor.setText(f"{LOCALE[self.current_lang]['offset']}: {offset:08X}")
        self.lbl_val.setText(f"{LOCALE[self.current_lang]['hex']}: {val:02X}")
        
        sel_size = 0
        if self.hex_view.selection_start != -1:
            sel_size = abs(self.hex_view.selection_end - self.hex_view.selection_start) + 1
        self.lbl_sel.setText(f"{LOCALE[self.current_lang].get('sel', 'Sel')}: {sel_size}")
        
        self.lbl_mode.setText("OVR" if self.hex_view.overwrite_mode else "INS")

    def goto(self, offset):
        if self.current_tab:
            self.current_tab.goto(offset)
            # Track as hotspot
            if hasattr(self, 'hotspots_widget'):
                self.hotspots_widget.track_access(offset)

    def update_inspector(self, offset):
        self.refresh_status_bar(offset)
        if self.current_tab:
            data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
            self.inspector.set_data(data, offset)
        else:
            self.inspector.set_data(b"", 0)

    def sync_minimap(self):
        pass

    def open_file_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, LOCALE[self.current_lang]["open"])
        if fname:
            self.open_file(fname)

    def open_file(self, fname):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, HexTab) and widget.file_path == fname:
                self.tabs.setCurrentIndex(i)
                return

        tab = HexTab(self)
        if tab.open_file(fname):
            idx = self.tabs.addTab(tab, os.path.basename(fname))
            self.tabs.setCurrentIndex(idx)
            tab.cursorChanged.connect(self.update_inspector)
            self.current_file = fname
        else:
            tab.deleteLater()
            
    def save_file(self):
        if self.current_tab:
            if self.current_tab.save_file():
                self.statusBar().showMessage(LOCALE[self.current_lang]["saved"], 3000)

    def close_tab(self, index):
        tab = self.tabs.widget(index)
        if hasattr(tab, 'close_file'):
            tab.close_file()
        self.tabs.removeTab(index)
        
    def on_tab_changed(self, index):
        if index != -1:
            tab = self.tabs.widget(index)
            if isinstance(tab, HexTab):
                self.current_file = tab.file_path
                if tab.hex_view:
                    self.update_inspector(tab.hex_view.cursor_pos)
        else:
            self.current_file = None
            if hasattr(self, 'inspector'):
                self.inspector.set_data(b"", 0)



    def apply_theme(self, theme_name=None):
        if not theme_name:
            theme_name = self.settings.value("theme", "Dark (Default)")
        
        t = THEMES.get(theme_name, THEMES["Dark (Default)"])
        # self.hex_view is a property that depends on current_tab
        if self.hex_view:
            self.hex_view.apply_theme(t)
            
        # Update all tabs?
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'hex_view'):
                widget.hex_view.apply_theme(t)
                # Also apply to minimap if needed
                if hasattr(widget, 'minimap'):
                    widget.minimap.apply_theme(t) # Assuming minimize has apply_theme or uses same dict
        
        qss = f"""
            QMainWindow, QDialog {{ background-color: {t["bg"]}; color: {t["fg"]}; }}
            QLineEdit, QComboBox, QListWidget, QTableWidget {{ background-color: {t["alt_bg"]}; color: {t["fg"]}; border: 1px solid #444; }}
            QMenuBar {{ background-color: {t["menu_bg"]}; color: {t["menu_fg"]}; }}
            QMenuBar::item:selected {{ background-color: {t["sel_bg"]}; }}
            QMenu {{ background-color: {t["menu_bg"]}; color: {t["menu_fg"]}; border: 1px solid {t["alt_bg"]}; }}
            QMenu::item {{ padding: 5px 30px 5px 20px; }}
            QMenu::item:selected {{ background-color: {t["sel_bg"]}; }}
            QLabel {{ color: {t["fg"]}; }}
            QToolBar {{ background-color: {t["menu_bg"]}; border-bottom: 1px solid {t["alt_bg"]}; border-top: 1px solid {t["alt_bg"]}; spacing: 5px; }}
            QToolButton {{ color: {t["fg"]}; background-color: transparent; border: none; padding: 5px; }}
            QToolButton:hover {{ background-color: {t["sel_bg"]}; border-radius: 4px; }}
            QToolButton:pressed {{ background-color: {t["alt_bg"]}; }}
            QHeaderView::section {{ background-color: {t["alt_bg"]}; color: {t["fg"]}; border: 1px solid #444; }}
            QStatusBar {{ background-color: {t["menu_bg"]}; color: {t["fg"]}; }}
        """
        self.setStyleSheet(qss)

    def show_search(self):
        dialog = SearchDialog(self)
        if dialog.exec():
            pattern_str = dialog.input_search.text()
            if not pattern_str: return
            
            # Prepare pattern
            pattern = b""
            try:
                if dialog.mode == "hex":
                    pattern = binascii.unhexlify(pattern_str.replace(" ", ""))
                else:
                    pattern = pattern_str.encode("utf-8") # Basic UTF-8
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Invalid Pattern: {e}")
                return
                
            start_pos = self.hex_view.cursor_pos + 1
            if start_pos >= self.hex_view.file_size: start_pos = 0
            
            # Search
            if self.mmap_obj:
                found_pos = self.mmap_obj.find(pattern, start_pos)
                if found_pos == -1: # Try wrap around
                    found_pos = self.mmap_obj.find(pattern, 0)
            else:
                found_pos = self.hex_view.data_source.find(pattern, start_pos)
                if found_pos == -1:
                    found_pos = self.hex_view.data_source.find(pattern, 0)
            
            if found_pos != -1:
                self.goto(found_pos)
            else:
                QMessageBox.information(self, "Result", LOCALE[self.current_lang]["not_found"])

    def show_goto(self):
        dialog = GoToDialog(self)
        if dialog.exec():
            try:
                offset_str = dialog.input_offset.text().replace("0x", "").strip()
                offset = int(offset_str, 16)
                if 0 <= offset < self.hex_view.file_size:
                    self.goto(offset)
                else:
                    QMessageBox.warning(self, "Error", "Offset out of bounds")
            except ValueError:
                QMessageBox.warning(self, "Error", "Invalid Hex Offset")

    def show_checksum(self):
        if not self.hex_view: return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = ChecksumDialog(self, data)
        dialog.exec()

    def show_signature(self):
        if not self.hex_view: return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = SignatureDialog(self, data)
        dialog.exec()
        
    def show_strings(self):
        if not self.hex_view: return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = StringsDialog(self, data)
        dialog.exec()
        
    def show_entropy(self):
        if not self.hex_view: return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = EntropyDialog(self, data)
        dialog.exec()

    def show_bitwise(self):
        dialog = BitwiseDialog(self)
        if dialog.exec():
            op = dialog.combo_op.currentText()
            operand_str = dialog.inp_operand.text().strip()
            
            operand = 0
            if op != "NOT":
                try:
                    operand = int(operand_str, 16)
                except ValueError:
                    QMessageBox.warning(self, "Error", "Invalid Operand (Hex expected)")
                    return
            
            self.apply_bitwise(op, operand)
            
    def apply_bitwise(self, op, operand):
        if self.hex_view.selection_start == -1:
            QMessageBox.information(self, "Info", "Select a region first.")
            return
            
        start = min(self.hex_view.selection_start, self.hex_view.selection_end)
        end = max(self.hex_view.selection_start, self.hex_view.selection_end) + 1
        
        self.hex_view.begin_macro()
        try:
            for i in range(start, end):
                 val = self.hex_view.get_byte(i)
                 new_val = val
                 
                 if op == "AND": new_val = val & operand
                 elif op == "OR": new_val = val | operand
                 elif op == "XOR": new_val = val ^ operand
                 elif op == "NOT": new_val = ~val & 0xFF
                 elif op.startswith("Shift Left"): new_val = (val << operand) & 0xFF
                 elif op.startswith("Shift Right"): new_val = (val >> operand) & 0xFF
                 elif op.startswith("Rotate Left"): new_val = ((val << operand) | (val >> (8 - operand))) & 0xFF
                 elif op.startswith("Rotate Right"): new_val = ((val >> operand) | (val << (8 - operand))) & 0xFF
                 
                 if new_val != val:
                     old_val = self.hex_view.edits.get(i, None)
                     self.hex_view.push_edit(i, old_val, new_val)
                     self.hex_view.edits[i] = new_val
        finally:
            self.hex_view.end_macro()
                 
        self.hex_view.viewport().update()
        self.hex_view.cursorChanged.emit(self.hex_view.cursor_pos) 
        
    def add_bookmark_handler(self, offset):
        text, ok = QInputDialog.getText(self, LOCALE[self.current_lang]["add_bm"], LOCALE[self.current_lang]["desc"], text=f"Offset {offset:X}")
        if ok:
            self.bookmarks_widget.add_bookmark(offset, text)

    # --- v1.0 NEW FEATURE HANDLERS ---
    
    def show_diff(self):
        if not self.hex_view or not self.hex_view.data_source:
            QMessageBox.warning(self, LOCALE[self.current_lang]["warning"], LOCALE[self.current_lang]["open_file_first"])
            return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        fname = self.windowTitle().split(" - ")[-1] if " - " in self.windowTitle() else "Current File"
        dialog = DiffDialog(self, data, fname)
        dialog.exec()
        
    def show_regex_search(self):
        dialog = RegexSearchDialog(self)
        dialog.exec()
        
    def show_bytemap(self):
        if not self.hex_view or not self.hex_view.data_source:
            QMessageBox.warning(self, LOCALE[self.current_lang]["warning"], LOCALE[self.current_lang]["open_file_first"])
            return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = ByteMapDialog(self, data)
        dialog.exec()
        
    def show_patches(self):
        dialog = PatchDialog(self)
        dialog.exec()
        
    def show_offset_calc(self):
        dialog = OffsetCalculatorDialog(self)
        dialog.exec()
        
    def show_auto_analysis(self):
        if not self.hex_view or not self.hex_view.data_source:
            QMessageBox.warning(self, LOCALE[self.current_lang]["warning"], LOCALE[self.current_lang]["open_file_first"])
            return
        data = self.mmap_obj if self.mmap_obj is not None else self.hex_view.data_source
        dialog = AutoAnalysisDialog(self, data)
        dialog.exec()


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.open_file(files[0])

    def toggle_auto_update(self):
        self.auto_update = self.act_auto_upd.isChecked()
        self.settings.setValue("auto_update", self.auto_update)
        
    def check_updates(self, silent=False):
        try:
            url = f"https://api.github.com/repos/ReiKatari/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'StormHexEditor'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data["tag_name"]
                
                # Simple version check (assumes format vX.X.X or X.X.X)
                latest_ver = latest_tag.lstrip("v")
                current_ver = CURRENT_VERSION
                
                if latest_ver != current_ver:
                    msg = f"{LOCALE[self.current_lang]['new_ver']} {latest_tag}\n{LOCALE[self.current_lang]['current']} {CURRENT_VERSION}\n\n{LOCALE[self.current_lang]['open_page']}"
                    if QMessageBox.question(self, LOCALE[self.current_lang]["update_avail"], msg) == QMessageBox.StandardButton.Yes:
                         webbrowser.open(f"https://github.com/ReiKatari/{GITHUB_REPO}/releases")
                else:
                    if not silent:
                        QMessageBox.information(self, "Info", LOCALE[self.current_lang]["no_update"])
        except Exception as e:
            if silent:
                return
            QMessageBox.warning(self, LOCALE[self.current_lang]["update_err"], f"{LOCALE[self.current_lang]['update_fail']}\n{e}")

    def create_view_menu(self):
        pass

    def change_lang(self, lang_code):
        self.current_lang = lang_code
        self.retranslate_ui()
        
    def retranslate_ui(self):
        # Window Title - ALWAYS shows version, never filename
        self.setWindowTitle(f"STORM HEX EDITOR v{CURRENT_VERSION}")
            
        # Update Toolbar Actions
        if hasattr(self, 'toolbar'):
            self.toolbar.refresh()
            self.btn_open.setText("📂 " + LOCALE[self.current_lang]["open"])
            self.btn_save.setText("💾 " + LOCALE[self.current_lang]["save"])
            self.btn_undo.setText("↩ " + LOCALE[self.current_lang]["undo"])
            self.btn_redo.setText("↪ " + LOCALE[self.current_lang]["redo"])
            self.btn_search.setText("🔍 " + LOCALE[self.current_lang]["find"])
            self.btn_goto.setText("➡ " + LOCALE[self.current_lang]["goto"])
            self.btn_checksum.setText("🔢 " + LOCALE[self.current_lang]["checksum"])
            self.btn_entropy.setText("📊 " + LOCALE[self.current_lang]["entropy"])
            self.btn_conv.setText("🔢 " + LOCALE[self.current_lang]["base_conv"])
            self.btn_bitwise.setText("🔧 " + LOCALE[self.current_lang]["bitwise"])
            if hasattr(self, 'btn_sig'):
                self.btn_sig.setText("🔍 " + LOCALE[self.current_lang]["signature"])
                self.btn_str.setText("📜 " + LOCALE[self.current_lang]["strings"])
                self.btn_auto.setText("🤖 " + LOCALE[self.current_lang].get("auto", "Auto"))

        # Update Tab Titles
        if hasattr(self, 'tabs'):
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, HexTab):
                    self.tabs.setTabText(i, os.path.basename(tab.file_path) if tab.file_path else "Untitled")

        # Reconstruct Menu Bar
        menubar = self.menuBar()
        menubar.clear()
        
        # Program Menu - like Tile Manager with all apps
        self.menu_program = menubar.addMenu("📱 " + LOCALE[self.current_lang]["program"])
        for key, name in [("suite", "suite"), ("hex_editor", "hex_editor"), ("tile_manager", "tile_manager"), ("game_dict", "game_dict")]:
            action = QAction(LOCALE[self.current_lang][name], self)
            action.triggered.connect(lambda checked, k=key: self.switch_app(k))
            if key == self.app_key:
                action.setEnabled(False)
                action.setCheckable(True)
                action.setChecked(True)
            self.menu_program.addAction(action)

        # File Menu
        file_menu = menubar.addMenu("📁 " + LOCALE[self.current_lang]["file"])
        file_menu.addAction(self.btn_open)
        file_menu.addAction(self.btn_save)
        file_menu.addSeparator()
        act_close = QAction("📕 " + LOCALE[self.current_lang]["close"], self)
        act_close.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(act_close)
        file_menu.addSeparator()
        act_exit = QAction("🚪 " + LOCALE[self.current_lang]["exit"], self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Edit Menu
        edit_menu = menubar.addMenu("✏ " + LOCALE[self.current_lang]["edit"])
        edit_menu.addAction(self.btn_undo)
        edit_menu.addAction(self.btn_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.btn_search)
        edit_menu.addAction(self.btn_goto)

        # Tools Menu
        self.create_tools_menu()

        # View Menu
        view_menu = menubar.addMenu("👁 " + LOCALE[self.current_lang]["view"])
        theme_menu = view_menu.addMenu("🎨 " + LOCALE[self.current_lang]["theme"])
        for t_name in THEMES.keys():
            act = QAction(t_name, self)
            act.triggered.connect(lambda checked, n=t_name: self.apply_theme(n))
            theme_menu.addAction(act)
        
        lang_menu = view_menu.addMenu("🌐 " + LOCALE[self.current_lang]["lang"])
        act_ru = QAction("Русский", self)
        act_ru.triggered.connect(lambda: self.change_lang("ru"))
        act_en = QAction("English", self)
        act_en.triggered.connect(lambda: self.change_lang("en"))
        lang_menu.addAction(act_ru)
        lang_menu.addAction(act_en)

        # Help Menu - like Tile Manager
        help_menu = menubar.addMenu("❓ " + LOCALE[self.current_lang]["help"])
        
        self.act_auto_upd = QAction("⚙️ " + LOCALE[self.current_lang]["auto_update"], self)
        self.act_auto_upd.setCheckable(True)
        self.act_auto_upd.setChecked(self.settings.value("auto_update", True, type=bool))
        self.act_auto_upd.triggered.connect(self.toggle_auto_update)
        help_menu.addAction(self.act_auto_upd)
        
        act_upd = QAction("🔄 " + LOCALE[self.current_lang]["check_updates"], self)
        act_upd.triggered.connect(lambda: self.check_updates(silent=False))
        help_menu.addAction(act_upd)
        
        act_gh = QAction("🌐 GitHub", self)
        act_gh.triggered.connect(lambda: webbrowser.open(f"https://github.com/{APP_REPOS.get(self.app_key, APP_REPOS['suite'])}"))
        help_menu.addAction(act_gh)
        
        act_about = QAction("ℹ️ " + LOCALE[self.current_lang]["about"], self)
        act_about.triggered.connect(lambda: show_about_dialog(self, self.app_key))
        help_menu.addAction(act_about)

        # Update Inspector
        if hasattr(self, 'inspector'):
            self.inspector.retranslate_ui()
            
        # Update Bookmarks
        if hasattr(self, 'bookmarks_widget'):
            self.bookmarks_widget.update_ui()
            
        # Update Hotspots
        if hasattr(self, 'hotspots_widget'):
            self.hotspots_widget.update_ui()


    def create_tools_menu(self):
        """Create Tools menu with all analysis and utility features"""
        tools_menu = self.menuBar().addMenu(LOCALE[self.current_lang]["tools"])
        
        # Analysis tools
        act_checksum = QAction("🔢 " + LOCALE[self.current_lang]["checksum"], self)
        act_checksum.triggered.connect(self.show_checksum)
        tools_menu.addAction(act_checksum)
        
        act_entropy = QAction("📊 " + LOCALE[self.current_lang]["entropy"], self)
        act_entropy.triggered.connect(self.show_entropy)
        tools_menu.addAction(act_entropy)
        
        act_sig = QAction("🔍 " + LOCALE[self.current_lang]["signature"], self)
        act_sig.triggered.connect(self.show_signature)
        tools_menu.addAction(act_sig)
        
        act_str = QAction("📜 " + LOCALE[self.current_lang]["strings"], self)
        act_str.triggered.connect(self.show_strings)
        tools_menu.addAction(act_str)
        
        act_auto = QAction("🤖 " + LOCALE[self.current_lang]["auto"], self)
        act_auto.triggered.connect(self.show_auto_analysis)
        tools_menu.addAction(act_auto)
        
        tools_menu.addSeparator()
        
        # Converters and calculators  
        act_conv = QAction("🔢 " + LOCALE[self.current_lang]["base_conv"], self)
        act_conv.triggered.connect(lambda: BaseConverterDialog(self).show())
        tools_menu.addAction(act_conv)
        
        act_bitwise = QAction("🔧 " + LOCALE[self.current_lang]["bitwise"], self)
        act_bitwise.triggered.connect(self.show_bitwise)
        tools_menu.addAction(act_bitwise)
        
        tools_menu.addSeparator()
        
        # v1.0 New Features
        act_diff = QAction("⚖ " + LOCALE[self.current_lang]["diff"], self)
        act_diff.triggered.connect(self.show_diff)
        tools_menu.addAction(act_diff)
        
        act_regex = QAction("🔎 " + LOCALE[self.current_lang]["regex_search"], self)
        act_regex.triggered.connect(self.show_regex_search)
        tools_menu.addAction(act_regex)
        
        act_bytemap = QAction("🗺 " + LOCALE[self.current_lang]["byte_map"], self)
        act_bytemap.triggered.connect(self.show_bytemap)
        tools_menu.addAction(act_bytemap)
        
        act_patches = QAction("🩹 " + LOCALE[self.current_lang]["patches"], self)
        act_patches.triggered.connect(self.show_patches)
        tools_menu.addAction(act_patches)
        
        act_offset_calc = QAction("🧮 " + LOCALE[self.current_lang]["offset_calc"], self)
        act_offset_calc.triggered.connect(self.show_offset_calc)
        tools_menu.addAction(act_offset_calc)

    def show_about(self):
        show_about_dialog(self, "hex_editor")

    def show_launcher(self):
        try:
            subprocess.Popen([sys.executable, "stormsuite.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch Storm Suite: {e}")


    # ... (other methods)
    
# --- ENTRY POINT ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    # CLI: Open file if passed as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path):
            window.open_file(file_path)
    
    sys.exit(app.exec())
