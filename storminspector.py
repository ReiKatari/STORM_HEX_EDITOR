import struct
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, QLabel, 
                             QLineEdit, QTextEdit, QTreeWidget, QTreeWidgetItem, QSplitter,
                             QPushButton, QMessageBox, QHBoxLayout, QComboBox)
from PyQt6.QtCore import Qt
from stormbase import LOCALE

class StormInspector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_ref = b""
        self.current_offset = 0
        self.is_little_endian = True
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Endian)
        header = QHBoxLayout()
        self.combo_endian = QComboBox()
        self.combo_endian.addItems(["Little Endian", "Big Endian"])
        self.combo_endian.currentIndexChanged.connect(self.on_endian_change)
        header.addWidget(QLabel("Endian:"))
        header.addWidget(self.combo_endian)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: Scalars
        self.tab_scalars = QWidget()
        self.init_scalars_ui()
        self.tabs.addTab(self.tab_scalars, "Scalars")
        
        # Tab 2: Structures
        self.tab_structs = QWidget()
        self.init_structs_ui()
        self.tabs.addTab(self.tab_structs, "Structures")
        
        self.retranslate_ui()
        
    def init_scalars_ui(self):
        self.scalar_layout = QFormLayout(self.tab_scalars)
        self.lbl_i8 = QLineEdit(); self.lbl_i8.setReadOnly(True)
        self.lbl_u8 = QLineEdit(); self.lbl_u8.setReadOnly(True)
        self.lbl_i16 = QLineEdit(); self.lbl_i16.setReadOnly(True)
        self.lbl_u16 = QLineEdit(); self.lbl_u16.setReadOnly(True)
        self.lbl_i32 = QLineEdit(); self.lbl_i32.setReadOnly(True)
        self.lbl_u32 = QLineEdit(); self.lbl_u32.setReadOnly(True)
        self.lbl_f32 = QLineEdit(); self.lbl_f32.setReadOnly(True)
        self.lbl_f64 = QLineEdit(); self.lbl_f64.setReadOnly(True)
        
        self.scalar_layout.addRow("Int8:", self.lbl_i8)
        self.scalar_layout.addRow("UInt8:", self.lbl_u8)
        self.scalar_layout.addRow("Int16:", self.lbl_i16)
        self.scalar_layout.addRow("UInt16:", self.lbl_u16)
        self.scalar_layout.addRow("Int32:", self.lbl_i32)
        self.scalar_layout.addRow("UInt32:", self.lbl_u32)
        self.scalar_layout.addRow("Float:", self.lbl_f32)
        self.scalar_layout.addRow("Double:", self.lbl_f64)

    def retranslate_ui(self, lang="ru"):
        # We need to find the labels in the QFormLayout or recreate it.
        # Actually, let's just update the tab titles and known labels.
        self.tabs.setTabText(0, LOCALE[lang].get("scalars", "Scalars"))
        self.tabs.setTabText(1, LOCALE[lang].get("structures", "Structures"))
        
        # Endian label?
        # To avoid complex layout surgery, we can find the labels.
        # But for now, let's just focus on the main ones.
        
        # Re-applying rows to QFormLayout is tricky if we want to change text.
        # Let's just track the label widgets.
        # Or better: just replace the text for the QLabels in the rows.
        for i in range(self.scalar_layout.rowCount()):
            label_item = self.scalar_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label_item:
                p_label = label_item.widget()
                if isinstance(p_label, QLabel):
                     # Match by index
                     keys = ["int8", "uint8", "int16", "uint16", "int32", "uint32", "float", "double"]
                     if i < len(keys):
                         p_label.setText(LOCALE[lang].get(keys[i], keys[i].capitalize()) + ":")
        
    def init_structs_ui(self):
        layout = QVBoxLayout(self.tab_structs)
        
        # Definition
        layout.addWidget(QLabel("Struct Fmt (Python):"))
        self.txt_def = QTextEdit()
        self.txt_def.setPlaceholderText("< I 4s H")
        self.txt_def.setText("< I 4s H") # Default: LE, U32, 4-char, U16
        self.txt_def.setMaximumHeight(50)
        layout.addWidget(self.txt_def)
        
        btn_apply = QPushButton("Parse at Cursor")
        btn_apply.clicked.connect(self.parse_struct)
        layout.addWidget(btn_apply)
        
        # Results
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Field", "Value"])
        layout.addWidget(self.tree)
        
    def on_endian_change(self, idx):
        self.is_little_endian = (idx == 0)
        self.update_scalars()
        if self.tabs.currentWidget() == self.tab_structs:
             pass # Maybe re-parse

    def set_data(self, data, offset, little_endian=True):
        self.data_ref = data
        self.current_offset = offset
        # self.is_little_endian = little_endian # Controlled by UI now
        self.update_scalars()
        # Auto-parse struct if visible? Maybe heavy.
        if self.tabs.currentWidget() == self.tab_structs:
             # Only if user wants?
             pass 
            
    def update_scalars(self):
        if not self.data_ref or self.current_offset < 0 or self.current_offset >= len(self.data_ref):
            self.clear_scalars()
            return
            
        endian = "<" if self.is_little_endian else ">"
        
        # Helper to unpack
        def unpack(fmt, offs):
            try:
                size = struct.calcsize(fmt)
                if offs + size > len(self.data_ref): return "---"
                val = struct.unpack(endian + fmt, self.data_ref[offs:offs+size])[0]
                return str(val)
            except: return "Error"
            
        self.lbl_i8.setText(unpack("b", self.current_offset))
        self.lbl_u8.setText(unpack("B", self.current_offset))
        self.lbl_i16.setText(unpack("h", self.current_offset))
        self.lbl_u16.setText(unpack("H", self.current_offset))
        self.lbl_i32.setText(unpack("i", self.current_offset))
        self.lbl_u32.setText(unpack("I", self.current_offset))
        self.lbl_f32.setText(unpack("f", self.current_offset))
        self.lbl_f64.setText(unpack("d", self.current_offset))

    def clear_scalars(self):
        self.lbl_i8.setText("")
        # ... (lazy clearing)
        
    def parse_struct(self):
        fmt = self.txt_def.toPlainText().strip()
        if not fmt: return
        
        self.tree.clear()
        try:
            size = struct.calcsize(fmt)
            if self.current_offset + size > len(self.data_ref):
                self.tree.addTopLevelItem(QTreeWidgetItem(["Error", "End of file"]))
                return
                
            vals = struct.unpack(fmt, self.data_ref[self.current_offset : self.current_offset + size])
            
            for i, val in enumerate(vals):
                str_val = str(val)
                if isinstance(val, bytes):
                    try: str_val = f"{val.decode('utf-8', 'ignore')} (Hex: {val.hex()})"
                    except: str_val = val.hex()
                    
                item = QTreeWidgetItem([f"Field {i}", str_val])
                self.tree.addTopLevelItem(item)
                
        except Exception as e:
            self.tree.addTopLevelItem(QTreeWidgetItem(["Error", str(e)]))
