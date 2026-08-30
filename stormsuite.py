
import sys
import subprocess
import os
import json
import urllib.request
import urllib.error
from PyQt6.QtWidgets import (QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QFrame, QGridLayout, QMessageBox,
                             QProgressDialog)
from PyQt6.QtCore import Qt, QSize, QSettings, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QPixmap

from stormbase import LOCALE, THEMES, resource_path, APP_NAME, CURRENT_VERSION, APP_REPOS, show_about_dialog

# Map app keys to expected EXE names
APP_EXES = {
    "hex_editor": "STORM HEX EDITOR.exe",
    "tile_manager": "STORM TILE MANAGER.exe",
    "game_dict": "STORM GAME DICTIONARY.exe"
}

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str) # success, message (or path)

    def __init__(self, repo, target_name):
        super().__init__()
        self.repo = repo
        self.target_name = target_name

    def run(self):
        try:
            # 1. Get latest release info
            api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"
            # GitHub requires User-Agent
            req = urllib.request.Request(api_url, headers={'User-Agent': "StormSuite-Launcher"})
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
            
            # 2. Find asset
            asset = None
            # Prefer asset with exact name, or any .exe
            for a in data.get("assets", []):
                # Simple heuristic: if target_name matches or it's the only exe
                if a["name"].lower() == self.target_name.lower():
                    asset = a
                    break
                if a["name"].lower().endswith(".exe"):
                    # Fallback or if name differs slightly
                    asset = a
            
            if not asset:
                self.finished.emit(False, "No suitable EXE found in latest release.")
                return

            download_url = asset["browser_download_url"]
            filename = asset["name"] # Use the actual asset name from GitHub
            
            # 3. Download
            req_dl = urllib.request.Request(download_url, headers={'User-Agent': "StormSuite-Launcher"})
            with urllib.request.urlopen(req_dl) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(filename, "wb") as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.progress.emit(percent)
                            
            self.finished.emit(True, filename)
            
        except Exception as e:
            self.finished.emit(False, str(e))

