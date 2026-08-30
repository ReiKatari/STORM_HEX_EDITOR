
import sys
import os
import re
import urllib.request
import json
import webbrowser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFileDialog, 
                             QMessageBox, QLineEdit, QGroupBox, QSplitter, QTextEdit, QHeaderView,
                             QDialog, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor

# --- STORM SUITE IMPORTS ---
from stormbase import StormApp, LOCALE, THEMES, resource_path, APP_NAME, CURRENT_VERSION, AUTHOR, APP_REPOS, show_about_dialog

class TableEntry:
    def __init__(self, hex_code, char):
        self.hex_code = hex_code # String "00" or "0A10"
        self.char = char         # String "A" or "<EOF>"

class TableManager:
    def __init__(self):
        self.entries = [] # List of TableEntry
        self.hex_map = {} # hex_str -> char
        self.current_file = None
        
    def load_tbl(self, filename):
        try:
            entries = []
            hex_map = {}
            
            # Check if binary
            with open(filename, "rb") as bf:
                head = bf.read(1024)
                if b'\0' in head:
                    # Likely binary
                    pass # We can handle this in load_tbl or caller
            
            # Try multiple encodings
            content = None
            for enc in ["utf-8", "cp1251", "latin-1"]:
                try:
                    with open(filename, "r", encoding=enc) as f:
                        content = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # Last resort: open as bytes and decode with replace
                with open(filename, "rb") as f:
                    content = f.read().decode("utf-8", errors="replace").splitlines()

            for line in content:
                if "=" in line:
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        h = parts[0].strip()
                        c = parts[1]
                        entries.append(TableEntry(h, c))
                        hex_map[h.upper()] = c
            
            self.entries = entries
            self.hex_map = hex_map
            self.current_file = filename
            
            # Count '=' to see if it's really a TBL
            if len(self.entries) < 5 and os.path.getsize(filename) > 1024:
                return "binary" # Special return for warning
                
            return True
        except Exception as e:
            print(f"Error loading TBL: {e}")
            return False
            
    def save_tbl(self, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for entry in self.entries:
                    f.write(f"{entry.hex_code}={entry.char}\n")
            self.current_file = filename
            return True
        except Exception as e:
            print(f"Error saving TBL: {e}")
            return False
            
    def add_entry(self, hex_code, char):
        self.entries.append(TableEntry(hex_code, char))
        self.hex_map[hex_code.upper()] = char

# History Manager for Undo/Redo (up to 100 entries)
class HistoryManager:
    def __init__(self, max_entries=100):
        self.max_entries = max_entries
        self.undo_stack = []
        self.redo_stack = []
        
    def push(self, state):
        """Push a copy of current state to undo stack"""
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_entries:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        
    def undo(self):
        """Pop from undo stack, push current to redo"""
        if self.undo_stack:
            return self.undo_stack.pop()
        return None
        
    def redo(self):
        """Pop from redo stack"""
        if self.redo_stack:
            return self.redo_stack.pop()
        return None
        
    def push_redo(self, state):
        """Push state to redo stack (called before applying undo)"""
        self.redo_stack.append(state)
        
    def can_undo(self):
        return len(self.undo_stack) > 0
        
    def can_redo(self):
        return len(self.redo_stack) > 0

class DictionaryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_manager = TableManager()
        self.history = HistoryManager(100)
        self.current_lang = "en" # Default, updated by MainWindow
        self.backup_state = None # For "Back" functionality
        
        # Main Layout (Splitter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Table Editor
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5,5,5,5)
        
        self.tbl_editor = QTableWidget()
        self.tbl_editor.setColumnCount(2)
        header = self.tbl_editor.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.tbl_editor)
        
        # Add Entry Form
        form_layout = QHBoxLayout()
        self.inp_hex = QLineEdit()
        self.inp_char = QLineEdit()
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self.add_entry_ui)
        
        form_layout.addWidget(self.inp_hex)
        form_layout.addWidget(self.inp_char)
        form_layout.addWidget(self.btn_add)
        
        self.btn_gen_ascii = QPushButton()
        self.btn_gen_ascii.clicked.connect(self.generate_ascii_tbl)
        form_layout.addWidget(self.btn_gen_ascii)
        
        # Back Button (Initially hidden)
        self.btn_back = QPushButton("🔙 Back")
        self.btn_back.setVisible(False)
        self.btn_back.clicked.connect(self.restore_backup)
        form_layout.addWidget(self.btn_back)
        
        left_layout.addLayout(form_layout)
        
        self.splitter.addWidget(left_panel)
        
        # Right: Testing / Search
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5,5,5,5)
        
        self.gb_test = QGroupBox()
        test_layout = QVBoxLayout(self.gb_test)
        
        self.txt_input = QTextEdit()
        test_layout.addWidget(self.txt_input)
        
        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_decode = QPushButton()
        self.btn_decode.clicked.connect(self.decode_text)
        btn_row.addWidget(self.btn_decode)
        
        self.btn_encode = QPushButton()
        self.btn_encode.clicked.connect(self.encode_text)
        btn_row.addWidget(self.btn_encode)
        test_layout.addLayout(btn_row)
        
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        test_layout.addWidget(self.txt_output)

        right_layout.addWidget(self.gb_test)
        self.splitter.addWidget(right_panel)
        
        layout.addWidget(self.splitter)
        
    def refresh_table(self):
        self.tbl_editor.setRowCount(0)
        self.tbl_editor.setRowCount(len(self.table_manager.entries))
        for r, entry in enumerate(self.table_manager.entries):
            i1 = QTableWidgetItem(entry.hex_code)
            i2 = QTableWidgetItem(entry.char)
            self.tbl_editor.setItem(r, 0, i1)
            self.tbl_editor.setItem(r, 1, i2)
            
    def add_entry_ui(self):
        h = self.inp_hex.text().strip()
        c = self.inp_char.text()
        if h and c:
            self.save_state_to_history()
            self.table_manager.add_entry(h, c)
            self.refresh_table()
            self.inp_hex.clear()
            self.inp_char.clear()

    def generate_ascii_tbl(self):
        # Backup current state
        self.backup_state = (list(self.table_manager.entries), self.table_manager.hex_map.copy())
        self.btn_back.setVisible(True)
        
        self.table_manager.entries = []
        self.table_manager.hex_map = {}
        for i in range(0x20, 0x100):
            h = f"{i:02X}"
            c = chr(i)
            self.table_manager.add_entry(h, c)
        self.refresh_table()

    def restore_backup(self):
        if self.backup_state:
            self.table_manager.entries = self.backup_state[0]
            self.table_manager.hex_map = self.backup_state[1]
            self.refresh_table()
            self.backup_state = None
            self.btn_back.setVisible(False)

    def decode_text(self):
        text = self.txt_input.toPlainText().strip()
        hex_str = re.sub(r'[^0-9A-Fa-f]', '', text)
        result = ""
        idx = 0
        while idx < len(hex_str):
            matched = False
            for length in range(8, 1, -2): 
                if idx + length <= len(hex_str):
                    code = hex_str[idx : idx+length].upper()
                    if code in self.table_manager.hex_map:
                        result += self.table_manager.hex_map[code]
                        idx += length
                        matched = True
                        break
            if not matched:
                if idx + 2 <= len(hex_str):
                     result += f"[{hex_str[idx:idx+2]}]"
                     idx += 2
                else: break
        self.txt_output.setPlainText(result)
    
    def encode_text(self):
        text = self.txt_input.toPlainText()
        char_map = {}
        for entry in self.table_manager.entries:
            if entry.char not in char_map:
                char_map[entry.char] = entry.hex_code
        result = ""
        i = 0
        while i < len(text):
            matched = False
            for length in range(4, 0, -1):
                if i + length <= len(text):
                    substr = text[i:i+length]
                    if substr in char_map:
                        result += char_map[substr] + " "
                        i += length
                        matched = True
                        break
            if not matched:
                result += f"[{ord(text[i]):02X}] "
                i += 1
        self.txt_output.setPlainText(result.strip())

    def save_state_to_history(self):
        state = [(e.hex_code, e.char) for e in self.table_manager.entries]
        self.history.push(state)

