import sys
import os
import struct
import urllib.request
import json
import webbrowser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QScrollArea, QFileDialog, 
                             QMessageBox, QSpinBox, QGroupBox, QGridLayout, QFrame, QDialog, QLineEdit, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint, QRect
from PyQt6.QtGui import QIcon, QImage, QPixmap, QPainter, QColor, QPen, QAction, QBrush, QPalette, QKeySequence

# --- STORM SUITE IMPORTS ---
from stormbase import StormApp, LOCALE, THEMES, resource_path, APP_NAME, CURRENT_VERSION, AUTHOR, APP_REPOS, show_about_dialog

class TileFormat:
    """Helper for tile decoding/encoding"""
    @staticmethod
    def decode_1bpp(data, width=8, height=8):
        # 1 bit per pixel. 8 pixels = 1 byte.
        # Simple row-packed 1BPP
        pixels = []
        stride = width // 8
        if stride < 1: stride = 1
        
        for y in range(height):
            for x in range(0, width, 8):
                idx = (y * stride) + (x // 8)
                if idx >= len(data): b = 0
                else: b = data[idx]
                
                for bit in range(7, -1, -1):
                    pixels.append((b >> bit) & 1)
        return pixels

    @staticmethod
    def decode_2bpp(data, width=8, height=8):
        # Gameboy 2BPP (Planar: 2 bytes per row)
        pixels = []
        bytes_per_row = 2
        
        for y in range(height):
            idx = y * bytes_per_row
            if idx + 1 >= len(data): 
                # Fill remaining with 0 if incomplete
                b1, b2 = 0, 0
            else:
                b1 = data[idx]
                b2 = data[idx+1]
            
            for x in range(7, -1, -1):
                lo = (b1 >> x) & 1
                hi = (b2 >> x) & 1
                pixels.append((hi << 1) | lo)
        return pixels
    
    @staticmethod
    def decode_nes_2bpp(data, width=8, height=8):
        # NES 2BPP (8 bytes plane 0, 8 bytes plane 1)
        pixels = [0] * (width * height)
        for y in range(8):
            if y >= len(data): break
            lo = data[y]
            hi = data[y + 8] if y + 8 < len(data) else 0
            for x in range(8):
                bit_lo = (lo >> (7 - x)) & 1
                bit_hi = (hi >> (7 - x)) & 1
                pixels[y * 8 + x] = (bit_hi << 1) | bit_lo
        return pixels

    @staticmethod
    def decode_4bpp(data, width=8, height=8):
        # SNES/GBA style 4BPP 
        # Simple packed: 1 byte = 2 pixels (high nibble, low nibble)
        # Actually standard is usually (b & 0xF) then (b >> 4) or vice versa.
        # Let's match typical LE: (b & 0xF) is p0, (b >> 4) is p1
        # Wait, if we used (b >> 4) first in encode, we should do same here.
        pixels = []
        for b in data:
            pixels.append((b >> 4) & 0xF)
            pixels.append(b & 0xF)
        return pixels[:width*height]

    @staticmethod
    def decode_4bpp_linear(data, width=8, height=8):
        # Sega Genesis/Mega Drive 4BPP Linear format
        # Each tile is 32 bytes (8x8 pixels, 4 bits per pixel)
        # Byte order: each byte contains 2 pixels (high nibble first)
        pixels = []
        for b in data:
            pixels.append((b >> 4) & 0xF)
            pixels.append(b & 0xF)
        return pixels[:width*height]

    @staticmethod
    def encode_1bpp(pixels, width=8, height=8):
        data = bytearray()
        stride = width // 8
        if stride < 1: stride = 1
        
        for y in range(height):
            for x in range(0, width, 8):
                b = 0
                for bit in range(8):
                    if (y * width) + x + bit < len(pixels):
                        b |= (pixels[(y * width) + x + bit] & 1) << (7 - bit)
                data.append(b)
        return data

    @staticmethod
    def encode_2bpp(pixels, width=8, height=8):
        data = bytearray()
        for y in range(height):
            low_byte = 0
            high_byte = 0
            for x in range(8):
                idx = y * width + x
                val = pixels[idx] if idx < len(pixels) else 0
                
                if val & 1: low_byte |= (1 << (7 - x))
                if val & 2: high_byte |= (1 << (7 - x))
            
            data.append(low_byte)
            data.append(high_byte)
        return data

    @staticmethod
    def encode_4bpp(pixels, width=8, height=8):
        data = bytearray()
        for i in range(0, len(pixels), 2):
            p0 = pixels[i] if i < len(pixels) else 0
            p1 = pixels[i+1] if i+1 < len(pixels) else 0
            b = ((p0 & 0xF) << 4) | (p1 & 0xF)
            data.append(b)
        return data

    @staticmethod
    def encode_nes_2bpp(pixels, width=8, height=8):
        # NES 2BPP (8 bytes plane 0, then 8 bytes plane 1)
        data = bytearray(16)
        for y in range(8):
            lo = 0
            hi = 0
            for x in range(8):
                idx = y * 8 + x
                p = pixels[idx] if idx < len(pixels) else 0
                if p & 1: lo |= (1 << (7 - x))
                if p & 2: hi |= (1 << (7 - x))
            data[y] = lo
            data[y + 8] = hi
        return data

    @staticmethod
    def encode_4bpp_linear(pixels, width=8, height=8):
        return TileFormat.encode_4bpp(pixels, width, height)

class HistoryManager:
    def __init__(self, limit=100):
        self.limit = limit
        self.stack = []
        self.index = -1
    
    def add(self, data):
        # If we are in the middle of history, clear forward
        if self.index < len(self.stack) - 1:
            self.stack = self.stack[:self.index + 1]
        
        self.stack.append(bytearray(data))
        if len(self.stack) > self.limit:
            self.stack.pop(0)
        else:
            self.index += 1
            
    def undo(self):
        if self.index > 0:
            self.index -= 1
            return bytearray(self.stack[self.index])
        return None
        
    def redo(self):
        if self.index < len(self.stack) - 1:
            self.index += 1
            return bytearray(self.stack[self.index])
        return None

class PaletteWidget(QWidget):
    colorSelected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.colors = [QColor(i*15, i*15, i*15) for i in range(16)] # Default grayscale
        self.selected_idx = 0
        self.cell_size = 32
        
    def set_palette(self, colors):
        self.colors = colors
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#222"))
        
        spacing = 4
        cols = 4
        
        for i, color in enumerate(self.colors):
            r = i // cols
            c = i % cols
            x = c * (self.cell_size + spacing) + spacing
            y = r * (self.cell_size + spacing) + spacing
            
            rect = QRect(x, y, self.cell_size, self.cell_size)
            painter.fillRect(rect, color)
            
            if i == self.selected_idx:
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawRect(rect.adjusted(-1,-1,1,1))
                
    def mousePressEvent(self, event):
        spacing = 4
        cols = 4
        x = event.pos().x()
        y = event.pos().y()
        
        c = (x - spacing) // (self.cell_size + spacing)
        r = (y - spacing) // (self.cell_size + spacing)
        
        idx = r * cols + c
        if 0 <= idx < len(self.colors):
            self.selected_idx = idx
            self.colorSelected.emit(idx)
            self.update()

class TileGridWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.zoom = 4
        self.tile_data = b'\x00' * 1024 # Dummy data
        self.format = "4BPP"
        self.width_tiles = 16 # dynamic?
        self.fixed_width = False # If True, use width_tiles instead of widget width
        self.palette = [QColor(i*15, i*15, i*15) for i in range(16)] # 16 grayscale
        self.current_tool = "draw" # "draw", "fill"
        self.current_color_idx = 1
        self.history = None # Will be set by MainWindow
        self.show_grid = True  # Grid overlay toggle
        self.grid_size = 8  # Grid cell size (8, 16, 32)
        self.selected_tiles = []  # For animation preview
        
    def paintEvent(self, event):
        if not self.tile_data:
            return

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111"))
        
        # Determine tile size
        tile_w, tile_h = 8, 8
        
        # Calculate how many tiles fit in the data
        bytes_per_tile = 32
        if "1BPP" in self.format: bytes_per_tile = 8
        elif "2BPP" in self.format: bytes_per_tile = 16 # Same for NES
        elif "8BPP" in self.format: bytes_per_tile = 64
        
        total_tiles = len(self.tile_data) // bytes_per_tile
        if total_tiles == 0: return

        # Draw grid of tiles
        # Tiles per row depends on fixed_width or widget width
        if self.fixed_width:
            cols = self.width_tiles
        else:
            cols = self.width() // (tile_w * self.zoom)
        if cols < 1: cols = 1
        
        rows = (total_tiles + cols - 1) // cols
        
        # Update height
        min_h = rows * tile_h * self.zoom
        if self.minimumHeight() != min_h:
             self.setMinimumHeight(min_h)
             self.updateGeometry() # Crucial for scroll area to notice
        
        # We need to paint only the visible area for performance
        # For now, simple loop is fine unless it's slow.
        # Draw each tile
        ... # (Existing paint loop follows, but I'll update it later if needed)

        # Draw visible tiles only
        # We need a decoder 
        decoder = TileFormat.decode_4bpp
        if "1BPP" in self.format: decoder = TileFormat.decode_1bpp
        elif "NES" in self.format: decoder = TileFormat.decode_nes_2bpp
        elif "2BPP" in self.format: decoder = TileFormat.decode_2bpp
        elif "LINEAR" in self.format: decoder = TileFormat.decode_4bpp_linear
        elif "4BPP" in self.format: decoder = TileFormat.decode_4bpp

        # Define visible rect
        # Since this is inside a ScrollArea, paintEvent region is the visible region (usually)
        # But QWidget inside ScrollArea gets full paint event? No, only exposed.
        # Let's just iterate all for now (simple), optimization later if needed.
        
        current_x = 0
        current_y = 0
        
        for i in range(total_tiles):
            # Check if within update rect
            target_rect = QRect(current_x, current_y, tile_w * self.zoom, tile_h * self.zoom)
            
            if event.rect().intersects(target_rect):
                offset = i * bytes_per_tile
                chunk = self.tile_data[offset : offset+bytes_per_tile]
                pixels = decoder(chunk)
                
                img = QImage(tile_w, tile_h, QImage.Format.Format_RGB32)
                for py in range(tile_h):
                    for px in range(tile_w):
                        idx = py * tile_w + px
                        c_idx = pixels[idx] if idx < len(pixels) else 0
                        
                        # Apply Palette
                        if c_idx < len(self.palette):
                            img.setPixelColor(px, py, self.palette[c_idx])
                        else:
                            img.setPixelColor(px, py, QColor(0,0,0))
                
                painter.drawImage(target_rect, img)
            
            # Advance
            current_x += tile_w * self.zoom
            if current_x + tile_w * self.zoom > self.width():
                current_x = 0
                current_y += tile_h * self.zoom
        
        # Draw Grid Overlay
        if self.show_grid:
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            grid_step = self.grid_size * self.zoom
            
            # Vertical lines
            for x in range(0, self.width(), grid_step):
                painter.drawLine(x, 0, x, current_y + tile_h * self.zoom)
            
            # Horizontal lines
            for y in range(0, current_y + tile_h * self.zoom, grid_step):
                painter.drawLine(0, y, self.width(), y)
                
    def set_data(self, data):
        self.tile_data = bytearray(data)
        self.update()

    def mousePressEvent(self, event):
        if not self.tile_data: return
        
        # Calculate tile x, y
        tile_w, tile_h = 8, 8
        if self.fixed_width:
             cols = self.width_tiles
        else:
             cols = self.width() // (tile_w * self.zoom)
        if cols < 1: cols = 1

        tx = event.pos().x() // (tile_w * self.zoom)
        ty = event.pos().y() // (tile_h * self.zoom)
        
        tile_idx = ty * cols + tx
        
        # Calculate pixel inside tile
        px = (event.pos().x() % (tile_w * self.zoom)) // self.zoom
        py = (event.pos().y() % (tile_h * self.zoom)) // self.zoom
        
        # Calculate bytes per tile
        bpt = 32
        if "1BPP" in self.format: bpt = 8
        elif "2BPP" in self.format: bpt = 16
        elif "8BPP" in self.format: bpt = 64
        
        if tile_idx * bpt >= len(self.tile_data): return
        
        if self.current_tool == "draw":
             self.draw_pixel(tile_idx, px, py)
        elif self.current_tool == "fill":
             self.fill_tile(tile_idx)
             
        # Add to history after change
        if self.history:
            self.history.add(self.tile_data)
            
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom = min(32, self.zoom + 1)
            else:
                self.zoom = max(1, self.zoom - 1)
            self.update()
            # We don't need to return or accept? Better accept.
            event.accept()
        else:
            super().wheelEvent(event)
             
    def draw_pixel(self, tile_idx, px, py):
        # We need to modify bits in self.tile_data
        # This is complex because of bit-planar formats.
        # Let's use a helper: decode -> modify -> encode
        bpt = 32
        decoder, encoder = TileFormat.decode_4bpp, TileFormat.encode_4bpp
        if "1BPP" in self.format: bpt, decoder, encoder = 8, TileFormat.decode_1bpp, TileFormat.encode_1bpp
        elif "NES" in self.format: bpt, decoder, encoder = 16, TileFormat.decode_nes_2bpp, TileFormat.encode_nes_2bpp
        elif "2BPP" in self.format: bpt, decoder, encoder = 16, TileFormat.decode_2bpp, TileFormat.encode_2bpp
        elif "LINEAR" in self.format: bpt, decoder, encoder = 32, TileFormat.decode_4bpp_linear, TileFormat.encode_4bpp_linear
        
        offset = tile_idx * bpt
        pixels = list(decoder(self.tile_data[offset : offset+bpt]))
        pixels[py * 8 + px] = self.current_color_idx
        self.tile_data[offset : offset+bpt] = encoder(pixels)
        self.update()

    def fill_tile(self, tile_idx):
        bpt = 32
        encoder = TileFormat.encode_4bpp
        if "1BPP" in self.format: bpt, encoder = 8, TileFormat.encode_1bpp
        elif "NES" in self.format: bpt, encoder = 16, TileFormat.encode_nes_2bpp
        elif "2BPP" in self.format: bpt, encoder = 16, TileFormat.encode_2bpp
        elif "LINEAR" in self.format: bpt, encoder = 32, TileFormat.encode_4bpp_linear
        
        offset = tile_idx * bpt
        pixels = [self.current_color_idx] * 64
        self.tile_data[offset : offset+bpt] = encoder(pixels)
        self.update()
        
    def get_binary_data(self):
        return self.tile_data
        
    def set_format(self, idx):
        formats = ["1BPP", "2BPP", "NES 2BPP", "4BPP_PLANAR", "4BPP_LINEAR", "8BPP"]
        if 0 <= idx < len(formats):
            self.format = formats[idx]
            self.update()
            
    def import_image(self, image):
        width = image.width()
        height = image.height()
        w_tiles = width // 8
        h_tiles = height // 8
        
        new_data = bytearray()
        
        encoder = TileFormat.encode_4bpp
        max_col = 16
        if "1BPP" in self.format: 
            encoder = TileFormat.encode_1bpp
            max_col = 2
        elif "2BPP" in self.format: 
            encoder = TileFormat.encode_2bpp
            max_col = 4
            
        for y in range(h_tiles):
            for x in range(w_tiles):
                pixels = []
                for ty in range(8):
                    for tx in range(8):
                        c = image.pixelColor(x*8+tx, y*8+ty)
                        # Grayscale approximation
                        val = (c.red() + c.green() + c.blue()) // 3
                        # Map 0-255 to 0-(max_col-1)
                        # inverted? Usually 0=black, but in index 0 is first color.
                        # Let's say 0=dark, max=light
                        idx = int(val / (256/max_col))
                        if idx >= max_col: idx = max_col-1
                        pixels.append(idx)
                
                chunk = encoder(pixels)
                new_data.extend(chunk)
        
        self.set_data(bytes(new_data))


class TileTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.history = HistoryManager()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: #111;")
        
        self.tile_grid = TileGridWidget()
        self.tile_grid.history = self.history
        self.history.add(self.tile_grid.tile_data)
        
        self.scroll.setWidget(self.tile_grid)
        layout.addWidget(self.scroll)
        
    def open_file(self, fname):
        self.file_path = fname
        with open(fname, "rb") as f:
            data = f.read()
            self.tile_grid.set_data(data)
            self.history.stack = []
            self.history.index = -1
            self.history.add(data)
            
    def save_file(self):
        if self.file_path:
            with open(self.file_path, "wb") as f:
                f.write(self.tile_grid.get_binary_data())
            return True
        return False

class MainWindow(StormApp):
    def __init__(self):
        super().__init__("tile_manager")
        self.setAutoFillBackground(True)
        self.setAcceptDrops(True)
        # History is now per-tab
        self.init_ui()
        
    def show_about(self):
        show_about_dialog(self, "tile_manager")
        
    def init_ui(self):
        self.setWindowTitle(f"STORM TILE MANAGER v{CURRENT_VERSION}")
        
        # Central Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Left Panel (Tools, Format, Palette)
        left_panel = QFrame()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        
        # Tools
        self.gb_tools = QGroupBox()
        tools_layout = QGridLayout(self.gb_tools)
        self.btn_draw = QPushButton()
        self.btn_fill = QPushButton()
        tools_layout.addWidget(self.btn_draw, 0, 0)
        tools_layout.addWidget(self.btn_fill, 0, 1)
        left_layout.addWidget(self.gb_tools)
        
        # Format
        self.gb_fmt = QGroupBox()
        fmt_layout = QVBoxLayout(self.gb_fmt)
        self.combo_bpp = QComboBox()
        self.combo_bpp.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.combo_bpp.setMinimumWidth(220)
        self.combo_bpp.addItems([
            "1BPP (1-bit)", 
            "2BPP (GB/GBC/NES)", 
            "4BPP Planar (SNES/GBA)",
            "4BPP Linear (Sega Genesis/MD)",
            "8BPP (VGA/256 colors)"
        ])
        fmt_layout.addWidget(self.combo_bpp)
        
        self.btn_auto = QPushButton()
        self.btn_auto.clicked.connect(self.auto_scan)
        fmt_layout.addWidget(self.btn_auto)
        
        # Width control
        self.lbl_width = QLabel()
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 1024)
        self.spin_width.setValue(16)
        self.spin_width.valueChanged.connect(self.set_fixed_width)
        
        fmt_layout.addWidget(self.lbl_width)
        fmt_layout.addWidget(self.spin_width)
        
        self.btn_apply_width = QPushButton("Apply")
        self.btn_apply_width.clicked.connect(lambda: self.set_fixed_width(self.spin_width.value()))
        fmt_layout.addWidget(self.btn_apply_width)
        
        left_layout.addWidget(self.gb_fmt)
        
        # Palette
        self.gb_pal = QGroupBox()
        pal_layout = QVBoxLayout(self.gb_pal)
        self.palette_widget = PaletteWidget()
        pal_layout.addWidget(self.palette_widget)
        left_layout.addWidget(self.gb_pal)
        
        # History
        self.gb_hist = QGroupBox("History")
        hist_layout = QHBoxLayout(self.gb_hist)
        self.btn_undo = QPushButton("↩ Undo")
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo = QPushButton("↪ Redo")
        self.btn_redo.clicked.connect(self.redo)
        hist_layout.addWidget(self.btn_undo)
        hist_layout.addWidget(self.btn_redo)
        left_layout.addWidget(self.gb_hist)
        
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)
        
        # Connect tools
        self.btn_draw.clicked.connect(lambda: self.set_tool("draw"))
        self.btn_fill.clicked.connect(lambda: self.set_tool("fill"))
        self.palette_widget.colorSelected.connect(self.set_color)
        
        self.combo_bpp.currentIndexChanged.connect(self.change_format)
        self.combo_bpp.setCurrentIndex(2)
        
        self.apply_theme()

        # Add initial empty tab
        self.new_file()
        
        self.retranslate_ui()
        
    def new_file(self):
        tab = TileTab(self)
        self.tabs.addTab(tab, "Untitled")
        self.tabs.setCurrentWidget(tab)
        
    def open_file(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, LOCALE[self.current_lang]["open"], "", LOCALE[self.current_lang]["all_files"])
        if fname:
            # Check if already open
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                if t.file_path == fname:
                    self.tabs.setCurrentIndex(i)
                    return

            try:
                tab = TileTab(self)
                tab.open_file(fname)
                self.tabs.addTab(tab, os.path.basename(fname))
                self.tabs.setCurrentWidget(tab)
            except Exception as e:
                QMessageBox.critical(self, LOCALE[self.current_lang]["error"], str(e))
                
    def save_file(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        # If tab has no file path, ask for it
        if not tab.file_path:
            fname, _ = QFileDialog.getSaveFileName(self, LOCALE[self.current_lang]["save_as"], "", LOCALE[self.current_lang]["all_files"])
            if fname:
                tab.file_path = fname
                self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(fname))
            else:
                return

        if tab.save_file():
             QMessageBox.information(self, LOCALE[self.current_lang]["success"], LOCALE[self.current_lang]["file_saved"])

    def import_bmp(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        fname, _ = QFileDialog.getOpenFileName(self, LOCALE[self.current_lang]["import_img"], "", LOCALE[self.current_lang]["img_filter"])
        if fname:
            img = QImage(fname)
            if not img.isNull():
                 tab.tile_grid.import_image(img)
                 
    def export_bmp(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        # Simply grab the widget? No, widget is virtual size.
        # We must render to QPixmap
        w = tab.tile_grid.width()
        h = tab.tile_grid.minimumHeight() # This is the full height
        if h < 10: h = 100
        
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.GlobalColor.black)
        
        # We need to force grid to paint into this pixmap
        # Use render?
        tab.tile_grid.render(pixmap)
        
        fname, _ = QFileDialog.getSaveFileName(self, LOCALE[self.current_lang]["export_img"], "", LOCALE[self.current_lang]["img_filter"])
        if fname:
            pixmap.save(fname)

    def change_format(self, idx):
        tab = self.tabs.currentWidget()
        if tab:
            tab.tile_grid.set_format(idx)

    def close_file(self):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            # If checking last tab, reset it instead of closing
            tab = self.tabs.widget(0)
            tab.tile_grid.set_data(b"")
            tab.file_path = None
            tab.history = HistoryManager()
            tab.tile_grid.history = tab.history
            self.tabs.setTabText(0, "Untitled")

    def on_tab_changed(self, index):
        tab = self.tabs.widget(index)
        if hasattr(tab, 'tile_grid'):
            # Update UI controls to match tab state
            # Match BPP combo
            current_fmt = tab.tile_grid.format
            # Find index in combo
            # ["1BPP", "2BPP", "NES 2BPP", "4BPP_PLANAR", "4BPP_LINEAR", "8BPP"]
            # Combo items: 
            # 0: "1BPP (1-bit)", 
            # 1: "2BPP (GB/GBC/NES)", 
            # 2: "4BPP Planar (SNES/GBA)",
            # 3: "4BPP Linear (Sega Genesis/MD)",
            # 4: "8BPP (VGA/256 colors)"
            
            idx = 2
            if "1BPP" in current_fmt: idx = 0
            elif "2BPP" in current_fmt: idx = 1
            elif "LINEAR" in current_fmt: idx = 3
            elif "8BPP" in current_fmt: idx = 4
            
            self.combo_bpp.blockSignals(True)
            self.combo_bpp.setCurrentIndex(idx)
            self.combo_bpp.blockSignals(False)
            
            # Match Width
            self.spin_width.blockSignals(True)
            self.spin_width.setValue(tab.tile_grid.width_tiles)
            self.spin_width.blockSignals(False)
            
            # Sync palette if needed (optional, maybe global palette is better for uniformity)
            
    def undo(self):
        tab = self.tabs.currentWidget()
        if tab:
            new_data = tab.history.undo()
            if new_data:
                tab.tile_grid.set_data(new_data)
            
    def redo(self):
        tab = self.tabs.currentWidget()
        if tab:
            new_data = tab.history.redo()
            if new_data:
                tab.tile_grid.set_data(new_data)
            
    def set_fixed_width(self, val):
        tab = self.tabs.currentWidget()
        if tab:
            tab.tile_grid.width_tiles = val
            tab.tile_grid.fixed_width = True
            tab.tile_grid.update()
            tab.tile_grid.setMinimumHeight(0) 
            tab.tile_grid.update()

    def auto_scan(self):
        tab = self.tabs.currentWidget()
        if not tab or not tab.tile_grid.tile_data: return
        
        # Test widths and BPPs
        bpps = [
            ("1BPP", TileFormat.decode_1bpp, 8, 0),
            ("2BPP", TileFormat.decode_2bpp, 16, 1),
            ("4BPP", TileFormat.decode_4bpp, 32, 2),
            ("4BPP_L", TileFormat.decode_4bpp_linear, 32, 3)
        ]
        
        best_overall_score = -1
        best_bpp_idx = 1 # Default 2BPP
        best_width = 16
        
        sample_size = min(len(tab.tile_grid.tile_data), 8192)
        sample = tab.tile_grid.tile_data[:sample_size]
        
        for bpp_name, decoder, bpt, bpp_idx in bpps:
            # For each BPP, test multiple widths
            num_total_tiles = len(sample) // bpt
            if num_total_tiles < 16: continue
            
            for w in [8, 16, 24, 32, 64]:
                if w > num_total_tiles: continue
                
                score = 0
                # Heuristic: check vertical similarity within tiles (BPP check)
                # AND horizontal similarity between adjacent tiles (Width check)
                for i in range(min(num_total_tiles - w, 32)):
                    pixels_curr = decoder(sample[i*bpt : (i+1)*bpt])
                    pixels_down = decoder(sample[(i+w)*bpt : (i+w+1)*bpt])
                    
                    # Vertical pattern within tile
                    for y in range(7):
                        for x in range(8):
                            if pixels_curr[y*8+x] == pixels_curr[(y+1)*8+x] and pixels_curr[y*8+x] != 0:
                                score += 1
                                
                    # Vertical pattern between tiles (matches width)
                    for x in range(8):
                        if pixels_curr[56+x] == pixels_down[x] and pixels_curr[56+x] != 0:
                            score += 2 # Higher weight for width match
                            
                if score > best_overall_score:
                    best_overall_score = score
                    best_bpp_idx = bpp_idx
                    best_width = w
        
        tab.tile_grid.fixed_width = True
        tab.tile_grid.width_tiles = best_width
        self.combo_bpp.setCurrentIndex(best_bpp_idx)
        self.spin_width.setValue(best_width)
        tab.tile_grid.update()
        
        fmt_name = bpps[best_bpp_idx][0]
        if fmt_name == "4BPP_L": fmt_name = "4BPP Linear (Sega)"
        
        msg = LOCALE[self.current_lang]["tm_det_fmt"].format(fmt_name) + f"\n{LOCALE[self.current_lang]['tm_width']}: {best_width}"
        QMessageBox.information(self, LOCALE[self.current_lang]["tm_auto"], msg)

    def set_tool(self, tool):
        tab = self.tabs.currentWidget()
        if tab:
            tab.tile_grid.current_tool = tool
        self.btn_draw.setDown(tool == "draw")
        self.btn_fill.setDown(tool == "fill")

    def set_color(self, idx):
        tab = self.tabs.currentWidget()
        if tab:
            tab.tile_grid.current_color_idx = idx


    def set_fixed_width(self, val):
        self.grid.fixed_width = True
        self.grid.width_tiles = val
        self.grid.update()

    def apply_theme(self, theme_name=None):
        if not theme_name:
            theme_name = self.global_settings.value("theme", "Dark (Default)")
        
        self.current_theme_name = theme_name
        self.global_settings.setValue("theme", theme_name)
        theme = THEMES.get(theme_name, THEMES["Dark (Default)"])
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(theme["bg"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["fg"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(theme["input_bg"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["alt_bg"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme["bg"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["fg"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(theme["fg"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(theme["btn_bg"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["btn_fg"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(theme["highlight"]))
        palette.setColor(QPalette.ColorRole.Link, QColor(theme["highlight"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["sel_bg"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme["sel_fg"]))
        self.setPalette(palette)
        
        css = f"""
            QMainWindow, QDialog {{ background-color: {theme['bg']}; color: {theme['fg']}; }}
            QWidget {{ background-color: {theme['bg']}; color: {theme['fg']}; }}
            QGroupBox {{ 
                border: 1px solid {theme['input_border']}; 
                margin-top: 6px; 
                padding-top: 10px; 
                color: {theme['highlight']};
                font-weight: bold;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{ 
                background-color: {theme['input_bg']}; 
                color: {theme['input_fg']}; 
                border: 1px solid {theme['input_border']}; 
                selection-background-color: {theme['sel_bg']};
                selection-color: {theme['sel_fg']};
            }}
            QComboBox::item {{ color: {theme['fg']}; background-color: {theme['input_bg']}; }}
            QComboBox::item:selected {{ background-color: {theme['sel_bg']}; }}
            QPushButton {{ 
                background-color: {theme['btn_bg']}; 
                color: {theme['btn_fg']}; 
                border: 1px solid {theme['input_border']}; 
                padding: 5px; 
                border-radius: 3px;
            }}
            QPushButton:hover {{ background-color: {theme['btn_hover']}; }}
            QPushButton:pressed {{ background-color: {theme['highlight']}; color: {theme['highlight_text']}; }}
            QScrollArea {{ border: none; }}
            QScrollBar:vertical {{ border: none; background: {theme['bg']}; width: 14px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {theme['btn_bg']}; min-height: 20px; border-radius: 7px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
            QMenu {{ background-color: {theme['bg']}; color: {theme['fg']}; border: 1px solid {theme['input_border']}; }}
            QMenu::item {{ padding: 5px 30px 5px 20px; }}
            QMenu::item:selected {{ background-color: {theme['sel_bg']}; }}
        """
        self.setStyleSheet(css)

    def change_lang(self, lang_code):
        self.current_lang = lang_code
        self.global_settings.setValue("lang", lang_code)
        self.retranslate_ui()
        
    def retranslate_ui(self):
        lang = self.current_lang
        self.setWindowTitle(f"STORM TILE MANAGER v{CURRENT_VERSION}")
        
        self.gb_tools.setTitle(LOCALE[lang]["tm_tools"])
        self.btn_draw.setText("🖌 " + LOCALE[lang]["tm_draw"])
        self.btn_fill.setText("🪣 " + LOCALE[lang]["tm_fill"])
        
        self.gb_fmt.setTitle(LOCALE[lang]["tm_format"])
        self.btn_auto.setText("🤖 " + LOCALE[lang]["tm_auto"])
        self.btn_auto.setToolTip(LOCALE[lang]["tm_auto_tip"])
        self.lbl_width.setText(LOCALE[lang]["tm_width"])
        self.btn_apply_width.setText(LOCALE[lang]["calc"])
        
        self.gb_pal.setTitle(LOCALE[lang]["tm_palette"])
        self.gb_hist.setTitle(LOCALE[lang].get("history", "History"))
        self.btn_undo.setText("↩ " + LOCALE[lang]["undo"])
        self.btn_redo.setText("↪ " + LOCALE[lang]["redo"])
        
        # Shortcuts
        self.btn_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.btn_redo.setShortcut(QKeySequence("Ctrl+Y"))
        
        # Reconstruct menus
        self.create_menus()

    def create_menus(self):
        self.menuBar().clear()
        
        
        # Program Menu

        self.menu_program = self.menuBar().addMenu("📱 " + LOCALE[self.current_lang]["program"])
        for key, name in [("suite", "suite"), ("hex_editor", "hex_editor"), ("tile_manager", "tile_manager"), ("game_dict", "game_dict")]:
            action = QAction(LOCALE[self.current_lang][name], self)
            action.triggered.connect(lambda checked, k=key: self.switch_app(k))
            if key == self.app_key:
                action.setEnabled(False)
                action.setCheckable(True)
                action.setChecked(True)
            self.menu_program.addAction(action)
            
        # ...


        
        # File Menu
        menu_file = self.menuBar().addMenu("📂 " + LOCALE[self.current_lang]["file"])
        
        act_open = QAction("📂 " + LOCALE[self.current_lang]["open"], self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.open_file)
        menu_file.addAction(act_open)
        
        act_save = QAction("💾 " + LOCALE[self.current_lang]["save"], self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_file)
        menu_file.addAction(act_save)
        
        act_close = QAction("❌ " + LOCALE[self.current_lang]["close"], self)
        act_close.triggered.connect(self.close_file)
        menu_file.addAction(act_close)
        
        menu_file.addSeparator()
        
        act_imp = QAction("📥 " + LOCALE[self.current_lang]["tm_import"] + "...", self)
        act_imp.triggered.connect(self.import_bmp)
        menu_file.addAction(act_imp)
        
        act_exp = QAction("📤 " + LOCALE[self.current_lang]["tm_export"] + "...", self)
        act_exp.triggered.connect(self.export_bmp)
        menu_file.addAction(act_exp)
        
        menu_file.addSeparator()
        
        act_imp_pal = QAction("🎨 " + LOCALE[self.current_lang]["tm_imp_pal"], self)
        act_imp_pal.triggered.connect(self.import_palette)
        menu_file.addAction(act_imp_pal)
        
        act_exp_pal = QAction("🎨 " + LOCALE[self.current_lang]["tm_exp_pal"], self)
        act_exp_pal.triggered.connect(self.export_palette)
        menu_file.addAction(act_exp_pal)
        
        menu_file.addSeparator()
        
        act_exit = QAction("🚪 " + LOCALE[self.current_lang]["exit"], self)
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)
        
        # View Menu
        menu_view = self.menuBar().addMenu("👁️ " + LOCALE[self.current_lang]["view"])
        
        menu_theme = menu_view.addMenu("🎨 " + LOCALE[self.current_lang]["theme"])
        for theme_name in THEMES.keys():
            act = QAction(theme_name, self)
            act.triggered.connect(lambda checked, t=theme_name: self.apply_theme(t))
            menu_theme.addAction(act)
            
        menu_lang = menu_view.addMenu("🌐 " + LOCALE[self.current_lang]["lang"])
        act_ru = QAction("Русский", self)
        act_ru.triggered.connect(lambda: self.change_lang("ru"))
        menu_lang.addAction(act_ru)
        
        menu_view.addSeparator()
        
        # Grid toggle
        self.act_grid = QAction("📐 " + LOCALE[self.current_lang].get("grid", "Grid"), self)
        self.act_grid.setCheckable(True)
        
        # Check current tab state
        show_grid = False
        if hasattr(self, 'tabs'):
            cur = self.tabs.currentWidget()
            if hasattr(cur, 'tile_grid'):
                show_grid = cur.tile_grid.show_grid
                
        self.act_grid.setChecked(show_grid)
        self.act_grid.triggered.connect(self.toggle_grid)
        menu_view.addAction(self.act_grid)
        
        # Grid size submenu
        menu_grid_size = menu_view.addMenu("📏 " + LOCALE[self.current_lang].get("grid_size", "Grid Size"))
        for size in [8, 16, 32]:
            act = QAction(f"{size}x{size}", self)
            act.triggered.connect(lambda checked, s=size: self.set_grid_size(s))
            menu_grid_size.addAction(act)
        
        menu_view.addSeparator()
        
        # Animation preview
        act_anim = QAction("🎬 " + LOCALE[self.current_lang].get("animation", "Animation Preview"), self)
        act_anim.triggered.connect(self.show_animation_dialog)
        menu_view.addAction(act_anim)
        
        # Help Menu
        menu_help = self.menuBar().addMenu("❓ " + LOCALE[self.current_lang]["help"])
        
        self.act_auto_upd = QAction("⚙️ " + LOCALE[self.current_lang]["auto_update"], self)
        self.act_auto_upd.setCheckable(True)
        self.act_auto_upd.setChecked(self.settings.value("auto_update", True, type=bool))
        self.act_auto_upd.triggered.connect(self.toggle_auto_update)
        menu_help.addAction(self.act_auto_upd)
        
        act_upd = QAction("🔄 " + LOCALE[self.current_lang]["check_updates"], self)
        act_upd.triggered.connect(lambda: self.check_updates(silent=False))
        menu_help.addAction(act_upd)
        
        act_gh = QAction("🌐 GitHub", self)
        act_gh.triggered.connect(lambda: webbrowser.open(f"https://github.com/{APP_REPOS.get(self.app_key, APP_REPOS['suite'])}"))
        menu_help.addAction(act_gh)
        
        act_about = QAction("ℹ️ " + LOCALE[self.current_lang]["about"], self)
        act_about.triggered.connect(lambda: show_about_dialog(self, self.app_key))
        menu_help.addAction(act_about)
        


    def toggle_auto_update(self):
        self.settings.setValue("auto_update", self.act_auto_upd.isChecked())
        
    def check_updates(self, silent=False):
        try:
            url = f"https://api.github.com/repos/ReiKatari/{self.github_repo}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': APP_NAME})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data["tag_name"]
                latest_ver = latest_tag.lstrip("v")
                
                if latest_ver != CURRENT_VERSION:
                    msg = f"{LOCALE[self.current_lang]['new_ver']} {latest_tag}\n{LOCALE[self.current_lang]['current']} {CURRENT_VERSION}\n\n{LOCALE[self.current_lang]['open_page']}"
                    
                    dlg = QDialog(self)
                    dlg.setWindowTitle(LOCALE[self.current_lang]["update_avail"])
                    dlg.resize(300, 150)
                    dlg.setStyleSheet(self.styleSheet())
                    layout = QVBoxLayout(dlg)
                    
                    lbl = QLabel(msg)
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(lbl)
                    
                    btn_box = QHBoxLayout()
                    btn_yes = QPushButton(LOCALE[self.current_lang]["yes"])
                    btn_yes.clicked.connect(lambda: [webbrowser.open(data["html_url"]), dlg.accept()])
                    btn_no = QPushButton(LOCALE[self.current_lang]["no"])
                    btn_no.clicked.connect(dlg.reject)
                    btn_box.addWidget(btn_yes)
                    btn_box.addWidget(btn_no)
                    layout.addLayout(btn_box)
                    
                    dlg.exec()
                else:
                    if not silent:
                        QMessageBox.information(self, LOCALE[self.current_lang]["info"], LOCALE[self.current_lang]["no_update"])
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, LOCALE[self.current_lang]["update_err"], f"{str(e)}")

    def import_palette(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Import Palette", "", "Adobe Color Table (*.act);;Microsoft Palette (*.pal)")
        if not fname: return
        
        try:
            colors = []
            if fname.lower().endswith(".act"):
                with open(fname, "rb") as f:
                    data = f.read()
                    count = 256
                    if len(data) >= 768:
                        for i in range(count):
                            if i*3+2 < len(data):
                                r, g, b = data[i*3], data[i*3+1], data[i*3+2]
                                colors.append(QColor(r, g, b))
            
            elif fname.lower().endswith(".pal"):
                with open(fname, "rb") as f:
                    sig = f.read(4)
                
                if sig == b"RIFF":
                    QMessageBox.warning(self, "Info", "RIFF PAL not yet fully supported.")
                    return
                else:
                    # Try JASC-PAL
                    with open(fname, "r") as f:
                        lines = f.readlines()
                        if lines and "JASC-PAL" in lines[0]:
                            for line in lines[3:]:
                                parts = line.split()
                                if len(parts) >= 3:
                                    colors.append(QColor(int(parts[0]), int(parts[1]), int(parts[2])))
            
            if colors:
                if hasattr(self, 'palette_widget'):
                    self.palette_widget.set_palette(colors)
                    
                    # Sync with current grid
                    cur = self.tabs.currentWidget()
                    if cur and hasattr(cur, 'tile_grid'):
                        cur.tile_grid.palette = colors
                        cur.tile_grid.update()
                        
                QMessageBox.information(self, "Success", f"Loaded {len(colors)} colors.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_palette(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export Palette", "", "Adobe Color Table (*.act);;JASC Palette (*.pal)")
        if not fname: return
        
        try:
            colors = self.palette_widget.colors
            if fname.lower().endswith(".act"):
                with open(fname, "wb") as f:
                    for i in range(256):
                        if i < len(colors):
                            c = colors[i]
                            f.write(bytes([c.red(), c.green(), c.blue()]))
                        else:
                            f.write(bytes([0, 0, 0]))
                            
            elif fname.lower().endswith(".pal"):
                with open(fname, "w") as f:
                    f.write("JASC-PAL\n0100\n256\n")
                    for i in range(256):
                        if i < len(colors):
                            c = colors[i]
                            f.write(f"{c.red()} {c.green()} {c.blue()}\n")
                        else:
                            f.write("0 0 0\n")
                            
            QMessageBox.information(self, "Success", "Palette saved.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.open_file(files[0])

    def toggle_grid(self, checked):
        cur = self.tabs.currentWidget()
        if cur and hasattr(cur, 'tile_grid'):
            cur.tile_grid.show_grid = checked
            cur.tile_grid.update()
        
    def set_grid_size(self, size):
        cur = self.tabs.currentWidget()
        if cur and hasattr(cur, 'tile_grid'):
            cur.tile_grid.grid_size = size
            cur.tile_grid.update()
        
    def show_animation_dialog(self):
        cur = self.tabs.currentWidget()
        if not cur or not hasattr(cur, 'tile_grid'):
             return

        dlg = AnimationPreviewDialog(cur.tile_grid, self)
        dlg.exec()

# Animation Preview Dialog
class AnimationPreviewDialog(QDialog):
    def __init__(self, tile_grid, parent=None):
        super().__init__(parent)
        self.tile_grid = tile_grid
        self.setWindowTitle(LOCALE.get(parent.current_lang, {}).get("animation", "Animation Preview"))
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(128, 128)
        self.preview_label.setStyleSheet("background-color: #222; border: 1px solid #555;")
        layout.addWidget(self.preview_label)
        
        # Frame list (tile indices)
        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frames (tile indices):"))
        self.frame_input = QLineEdit()
        self.frame_input.setPlaceholderText("0, 1, 2, 3")
        frame_layout.addWidget(self.frame_input)
        layout.addLayout(frame_layout)
        
        # FPS control
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        layout.addLayout(fps_layout)
        
        # Controls
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.btn_play.clicked.connect(self.toggle_play)
        btn_layout.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self.stop_animation)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)
        
        # Timer for animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.current_frame = 0
        self.frames = []
        
    def toggle_play(self):
        frames_text = self.frame_input.text()
        try:
            self.frames = [int(x.strip()) for x in frames_text.split(",") if x.strip()]
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid frame list. Use comma-separated tile indices.")
            return
            
        if not self.frames:
            QMessageBox.warning(self, "Error", "No frames specified.")
            return
            
        self.current_frame = 0
        fps = self.fps_spin.value()
        self.timer.start(1000 // fps)
        self.btn_play.setEnabled(False)
        
    def stop_animation(self):
        self.timer.stop()
        self.btn_play.setEnabled(True)
        
    def next_frame(self):
        if not self.frames:
            self.stop_animation()
            return
            
        tile_idx = self.frames[self.current_frame % len(self.frames)]
        self.render_tile(tile_idx)
        self.current_frame += 1
        
    def render_tile(self, tile_idx):
        tg = self.tile_grid
        
        # Calculate bytes per tile
        bpt = 32
        if "1BPP" in tg.format: bpt = 8
        elif "2BPP" in tg.format: bpt = 16
        elif "8BPP" in tg.format: bpt = 64
        
        offset = tile_idx * bpt
        if offset + bpt > len(tg.tile_data):
            return
            
        chunk = tg.tile_data[offset : offset + bpt]
        
        # Decode
        decoder = TileFormat.decode_4bpp
        if "1BPP" in tg.format: decoder = TileFormat.decode_1bpp
        elif "NES" in tg.format: decoder = TileFormat.decode_nes_2bpp
        elif "2BPP" in tg.format: decoder = TileFormat.decode_2bpp
        elif "LINEAR" in tg.format: decoder = TileFormat.decode_4bpp_linear
        
        pixels = decoder(chunk)
        
        # Create image
        img = QImage(8, 8, QImage.Format.Format_RGB32)
        for y in range(8):
            for x in range(8):
                idx = y * 8 + x
                c_idx = pixels[idx] if idx < len(pixels) else 0
                if c_idx < len(tg.palette):
                    img.setPixelColor(x, y, tg.palette[c_idx])
                else:
                    img.setPixelColor(x, y, QColor(0, 0, 0))
        
        # Scale for preview
        scaled = img.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio)
        self.preview_label.setPixmap(QPixmap.fromImage(scaled))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