class LauncherButton(QPushButton):
    def __init__(self, title, icon_name, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border: 2px solid #555555;
                border-radius: 10px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444444;
                border-color: #007acc;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Icon
        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Placeholder icon if file doesn't exist
        pixmap = QPixmap(resource_path(icon_name))
        if pixmap.isNull():
             # Create simple colored box
             pixmap = QPixmap(64, 64)
             pixmap.fill(Qt.GlobalColor.gray)
        else:
             pixmap = pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
             
        lbl_icon.setPixmap(pixmap)
        layout.addWidget(lbl_icon)
        
        # Title
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(lbl_title)

class LauncherDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{CURRENT_VERSION}")
        self.resize(800, 500)
        self.setWindowIcon(QIcon(resource_path("stormsuite.ico")))
        
        # Settings
        self.settings = QSettings("StormSuite", "Launcher")
        self.current_lang = "ru" # Default
        self.active_processes = []
        
        # Theme
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-family: 'Segoe UI';")
        
        # Supervisor Timer
        self.supervisor_timer = QTimer(self)
        self.supervisor_timer.timeout.connect(self.check_supervisor)
        self.supervisor_timer.start(1000)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header
        lbl_header = QLabel(APP_NAME)
        lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_header.setStyleSheet("font-size: 32px; font-weight: bold; color: #007acc; margin-bottom: 20px;")
        layout.addWidget(lbl_header)
        
        # App Grid
        grid = QGridLayout()
        grid.setSpacing(30)
        
        # 1. Hex Editor
        self.btn_hex = LauncherButton(LOCALE[self.current_lang]["hex_editor"], "stormhexeditor.ico")
        self.btn_hex.clicked.connect(lambda: self.launch("hex_editor"))
        grid.addWidget(self.btn_hex, 0, 0)
        
        # 2. Tile Manager
        self.btn_tile = LauncherButton(LOCALE[self.current_lang]["tile_manager"], "stormtilemanager.ico")
        self.btn_tile.clicked.connect(lambda: self.launch("tile_manager"))
        grid.addWidget(self.btn_tile, 0, 1)
        
        # 3. Game Dictionary
        self.btn_dict = LauncherButton(LOCALE[self.current_lang]["game_dict"], "stormgamedictionary.ico")
        self.btn_dict.clicked.connect(lambda: self.launch("game_dict"))
        grid.addWidget(self.btn_dict, 0, 2)
        
        layout.addLayout(grid)
        
        # Footer Options
        footer = QHBoxLayout()
        
        btn_about = QPushButton("ℹ️")
        btn_about.setFixedSize(40, 40)
        btn_about.setStyleSheet("background-color: #333333; color: white; border-radius: 5px; font-size: 20px;")
        btn_about.clicked.connect(lambda: show_about_dialog(self, "suite"))
        footer.addWidget(btn_about)
        
        self.chk_multi = QCheckBox(LOCALE[self.current_lang]["multi_proc"])
        self.chk_multi.setStyleSheet("""
            QCheckBox { font-size: 14px; color: white; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:checked { background-color: #2ecc71; border: 1px solid #27ae60; }
            QCheckBox::indicator:unchecked { background-color: #333333; border: 1px solid #555555; }
        """)
        self.chk_multi.setChecked(self.settings.value("multi_proc", False, type=bool))
        footer.addWidget(self.chk_multi)

        self.chk_super = QCheckBox(LOCALE[self.current_lang]["supervisor"])
        self.chk_super.setStyleSheet("""
            QCheckBox { font-size: 14px; color: white; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:checked { background-color: #2ecc71; border: 1px solid #27ae60; }
            QCheckBox::indicator:unchecked { background-color: #333333; border: 1px solid #555555; }
        """)
        self.chk_super.setChecked(self.settings.value("supervisor", True, type=bool))
        footer.addWidget(self.chk_super)
        
        footer.addStretch()
        
        btn_exit = QPushButton(LOCALE[self.current_lang]["exit"])
        btn_exit.setFixedSize(100, 40)
        btn_exit.setStyleSheet("""
            background-color: #cc0000; color: white; border-radius: 5px; font-weight: bold;
        """)
        btn_exit.clicked.connect(self.close)
        footer.addWidget(btn_exit)
        
        layout.addLayout(footer)
        
    def launch(self, app_key):
        # Save settings
        self.settings.setValue("multi_proc", self.chk_multi.isChecked())
        self.settings.setValue("supervisor", self.chk_super.isChecked())
        
        target_exe = APP_EXES.get(app_key)
        if not target_exe: return

        # IMPORTANT: When running as frozen exe, we need to look in the folder 
        # where the exe is, NOT where the temp folder (_MEI) is.
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        exe_path = os.path.join(base_dir, target_exe)
        
        if os.path.exists(exe_path):
            self.run_exe(exe_path)
        else:
            self.download_app(app_key, target_exe)

    def download_app(self, app_key, target_name):
        repo = APP_REPOS.get(app_key)
        if not repo: return
        
        msg = QMessageBox(self)
        msg.setWindowTitle(LOCALE[self.current_lang]["info"])
        # "{} not found.\nDownload from GitHub?"
        msg.setText(LOCALE[self.current_lang]["download_ask"].format(target_name))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        # Localize buttons attempt? Standard buttons follow system locale mostly, 
        # but we can try to set text if needed, but PyQt usually handles standard buttons well enough.
        
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Progress Dialog using localized "Downloading..."
        self.pd = QProgressDialog(LOCALE[self.current_lang]["downloading"], 
                                  LOCALE[self.current_lang].get("cancel", "Cancel"), 0, 100, self)
        self.pd.setWindowModality(Qt.WindowModality.WindowModal)
        self.pd.show()
        
        self.downloader = DownloadThread(repo, target_name)
        self.downloader.progress.connect(self.pd.setValue)
        self.downloader.finished.connect(lambda s, m: self.on_download_finished(s, m, app_key))
        self.downloader.start()

    def on_download_finished(self, success, result, app_key):
        self.pd.close()
        if success:
            QMessageBox.information(self, LOCALE[self.current_lang]["success"], 
                                    LOCALE[self.current_lang]["download_success"].format(result))
            
            # Recalculate path to launch
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(base_dir, result)
            
            self.run_exe(exe_path)
        else:
            QMessageBox.critical(self, LOCALE[self.current_lang]["error"], 
                                 LOCALE[self.current_lang]["download_fail"].format(result))

    def run_exe(self, exe_path):
        try:
            proc = subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            self.active_processes.append(proc)
            
            if self.chk_super.isChecked():
                self.hide()
            elif not self.chk_multi.isChecked():
                self.close()
        except Exception as e:
            QMessageBox.critical(self, LOCALE[self.current_lang]["error"], 
                                 f"{LOCALE[self.current_lang]['launch_err']} {e}")

    def check_supervisor(self):
        # Remove finished processes
        self.active_processes = [p for p in self.active_processes if p.poll() is None]
        
        if not self.active_processes and self.chk_super.isChecked() and self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = LauncherDialog()
    launcher.show()
    sys.exit(app.exec())
