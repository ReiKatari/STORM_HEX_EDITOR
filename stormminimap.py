from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QBrush

class HexMinimap(QWidget):
    jumpToOffset = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(20) # Thin strip
        self.data_ref = b"" # Reference to data
        self.total_size = 0
        self.image = None
        self.viewport_start = 0
        self.viewport_size = 0
        self.byte_per_pixel = 16 # How many bytes one vertical pixel represents (zoom level)
        # width is fixed ~20px. One line in image = 20 pixels width.
        # So we can map bytes to pixels.
        # Simple approach: Heatmap style. Each pixel represents a chunk of bytes.
        
        self.apply_theme({"bg": "#2e2e2e"})
        
    def apply_theme(self, theme):
        bg = theme.get("bg", "#2e2e2e")
        self.setStyleSheet(f"background-color: {bg};")
        self.refresh_map()
        
    def set_data(self, data):
        self.data_ref = data
        self.total_size = len(data)
        self.refresh_map()
        
    def set_viewport(self, start, size):
        self.viewport_start = start
        self.viewport_size = size
        self.update() # Just repaint overlay
        
    def refresh_map(self):
        if not self.total_size:
            self.image = None
            self.update()
            return
            
        w = self.width()
        h = self.height()
        
        # Determine density.
        # If file is huge, we map N bytes to 1 pixel height.
        # If file is small, we map 1 byte to N pixels height?
        # Let's assume typical hex editor minimap:
        # Fits whole file? Or just a scrollbar replacement?
        # Usually it REPLACES the scrollbar track or sits next to it.
        # If it fits whole file, height is fixed to widget height.
        
        # Simple density:
        self.bytes_per_v_pixel = max(1, self.total_size / max(1, h))
        
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor("#2e2e2e"))
        
        # Fast render logic (approximation)
        # We can't iterate all bytes for TB files in Python.
        # For < 1MB files we can iterate.
        # For large files, we sample.
        
        ptr = 0
        step = self.bytes_per_v_pixel
        
        # We can use QPainter on QImage
        painter = QPainter(img)
        
        # We draw strips.
        # Color based on byte value entropy or simply value?
        # Blue = 00, White = FF, Green = ASCII...
        
        # Optim: If step is huge, just pick random byte or average?
        # Sample every step bytes.
        
        try:
            for y in range(h):
                offset = int(y * step)
                if offset >= self.total_size: break
                
                # Sample a few bytes
                chunk_len = max(1, int(step))
                chunk = self.data_ref[offset : offset + min(10, chunk_len)]
                if not chunk: break
                
                # Analyze chunk
                # 0x00 -> Dark
                # 0xFF -> Bright
                # Printable -> Color
                
                b = chunk[0]
                if b == 0:
                    col = QColor(30, 30, 30)
                elif 32 <= b <= 126:
                    col = QColor(100, 200, 100) # Greenish for ASCII
                elif b == 0xFF:
                    col = QColor(200, 200, 200) # Whitish
                else:
                    col = QColor(100, 100, 150) # Blueish
                    
                painter.setPen(col)
                painter.drawLine(0, y, w, y)
        except Exception:
            pass
            
        painter.end()
        self.image = img
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        if self.image:
            painter.drawImage(0, 0, self.image)
            
        # Draw Viewport Overlay
        if self.total_size > 0:
            h = self.height()
            y_start = (self.viewport_start / self.total_size) * h
            y_end = ((self.viewport_start + self.viewport_size) / self.total_size) * h
            h_vp = max(2, y_end - y_start)
            
            painter.setPen(QPen(QColor(255, 255, 0, 100), 2))
            painter.setBrush(QBrush(QColor(255, 255, 0, 30)))
            painter.drawRect(0, int(y_start), self.width(), int(h_vp))
            
    def mousePressEvent(self, event):
        y = event.pos().y()
        h = self.height()
        if h > 0 and self.total_size > 0:
            ratio = y / h
            offset = int(ratio * self.total_size)
            self.jumpToOffset.emit(offset)
            
    def resizeEvent(self, event):
        self.refresh_map()
        super().resizeEvent(event)