class MainWindow(StormApp):
    def __init__(self):
        super().__init__("game_dict")
        # Managers moved to tabs
        self.rom_data = None  
        self.mte_entries = {} 
        self.setAcceptDrops(True)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"STORM GAME DICTIONARY v{CURRENT_VERSION}")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tabs)
        
        self.apply_theme()
        
        # Add initial tab
        self.new_file()
        
        self.retranslate_ui()
        
    def new_file(self):
        tab = DictionaryTab(self)
        self.tabs.addTab(tab, "Untitled")
        self.tabs.setCurrentWidget(tab)
        
    def open_tbl(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, LOCALE[self.current_lang]["open_tbl"], "", "Table Files (*.tbl);;All Files (*.*)")
        if fname:
            # Check if file already open
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                if t.table_manager.current_file == fname:
                    self.tabs.setCurrentIndex(i)
                    return
            
            # Use current empty tab or create new
            current_tab = self.tabs.currentWidget()
            if not current_tab.table_manager.entries and not current_tab.table_manager.current_file:
                tab = current_tab
            else:
                tab = DictionaryTab(self)
                self.tabs.addTab(tab, os.path.basename(fname))
                self.tabs.setCurrentWidget(tab)
            
            res = tab.table_manager.load_tbl(fname)
            if res == "binary":
                QMessageBox.warning(self, LOCALE[self.current_lang]["warning"], LOCALE[self.current_lang]["gd_warn_binary"])
            
            if res:
                tab.refresh_table()
                self.tabs.setTabText(self.tabs.indexOf(tab), os.path.basename(fname))

    def close_file(self):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            # If default tab, reset it
            tab = self.tabs.widget(0)
            tab.table_manager.entries = []
            tab.table_manager.hex_map = {}
            tab.table_manager.current_file = None
            tab.history = HistoryManager(100)
            tab.refresh_table()
            self.tabs.setTabText(0, "Untitled")

    def save_tbl(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        fname = tab.table_manager.current_file
        if not fname:
            fname, _ = QFileDialog.getSaveFileName(self, "Save TBL", "", "Table Files (*.tbl)")
            
        if fname:
            if tab.table_manager.save_tbl(fname):
                 self.tabs.setTabText(self.tabs.indexOf(tab), os.path.basename(fname))
                 QMessageBox.information(self, "Success", "Table saved.")

    def undo_action(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        if not tab.history.can_undo():
            return
        # Save current state for redo
        current = [(e.hex_code, e.char) for e in tab.table_manager.entries]
        tab.history.push_redo(current)
        # Restore previous state
        prev_state = tab.history.undo()
        if prev_state is not None:
            tab.table_manager.entries = [TableEntry(h, c) for h, c in prev_state]
            tab.table_manager.hex_map = {h.upper(): c for h, c in prev_state}
            tab.refresh_table()
            
    def redo_action(self):
        tab = self.tabs.currentWidget()
        if not tab: return
        
        if not tab.history.can_redo():
            return
        # Save current for undo
        current = [(e.hex_code, e.char) for e in tab.table_manager.entries]
        tab.history.push(current)
        # Restore redo state
        redo_state = tab.history.redo()
        if redo_state is not None:
            tab.table_manager.entries = [TableEntry(h, c) for h, c in redo_state]
            tab.table_manager.hex_map = {h.upper(): c for h, c in redo_state}
            tab.refresh_table()

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
            QMenu {{ background-color: {theme['bg']}; color: {theme['fg']}; border: 1px solid {theme['input_border']}; }}
            QMenu::item {{ padding: 5px 30px 5px 20px; }}
            QMenu::item:selected {{ background-color: {theme['sel_bg']}; }}
            QTableWidget {{ 
                background-color: {theme['tree_bg']}; 
                color: {theme['fg']}; 
                gridline-color: {theme['input_border']}; 
                selection-background-color: {theme['sel_bg']}; 
                selection-color: {theme['sel_fg']};
            }}
            QHeaderView::section {{ 
                background-color: {theme['btn_bg']}; 
                color: {theme['btn_fg']}; 
                border: 1px solid {theme['input_border']}; 
            }}
            QScrollArea {{ border: none; }}
            QScrollBar:vertical {{ border: none; background: {theme['bg']}; width: 14px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {theme['btn_bg']}; min-height: 20px; border-radius: 7px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; }}
        """
        self.setStyleSheet(css)

    def change_lang(self, lang_code):
        self.current_lang = lang_code
        self.global_settings.setValue("lang", lang_code)
        self.retranslate_ui()
        
    def retranslate_ui(self):
        title = f"STORM GAME DICTIONARY v{CURRENT_VERSION}"
        if self.table_manager.current_file:
             title += f" - {os.path.basename(self.table_manager.current_file)}"
        self.setWindowTitle(title)
        
        self.create_menus()
        
        if hasattr(self, 'tbl_editor'):
            self.tbl_editor.setHorizontalHeaderLabels([LOCALE[self.current_lang]["gd_hex"], LOCALE[self.current_lang]["gd_char"]])
            
            self.inp_hex.setPlaceholderText(LOCALE[self.current_lang]["gd_hex_hint"])
            self.inp_char.setPlaceholderText(LOCALE[self.current_lang]["gd_char_hint"])
            self.txt_input.setPlaceholderText(LOCALE[self.current_lang]["gd_input_hint"])
            self.txt_output.setPlaceholderText(LOCALE[self.current_lang]["gd_result"])
            
            self.btn_add.setText(LOCALE[self.current_lang]["gd_add"])
            self.gb_test.setTitle(LOCALE[self.current_lang]["gd_test"])
            self.btn_decode.setText(LOCALE[self.current_lang]["gd_decode"])
            self.btn_encode.setText(LOCALE[self.current_lang]["gd_encode"])

    def create_menus(self):
        self.menuBar().clear()
        
        # Program
        menu_prog = self.menuBar().addMenu("📱 " + LOCALE[self.current_lang]["program"])
        for key, name in [("suite", "suite"), ("hex_editor", "hex_editor"), ("tile_manager", "tile_manager"), ("game_dict", "game_dict")]:
            action = QAction(LOCALE[self.current_lang][name], self)
            action.triggered.connect(lambda checked, k=key: self.switch_app(k))
            if key == self.app_key:
                action.setEnabled(False)
                action.setCheckable(True)
                action.setChecked(True)
            menu_prog.addAction(action)
            
        # File
        menu_file = self.menuBar().addMenu("📁 " + LOCALE[self.current_lang]["file"])
        
        act_open = QAction("📂 " + LOCALE[self.current_lang]["gd_open_tbl"] + "...", self)
        act_open.triggered.connect(self.open_tbl)
        menu_file.addAction(act_open)
        
        act_save.triggered.connect(self.save_tbl)
        menu_file.addAction(act_save)
        
        act_close = QAction("❌ " + LOCALE[self.current_lang]["close"], self)
        act_close.triggered.connect(self.close_file)
        menu_file.addAction(act_close)
        
        menu_file.addSeparator()
        
        act_exit = QAction("🚪 " + LOCALE[self.current_lang]["exit"], self)
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # View
        menu_view = self.menuBar().addMenu("👁️ " + LOCALE[self.current_lang]["view"])
        
        # Themes
        menu_theme = menu_view.addMenu("🎨 " + LOCALE[self.current_lang]["theme"])
        for theme_name in THEMES.keys():
            act = QAction(theme_name, self)
            act.triggered.connect(lambda checked, t=theme_name: self.apply_theme(t))
            menu_theme.addAction(act)
            
        # Language
        menu_lang = menu_view.addMenu("🌐 " + LOCALE[self.current_lang]["lang"])
        act_ru = QAction("Русский", self)
        act_ru.triggered.connect(lambda: self.change_lang("ru"))
        menu_lang.addAction(act_ru)
        
        act_en = QAction("English", self)
        act_en.triggered.connect(lambda: self.change_lang("en"))
        menu_lang.addAction(act_en)
        
        # Help
        menu_help = self.menuBar().addMenu("❓ " + LOCALE[self.current_lang]["help"])
        
        self.act_auto_upd = QAction("⚙️ " + LOCALE[self.current_lang]["auto_update"], self)
        self.act_auto_upd.setCheckable(True)
        self.act_auto_upd.setChecked(self.settings.value("auto_update", True, type=bool))
        self.act_auto_upd.triggered.connect(self.toggle_auto_update)
        menu_help.addAction(self.act_auto_upd)
        
        act_upd = QAction("🔄 " + LOCALE[self.current_lang]["check_updates"], self)
    def retranslate_ui(self):
        title = f"STORM GAME DICTIONARY v{CURRENT_VERSION}"
        self.setWindowTitle(title)
        
        self.create_menus()
        
        # Iterate tabs and update their UI
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            # Update headers
            if hasattr(tab, 'tbl_editor'):
                tab.tbl_editor.setHorizontalHeaderLabels([LOCALE[self.current_lang]["gd_hex"], LOCALE[self.current_lang]["gd_char"]])
                tab.inp_hex.setPlaceholderText(LOCALE[self.current_lang]["gd_hex_hint"])
                tab.inp_char.setPlaceholderText(LOCALE[self.current_lang]["gd_char_hint"])
                tab.btn_add.setText("➕ " + LOCALE[self.current_lang]["gd_add"])
                tab.gb_test.setTitle("🕵️ " + LOCALE[self.current_lang]["gd_test"])
                tab.txt_input.setPlaceholderText(LOCALE[self.current_lang]["gd_input_hint"])
                tab.btn_decode.setText("🔍 " + LOCALE[self.current_lang]["gd_decode"])
                tab.btn_encode.setText("✍️ " + LOCALE[self.current_lang]["gd_encode"])
                tab.txt_output.setPlaceholderText(LOCALE[self.current_lang]["gd_result"])
                tab.btn_gen_ascii.setText("⌨️ " + LOCALE[self.current_lang]["gd_auto_ascii"])
                tab.btn_back.setText("🔙 " + LOCALE[self.current_lang].get("back", "Back"))
        
    def create_menus(self):
        bar = self.menuBar()
        bar.clear()
        
        # Program Menu (from base)
        self.init_common_ui() 
        
        # Edit Menu - Undo/Redo
        menu_edit = bar.addMenu("✏️ " + LOCALE[self.current_lang]["edit"])
        
        act_undo = QAction("↩ " + LOCALE[self.current_lang]["undo"], self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self.undo_action)
        menu_edit.addAction(act_undo)
        
        act_redo = QAction("↪ " + LOCALE[self.current_lang]["redo"], self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self.redo_action)
        menu_edit.addAction(act_redo)
        
        # View Menu
        menu_view = bar.addMenu("👁️ " + LOCALE[self.current_lang]["view"])
        menu_theme = menu_view.addMenu("🎨 " + LOCALE[self.current_lang]["theme"])
        for theme_name in THEMES.keys():
            act = QAction(theme_name, self)
            act.triggered.connect(lambda checked, t=theme_name: self.apply_theme(t))
            menu_theme.addAction(act)
            
        menu_lang = menu_view.addMenu("🌐 " + LOCALE[self.current_lang]["lang"])
        for l_code, l_name in [("ru", "Русский"), ("en", "English")]:
            act = QAction(l_name, self)
            act.triggered.connect(lambda checked, c=l_code: self.change_lang(c))
            menu_lang.addAction(act)
        
        # ROM Tools Menu
        menu_rom = bar.addMenu("🎮 " + LOCALE[self.current_lang].get("rom_tools", "ROM Tools"))
        
        act_open_rom = QAction("📂 " + LOCALE[self.current_lang].get("open_rom", "Open ROM"), self)
        act_open_rom.triggered.connect(self.open_rom)
        menu_rom.addAction(act_open_rom)
        
        act_search_rom = QAction("🔍 " + LOCALE[self.current_lang].get("search_rom", "Search in ROM"), self)
        act_search_rom.triggered.connect(self.search_in_rom)
        menu_rom.addAction(act_search_rom)
        
        act_detect = QAction("🔎 " + LOCALE[self.current_lang].get("auto_detect", "Auto-detect Encoding"), self)
        act_detect.triggered.connect(self.auto_detect_encoding)
        menu_rom.addAction(act_detect)
        
        menu_rom.addSeparator()
        
        act_export = QAction("📤 " + LOCALE[self.current_lang].get("export_script", "Export Script"), self)
        act_export.triggered.connect(self.export_script)
        menu_rom.addAction(act_export)
        
        act_import = QAction("📥 " + LOCALE[self.current_lang].get("import_script", "Import Script"), self)
        act_import.triggered.connect(self.import_script)
        menu_rom.addAction(act_import)

        # Help
        menu_help = bar.addMenu("❓ " + LOCALE[self.current_lang]["help"])
        
        self.act_auto_upd = QAction("⚙️ " + LOCALE[self.current_lang]["auto_update"], self, checkable=True)
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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.open_tbl(files[0])

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
                    btn_yes = QPushButton("Yes")
                    btn_yes.clicked.connect(lambda: [webbrowser.open(data["html_url"]), dlg.accept()])
                    btn_no = QPushButton("No")
                    btn_no.clicked.connect(dlg.reject)
                    btn_box.addWidget(btn_yes)
                    btn_box.addWidget(btn_no)
                    layout.addLayout(btn_box)
                    
                    dlg.exec()
                else:
                    if not silent:
                        QMessageBox.information(self, "Info", LOCALE[self.current_lang]["no_update"])
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, LOCALE[self.current_lang]["update_err"], f"{str(e)}")

    # ========== ROM TOOLS ==========
    
    def open_rom(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open ROM", "", "ROM Files (*.nes *.sfc *.smc *.gb *.gbc *.gba *.bin);;All Files (*.*)")
        if fname:
            with open(fname, "rb") as f:
                self.rom_data = f.read()
            QMessageBox.information(self, "ROM Loaded", f"Loaded {len(self.rom_data)} bytes from {os.path.basename(fname)}")
    
    def search_in_rom(self):
        if not self.rom_data:
            QMessageBox.warning(self, "Warning", "Load a ROM first!")
            return
            
        tab = self.tabs.currentWidget()
        if not tab: return
        
        dlg = RomSearchDialog(self.rom_data, tab.table_manager.hex_map, self)
        dlg.exec()
        
    def export_script(self):
        if not self.rom_data:
            QMessageBox.warning(self, "Warning", "Load a ROM first!")
            return
            
        tab = self.tabs.currentWidget()
        if not tab: return

        fname, _ = QFileDialog.getSaveFileName(self, "Export Script", "", "Text Files (*.txt)")
        if not fname:
            return
            
        # Simple export: find all sequences that decode to printable text
        # This is a basic implementation - can be enhanced
        try:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(f"# Script exported from ROM ({len(self.rom_data)} bytes)\n")
                f.write(f"# Table: {len(tab.table_manager.entries)} entries\n\n")
                
                # Find strings by scanning for printable sequences
                addr = 0
                while addr < len(self.rom_data):
                    # Try to decode starting at this address
                    result, length = self._decode_at_offset(addr, tab.table_manager, min_length=4)
                    if result and len(result) >= 4:
                        f.write(f"{addr:08X}={result}\n")
                        addr += length
                    else:
                        addr += 1
                        
            QMessageBox.information(self, "Success", f"Script exported to {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def _decode_at_offset(self, offset, table_manager, min_length=4, max_length=256):
        """Decode text at a ROM offset using the current table"""
        result = ""
        length = 0
        idx = offset
        
        while idx < len(self.rom_data) and length < max_length:
            matched = False
            # Try longest match first
            for code_len in range(4, 0, -1):
                if idx + code_len <= len(self.rom_data):
                    code = self.rom_data[idx:idx+code_len].hex().upper()
                    if code in table_manager.hex_map:
                        char = table_manager.hex_map[code]
                        if char == "<END>" or char == "<LF>":
                            if len(result) >= min_length:
                                return result, length
                            else:
                                return None, 0
                        result += char
                        length += code_len
                        idx += code_len
                        matched = True
                        break
            if not matched:
                break
                
        if len(result) >= min_length:
            return result, length
        return None, 0
        
    def import_script(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Import Script", "", "Text Files (*.txt)")
        if not fname:
            return
            
        try:
            with open(fname, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Parse format: OFFSET=TEXT
            entries_imported = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        # For now, just log - actual patching would modify ROM
                        entries_imported += 1
                        
            QMessageBox.information(self, "Import Complete", f"Parsed {entries_imported} script entries.\n(ROM patching not implemented yet)")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def auto_detect_encoding(self):
        if not self.rom_data:
            QMessageBox.warning(self, "Warning", "Load a ROM first!")
            return
            
        # Sample first 4KB of ROM
        sample = self.rom_data[:4096]
        
        # Check for common patterns
        ascii_count = sum(1 for b in sample if 0x20 <= b <= 0x7E)
        sjis_pairs = 0
        
        # Simple heuristic
        ascii_ratio = ascii_count / len(sample)
        
        detected = "Unknown"
        if ascii_ratio > 0.5:
            detected = "ASCII / Latin-1"
        elif ascii_ratio > 0.3:
            detected = "Shift-JIS (possible)"
        else:
            detected = "Custom/Compressed"
            
        QMessageBox.information(self, "Encoding Detection", f"Detected: {detected}\nASCII ratio: {ascii_ratio:.1%}")
        
    def open_in_hex_editor(self, offset):
        """Open Hex Editor at specified offset"""
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        hex_editor = os.path.join(script_dir, "stormhexeditor.py")
        
        # We can't pass offset directly, but we can open the file
        # For now, just launch the editor
        try:
            subprocess.Popen([sys.executable, hex_editor])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not launch Hex Editor: {e}")

# ROM Search Dialog
class RomSearchDialog(QDialog):
    def __init__(self, rom_data, hex_map, parent=None):
        super().__init__(parent)
        self.rom_data = rom_data
        self.hex_map = hex_map
        self.setWindowTitle("Search in ROM")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Search input
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text or hex (e.g. 'GAME' or '47414D45')")
        search_layout.addWidget(self.search_input)
        
        self.btn_search = QPushButton("🔍 Search")
        self.btn_search.clicked.connect(self.do_search)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)
        
        # Results
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Offset", "Hex", "Text"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.doubleClicked.connect(self.on_double_click)
        layout.addWidget(self.results_table)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
    def do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.results_table.setRowCount(0)
        
        # Determine if hex or text search
        if all(c in "0123456789ABCDEFabcdef" for c in query) and len(query) % 2 == 0:
            # Hex search
            search_bytes = bytes.fromhex(query)
        else:
            # Text search - convert to ASCII
            search_bytes = query.encode("latin-1", errors="ignore")
            
        # Find all occurrences
        results = []
        offset = 0
        while offset < len(self.rom_data):
            pos = self.rom_data.find(search_bytes, offset)
            if pos == -1:
                break
            
            # Get context
            context_hex = self.rom_data[pos:pos+16].hex().upper()
            context_text = ''.join(chr(b) if 0x20 <= b <= 0x7E else '.' for b in self.rom_data[pos:pos+16])
            
            results.append((pos, context_hex, context_text))
            offset = pos + 1
            
        # Display results
        self.results_table.setRowCount(len(results))
        for row, (off, hex_ctx, text_ctx) in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(f"0x{off:08X}"))
            self.results_table.setItem(row, 1, QTableWidgetItem(hex_ctx))
            self.results_table.setItem(row, 2, QTableWidgetItem(text_ctx))
            
        self.status_label.setText(f"Found {len(results)} matches")
        
    def on_double_click(self, index):
        row = index.row()
        offset_str = self.results_table.item(row, 0).text()
        offset = int(offset_str, 16)
        
        # Try to open in Hex Editor
        if hasattr(self.parent(), 'open_in_hex_editor'):
            self.parent().open_in_hex_editor(offset)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
