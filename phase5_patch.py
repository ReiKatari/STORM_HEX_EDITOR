import re
import math

TARGET_FILE = r"F:\MY SOFT\STORM HEX EDITOR\stormhexeditor.py"

ENTROPY_DIALOG = '''
class EntropyDialog(QDialog):
    def __init__(self, parent, data_source):
        super().__init__(parent)
        self.setWindowTitle("Entropy Analysis")
        self.setMinimumSize(700, 400)
        self.data = data_source
        self.parent_window = parent
        
        layout = QVBoxLayout(self)
        
        # Options
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Block Size:"))
        self.spin_block = QSpinBox()
        self.spin_block.setRange(64, 65536)
        self.spin_block.setValue(256)
        self.spin_block.setSingleStep(64)
        opt_layout.addWidget(self.spin_block)
        
        btn_analyze = QPushButton("Analyze")
        btn_analyze.clicked.connect(self.analyze)
        opt_layout.addWidget(btn_analyze)
        
        layout.addLayout(opt_layout)
        
        # Canvas for graph
        self.canvas = EntropyCanvas()
        layout.addWidget(self.canvas)
        
        # Info
        self.lbl_info = QLabel("Click 'Analyze' to calculate entropy")
        layout.addWidget(self.lbl_info)
        
    def calculate_entropy(self, data):
        if not data:
            return 0.0
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        length = len(data)
        entropy = 0.0
        for count in freq.values():
            if count > 0:
                p = count / length
                entropy -= p * math.log2(p)
        return entropy
        
    def analyze(self):
        if not self.data:
            return
            
        block_size = self.spin_block.value()
        total = len(self.data)
        
        self.lbl_info.setText("Analyzing...")
        QApplication.processEvents()
        
        entropy_values = []
        for i in range(0, total, block_size):
            chunk = bytes(self.data[i:i+block_size])
            e = self.calculate_entropy(chunk)
            entropy_values.append((i, e))
            
        self.canvas.set_data(entropy_values, total)
        
        avg_entropy = sum(e for _, e in entropy_values) / len(entropy_values) if entropy_values else 0
        self.lbl_info.setText(f"Blocks: {len(entropy_values)} | Avg Entropy: {avg_entropy:.2f} bits/byte | Max: 8.0")


class EntropyCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.entropy_data = []
        self.total_size = 0
        self.setMinimumHeight(200)
        
    def set_data(self, data, total):
        self.entropy_data = data
        self.total_size = total
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w, h = rect.width(), rect.height()
        
        # Background
        painter.fillRect(rect, QColor("#1a1a2e"))
        
        if not self.entropy_data:
            painter.setPen(QColor("#888888"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No data")
            return
            
        # Draw grid
        painter.setPen(QColor("#333355"))
        for i in range(1, 8):
            y = h - (i / 8) * h
            painter.drawLine(0, int(y), w, int(y))
            
        # Draw entropy bars
        bar_width = max(1, w / len(self.entropy_data))
        
        for idx, (offset, entropy) in enumerate(self.entropy_data):
            x = idx * bar_width
            bar_h = (entropy / 8.0) * h
            
            # Color based on entropy (green=low, yellow=medium, red=high)
            if entropy < 3:
                color = QColor("#00ff88")
            elif entropy < 6:
                color = QColor("#ffcc00")
            else:
                color = QColor("#ff4444")
                
            painter.fillRect(int(x), int(h - bar_h), max(1, int(bar_width) - 1), int(bar_h), color)
            
        # Labels
        painter.setPen(QColor("#ffffff"))
        painter.drawText(5, 15, "8.0")
        painter.drawText(5, h - 5, "0.0")
'''

def patch():
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Insert before StringsDialog
    marker = "class StringsDialog(QDialog):"
    if marker in content:
        content = content.replace(marker, ENTROPY_DIALOG + "\n" + marker)
        print("EntropyDialog and EntropyCanvas added.")
    else:
        print("Warning: Could not find StringsDialog marker.")
        return

    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patch applied successfully.")

if __name__ == "__main__":
    patch()
