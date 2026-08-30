
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QDialog, 
                             QPushButton, QLabel, QHBoxLayout, QGridLayout, QMessageBox,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPalette, QPixmap

# --- CONSTANTS ---
APP_NAME = "STORM SUITE"
CURRENT_VERSION = "2.2.0"
AUTHOR = "ReiKatari"
YEAR = "2026"

APP_REPOS = {
    "suite": "ReiKatari/STORM_SUITE",
    "hex_editor": "ReiKatari/STORM_HEX_EDITOR",
    "tile_manager": "ReiKatari/STORM_TILE_MANAGER",
    "game_dict": "ReiKatari/STORM_GAME_DICTIONARY"
}

APP_ICONS = {
    "suite": "stormsuite.ico",
    "hex_editor": "stormhexeditor.ico",
    "tile_manager": "stormtilemanager.ico",
    "game_dict": "stormgamedictionary.ico"
}

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def show_about_dialog(parent, app_key):
    """Show standardized About dialog"""
    app_titles = {
        "suite": "STORM SUITE",
        "hex_editor": "STORM HEX EDITOR",
        "tile_manager": "STORM TILE MANAGER",
        "game_dict": "STORM GAME DICTIONARY"
    }
    
    title = app_titles.get(app_key, APP_NAME)
    repo = APP_REPOS.get(app_key, APP_REPOS["suite"])
    url = f"https://github.com/{repo}"
    
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    
    # Modern vertical layout via rich text
    text = (
        f"<div style='text-align: center;'>"
        f"<h2 style='margin-bottom: 5px; color: #569cd6;'>{title}</h2>"
        f"<p style='margin: 0; font-weight: bold;'>v{CURRENT_VERSION}</p><br>"
        f"<p style='margin: 0;'>(c) {YEAR} {AUTHOR}</p><br>"
        f"<a href='{url}' style='color: #ce9178; text-decoration: none;'>GitHub Repository</a>"
        f"</div>"
    )
    
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()

# --- THEMES ---
THEMES = {
    # --- DARK THEMES ---
    "Dark (Default)": {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "offset_fg": "#569cd6", 
        "hex_fg": "#ce9178", "ascii_fg": "#9cdcfe", "sel_bg": "#264f78", "sel_fg": "#ffffff",
        "menu_bg": "#2d2d2d", "menu_fg": "#cccccc", "alt_bg": "#252526",
        "input_bg": "#252526", "input_fg": "#e0e0e0", "input_border": "#3e3e42",
        "btn_bg": "#333333", "btn_fg": "#ffffff", "btn_hover": "#444444",
        "highlight": "#007acc", "highlight_text": "#ffffff", "tree_bg": "#252526", "tree_alt": "#2d2d30"
    },
    "Storm Dark": {
        "bg": "#121212", "fg": "#e0e0e0", "offset_fg": "#bb86fc", 
        "hex_fg": "#03dac6", "ascii_fg": "#cf6679", "sel_bg": "#3700b3", "sel_fg": "#ffffff",
        "menu_bg": "#1f1f1f", "menu_fg": "#ffffff", "alt_bg": "#1a1a1a",
        "input_bg": "#1e1e1e", "input_fg": "#e0e0e0", "input_border": "#333333",
        "btn_bg": "#2c2c2c", "btn_fg": "#e0e0e0", "btn_hover": "#3c3c3c",
        "highlight": "#bb86fc", "highlight_text": "#000000", "tree_bg": "#121212", "tree_alt": "#1a1a1a"
    },
    "Monokai": {
        "bg": "#272822", "fg": "#f8f8f2", "offset_fg": "#75715e", 
        "hex_fg": "#a6e22e", "ascii_fg": "#e6db74", "sel_bg": "#49483e", "sel_fg": "#f8f8f2",
        "menu_bg": "#272822", "menu_fg": "#f8f8f2", "alt_bg": "#3e3d32",
        "input_bg": "#3e3d32", "input_fg": "#f8f8f2", "input_border": "#75715e",
        "btn_bg": "#3e3d32", "btn_fg": "#f8f8f2", "btn_hover": "#49483e",
        "highlight": "#f92672", "highlight_text": "#f8f8f2", "tree_bg": "#272822", "tree_alt": "#3e3d32"
    },
    "Dracula": {
        "bg": "#282a36", "fg": "#f8f8f2", "offset_fg": "#6272a4", 
        "hex_fg": "#ff79c6", "ascii_fg": "#8be9fd", "sel_bg": "#44475a", "sel_fg": "#f8f8f2",
        "menu_bg": "#282a36", "menu_fg": "#f8f8f2", "alt_bg": "#21222c",
        "input_bg": "#44475a", "input_fg": "#f8f8f2", "input_border": "#6272a4",
        "btn_bg": "#44475a", "btn_fg": "#f8f8f2", "btn_hover": "#6272a4",
        "highlight": "#bd93f9", "highlight_text": "#282a36", "tree_bg": "#282a36", "tree_alt": "#21222c"
    },
    "Nord": {
        "bg": "#2e3440", "fg": "#d8dee9", "offset_fg": "#4c566a", 
        "hex_fg": "#88c0d0", "ascii_fg": "#ebcb8b", "sel_bg": "#434c5e", "sel_fg": "#eceff4",
        "menu_bg": "#2e3440", "menu_fg": "#d8dee9", "alt_bg": "#3b4252",
        "input_bg": "#3b4252", "input_fg": "#d8dee9", "input_border": "#4c566a",
        "btn_bg": "#434c5e", "btn_fg": "#d8dee9", "btn_hover": "#4c566a",
        "highlight": "#88c0d0", "highlight_text": "#2e3440", "tree_bg": "#2e3440", "tree_alt": "#3b4252"
    },
    "Cyberpunk": {
        "bg": "#020202", "fg": "#00ff00", "offset_fg": "#ff00ff",
        "hex_fg": "#00ffff", "ascii_fg": "#ffff00", "sel_bg": "#ff0055", "sel_fg": "#ffffff",
        "menu_bg": "#101010", "menu_fg": "#00ff00", "alt_bg": "#050505",
        "input_bg": "#000000", "input_fg": "#00ff00", "input_border": "#00ff00",
        "btn_bg": "#000000", "btn_fg": "#00ffff", "btn_hover": "#101010",
        "highlight": "#ff0055", "highlight_text": "#ffffff", "tree_bg": "#020202", "tree_alt": "#050505"
    },
    "Synthwave": {
        "bg": "#2b213a", "fg": "#fff1f3", "offset_fg": "#5f4b8b",
        "hex_fg": "#ff2a6d", "ascii_fg": "#05d9e8", "sel_bg": "#d1f7ff", "sel_fg": "#01012b",
        "menu_bg": "#2b213a", "menu_fg": "#fff1f3", "alt_bg": "#241b30",
        "input_bg": "#241b30", "input_fg": "#05d9e8", "input_border": "#ff2a6d",
        "btn_bg": "#4c1a57", "btn_fg": "#fff1f3", "btn_hover": "#5f4b8b",
        "highlight": "#ff2a6d", "highlight_text": "#ffffff", "tree_bg": "#2b213a", "tree_alt": "#241b30"
    },
    "Deep Ocean": {
        "bg": "#0f111a", "fg": "#8f93a2", "offset_fg": "#4b526d",
        "hex_fg": "#c3e88d", "ascii_fg": "#82aaff", "sel_bg": "#1d202f", "sel_fg": "#ffffff",
        "menu_bg": "#0f111a", "menu_fg": "#8f93a2", "alt_bg": "#090b10",
        "input_bg": "#090b10", "input_fg": "#8f93a2", "input_border": "#4b526d",
        "btn_bg": "#1a1c29", "btn_fg": "#8f93a2", "btn_hover": "#292d3e",
        "highlight": "#82aaff", "highlight_text": "#0f111a", "tree_bg": "#0f111a", "tree_alt": "#090b10"
    },
    "Matrix": {
        "bg": "#000000", "fg": "#00ff00", "offset_fg": "#003300",
        "hex_fg": "#00cc00", "ascii_fg": "#00ff00", "sel_bg": "#004400", "sel_fg": "#ffffff",
        "menu_bg": "#000000", "menu_fg": "#00ff00", "alt_bg": "#0a0a0a",
        "input_bg": "#001100", "input_fg": "#00ff00", "input_border": "#003300",
        "btn_bg": "#002200", "btn_fg": "#00ff00", "btn_hover": "#003300",
        "highlight": "#00ff00", "highlight_text": "#000000", "tree_bg": "#000000", "tree_alt": "#0a0a0a"
    },
    "Gruvbox Dark": {
        "bg": "#282828", "fg": "#ebdbb2", "offset_fg": "#928374",
        "hex_fg": "#fb4934", "ascii_fg": "#b8bb26", "sel_bg": "#504945", "sel_fg": "#ebdbb2",
        "menu_bg": "#282828", "menu_fg": "#ebdbb2", "alt_bg": "#3c3836",
        "input_bg": "#3c3836", "input_fg": "#ebdbb2", "input_border": "#928374",
        "btn_bg": "#504945", "btn_fg": "#ebdbb2", "btn_hover": "#665c54",
        "highlight": "#fabd2f", "highlight_text": "#282828", "tree_bg": "#282828", "tree_alt": "#3c3836"
    },
    "One Dark": {
        "bg": "#282c34", "fg": "#abb2bf", "offset_fg": "#5c6370",
        "hex_fg": "#e06c75", "ascii_fg": "#98c379", "sel_bg": "#3e4452", "sel_fg": "#abb2bf",
        "menu_bg": "#282c34", "menu_fg": "#abb2bf", "alt_bg": "#21252b",
        "input_bg": "#21252b", "input_fg": "#abb2bf", "input_border": "#5c6370",
        "btn_bg": "#3b4048", "btn_fg": "#abb2bf", "btn_hover": "#4b5263",
        "highlight": "#61afef", "highlight_text": "#282c34", "tree_bg": "#282c34", "tree_alt": "#21252b"
    },
    "Palenight": {
        "bg": "#292d3e", "fg": "#a6accd", "offset_fg": "#676e95",
        "hex_fg": "#f07178", "ascii_fg": "#c3e88d", "sel_bg": "#444267", "sel_fg": "#ffffff",
        "menu_bg": "#292d3e", "menu_fg": "#a6accd", "alt_bg": "#202331",
        "input_bg": "#202331", "input_fg": "#a6accd", "input_border": "#676e95",
        "btn_bg": "#444267", "btn_fg": "#ffffff", "btn_hover": "#32374d",
        "highlight": "#89ddff", "highlight_text": "#292d3e", "tree_bg": "#292d3e", "tree_alt": "#202331"
    },
    "Cobalt2": {
        "bg": "#193549", "fg": "#e1efff", "offset_fg": "#0088ff",
        "hex_fg": "#ffc600", "ascii_fg": "#3ad900", "sel_bg": "#0d3a58", "sel_fg": "#ffffff",
        "menu_bg": "#193549", "menu_fg": "#e1efff", "alt_bg": "#15232d",
        "input_bg": "#15232d", "input_fg": "#e1efff", "input_border": "#0088ff",
        "btn_bg": "#1f4662", "btn_fg": "#e1efff", "btn_hover": "#193549",
        "highlight": "#ffc600", "highlight_text": "#193549", "tree_bg": "#193549", "tree_alt": "#15232d"
    },
    "Night Owl": {
        "bg": "#011627", "fg": "#d6deeb", "offset_fg": "#5f7e97",
        "hex_fg": "#82aaff", "ascii_fg": "#c5e478", "sel_bg": "#1d3b53", "sel_fg": "#ffffff",
        "menu_bg": "#011627", "menu_fg": "#d6deeb", "alt_bg": "#0b2942",
        "input_bg": "#0b2942", "input_fg": "#d6deeb", "input_border": "#5f7e97",
        "btn_bg": "#7e57c2", "btn_fg": "#ffffff", "btn_hover": "#5f7e97",
        "highlight": "#addb67", "highlight_text": "#011627", "tree_bg": "#011627", "tree_alt": "#0b2942"
    },
    "Tokyo Night": {
        "bg": "#1a1b26", "fg": "#a9b1d6", "offset_fg": "#565f89",
        "hex_fg": "#f7768e", "ascii_fg": "#7aa2f7", "sel_bg": "#283457", "sel_fg": "#c0caf5",
        "menu_bg": "#1a1b26", "menu_fg": "#a9b1d6", "alt_bg": "#16161e",
        "input_bg": "#16161e", "input_fg": "#a9b1d6", "input_border": "#565f89",
        "btn_bg": "#24283b", "btn_fg": "#a9b1d6", "btn_hover": "#414868",
        "highlight": "#bb9af7", "highlight_text": "#1a1b26", "tree_bg": "#1a1b26", "tree_alt": "#16161e"
    },
    "Twilight": {
        "bg": "#141414", "fg": "#f8f8f8", "offset_fg": "#5f5a60",
        "hex_fg": "#cf6a4c", "ascii_fg": "#8f9d6a", "sel_bg": "#3f3f3f", "sel_fg": "#f8f8f8",
        "menu_bg": "#141414", "menu_fg": "#f8f8f8", "alt_bg": "#1e1e1e",
        "input_bg": "#1e1e1e", "input_fg": "#f8f8f8", "input_border": "#5f5a60",
        "btn_bg": "#3f3f3f", "btn_fg": "#f8f8f8", "btn_hover": "#4f4f4f",
        "highlight": "#ac885b", "highlight_text": "#141414", "tree_bg": "#141414", "tree_alt": "#1e1e1e"
    },
    "Red": {
        "bg": "#200000", "fg": "#ffcccc", "offset_fg": "#660000",
        "hex_fg": "#ff0000", "ascii_fg": "#ff6666", "sel_bg": "#440000", "sel_fg": "#ffffff",
        "menu_bg": "#200000", "menu_fg": "#ffcccc", "alt_bg": "#330000",
        "input_bg": "#330000", "input_fg": "#ffcccc", "input_border": "#660000",
        "btn_bg": "#440000", "btn_fg": "#ffffff", "btn_hover": "#660000",
        "highlight": "#ff0000", "highlight_text": "#000000", "tree_bg": "#200000", "tree_alt": "#330000"
    },
    "Green": {
        "bg": "#002000", "fg": "#ccffcc", "offset_fg": "#006600",
        "hex_fg": "#00ff00", "ascii_fg": "#66ff66", "sel_bg": "#004400", "sel_fg": "#ffffff",
        "menu_bg": "#002000", "menu_fg": "#ccffcc", "alt_bg": "#003300",
        "input_bg": "#003300", "input_fg": "#ccffcc", "input_border": "#006600",
        "btn_bg": "#004400", "btn_fg": "#ffffff", "btn_hover": "#006600",
        "highlight": "#00ff00", "highlight_text": "#000000", "tree_bg": "#002000", "tree_alt": "#003300"
    },
    "Blue": {
        "bg": "#000020", "fg": "#ccccff", "offset_fg": "#000066",
        "hex_fg": "#0000ff", "ascii_fg": "#6666ff", "sel_bg": "#000044", "sel_fg": "#ffffff",
        "menu_bg": "#000020", "menu_fg": "#ccccff", "alt_bg": "#000033",
        "input_bg": "#000033", "input_fg": "#ccccff", "input_border": "#000066",
        "btn_bg": "#000044", "btn_fg": "#ffffff", "btn_hover": "#000066",
        "highlight": "#0000ff", "highlight_text": "#ffffff", "tree_bg": "#000020", "tree_alt": "#000033"
    },
    "Purple": {
        "bg": "#1a001a", "fg": "#e6ccff", "offset_fg": "#4d004d",
        "hex_fg": "#9933ff", "ascii_fg": "#d24dff", "sel_bg": "#330033", "sel_fg": "#ffffff",
        "menu_bg": "#1a001a", "menu_fg": "#e6ccff", "alt_bg": "#260026",
        "input_bg": "#260026", "input_fg": "#e6ccff", "input_border": "#4d004d",
        "btn_bg": "#330033", "btn_fg": "#ffffff", "btn_hover": "#4d004d",
        "highlight": "#9933ff", "highlight_text": "#ffffff", "tree_bg": "#1a001a", "tree_alt": "#260026"
    },
    "Orange": {
        "bg": "#201000", "fg": "#ffcc99", "offset_fg": "#663300",
        "hex_fg": "#ff6600", "ascii_fg": "#ff9933", "sel_bg": "#442200", "sel_fg": "#ffffff",
        "menu_bg": "#201000", "menu_fg": "#ffcc99", "alt_bg": "#331a00",
        "input_bg": "#331a00", "input_fg": "#ffcc99", "input_border": "#663300",
        "btn_bg": "#442200", "btn_fg": "#ffffff", "btn_hover": "#663300",
        "highlight": "#ff6600", "highlight_text": "#000000", "tree_bg": "#201000", "tree_alt": "#331a00"
    },
    "High Contrast Dark": {
        "bg": "#000000", "fg": "#ffffff", "offset_fg": "#888888",
        "hex_fg": "#ffff00", "ascii_fg": "#00ffff", "sel_bg": "#ffffff", "sel_fg": "#000000",
        "menu_bg": "#000000", "menu_fg": "#ffffff", "alt_bg": "#222222",
        "input_bg": "#000000", "input_fg": "#ffffff", "input_border": "#ffffff",
        "btn_bg": "#333333", "btn_fg": "#ffffff", "btn_hover": "#555555",
        "highlight": "#ffff00", "highlight_text": "#000000", "tree_bg": "#000000", "tree_alt": "#222222"
    },
    "Ubuntu": {
        "bg": "#300a24", "fg": "#ffffff", "offset_fg": "#77216f",
        "hex_fg": "#e95420", "ascii_fg": "#aea79f", "sel_bg": "#dd4814", "sel_fg": "#ffffff",
        "menu_bg": "#300a24", "menu_fg": "#ffffff", "alt_bg": "#2c001e",
        "input_bg": "#2c001e", "input_fg": "#ffffff", "input_border": "#77216f",
        "btn_bg": "#dd4814", "btn_fg": "#ffffff", "btn_hover": "#e95420",
        "highlight": "#e95420", "highlight_text": "#ffffff", "tree_bg": "#300a24", "tree_alt": "#2c001e"
    },
    "Zenburn": {
        "bg": "#3f3f3f", "fg": "#dcdccc", "offset_fg": "#709080",
        "hex_fg": "#cc9393", "ascii_fg": "#8cd0d3", "sel_bg": "#4f4f4f", "sel_fg": "#f0dfaf",
        "menu_bg": "#3f3f3f", "menu_fg": "#dcdccc", "alt_bg": "#484848",
        "input_bg": "#484848", "input_fg": "#dcdccc", "input_border": "#709080",
        "btn_bg": "#4f4f4f", "btn_fg": "#f0dfaf", "btn_hover": "#5f5f5f",
        "highlight": "#cc9393", "highlight_text": "#3f3f3f", "tree_bg": "#3f3f3f", "tree_alt": "#484848"
    },
    "SpaceGray": {
        "bg": "#343d46", "fg": "#c0c5ce", "offset_fg": "#65737e",
        "hex_fg": "#bf616a", "ascii_fg": "#a3be8c", "sel_bg": "#4f5b66", "sel_fg": "#eff1f5",
        "menu_bg": "#343d46", "menu_fg": "#c0c5ce", "alt_bg": "#2b3038",
        "input_bg": "#2b3038", "input_fg": "#c0c5ce", "input_border": "#65737e",
        "btn_bg": "#4f5b66", "btn_fg": "#eff1f5", "btn_hover": "#65737e",
        "highlight": "#bf616a", "highlight_text": "#343d46", "tree_bg": "#343d46", "tree_alt": "#2b3038"
    },

    # --- LIGHT THEMES ---
    "Light": {
        "bg": "#ffffff", "fg": "#000000", "offset_fg": "#0000ff", 
        "hex_fg": "#008000", "ascii_fg": "#a31515", "sel_bg": "#add8e6", "sel_fg": "#000000",
        "menu_bg": "#f0f0f0", "menu_fg": "#000000", "alt_bg": "#f5f5f5",
        "input_bg": "#ffffff", "input_fg": "#000000", "input_border": "#cccccc",
        "btn_bg": "#e0e0e0", "btn_fg": "#000000", "btn_hover": "#d0d0d0",
        "highlight": "#0078d7", "highlight_text": "#ffffff", "tree_bg": "#ffffff", "tree_alt": "#f5f5f5"
    },
    "Solarized Light": {
        "bg": "#fdf6e3", "fg": "#657b83", "offset_fg": "#93a1a1",
        "hex_fg": "#2aa198", "ascii_fg": "#b58900", "sel_bg": "#eee8d5", "sel_fg": "#586e75",
        "menu_bg": "#fdf6e3", "menu_fg": "#657b83", "alt_bg": "#eee8d5",
        "input_bg": "#eee8d5", "input_fg": "#657b83", "input_border": "#93a1a1",
        "btn_bg": "#eee8d5", "btn_fg": "#586e75", "btn_hover": "#93a1a1",
        "highlight": "#2aa198", "highlight_text": "#fdf6e3", "tree_bg": "#fdf6e3", "tree_alt": "#eee8d5"
    },
    "GitHub Light": {
        "bg": "#ffffff", "fg": "#24292e", "offset_fg": "#0366d6",
        "hex_fg": "#d73a49", "ascii_fg": "#005cc5", "sel_bg": "#c8c8fa", "sel_fg": "#24292e",
        "menu_bg": "#f6f8fa", "menu_fg": "#24292e", "alt_bg": "#f1f8ff",
        "input_bg": "#ffffff", "input_fg": "#24292e", "input_border": "#d1d5da",
        "btn_bg": "#eff3f6", "btn_fg": "#24292e", "btn_hover": "#e1e4e8",
        "highlight": "#0366d6", "highlight_text": "#ffffff", "tree_bg": "#ffffff", "tree_alt": "#f1f8ff"
    },
    "Xcode": {
        "bg": "#292A30", "fg": "#FFFFFF", "offset_fg": "#00A2FF",
        "hex_fg": "#FF3B30", "ascii_fg": "#4CD964", "sel_bg": "#585858", "sel_fg": "#FFFFFF",
        "menu_bg": "#292A30", "menu_fg": "#FFFFFF", "alt_bg": "#333333",
        "input_bg": "#292A30", "input_fg": "#FFFFFF", "input_border": "#00A2FF",
        "btn_bg": "#585858", "btn_fg": "#FFFFFF", "btn_hover": "#00A2FF",
        "highlight": "#00A2FF", "highlight_text": "#FFFFFF", "tree_bg": "#292A30", "tree_alt": "#333333"
    },
    
    # --- ULTRA THEMES ---
    "Neon City": {
        "bg": "#0b0c15", "fg": "#00f3ff", "offset_fg": "#ff00ff",
        "hex_fg": "#bd00ff", "ascii_fg": "#00f3ff", "sel_bg": "#1f2639", "sel_fg": "#ffffff",
        "menu_bg": "#090a11", "menu_fg": "#00f3ff", "alt_bg": "#121420",
        "input_bg": "#121420", "input_fg": "#00f3ff", "input_border": "#ff00ff",
        "btn_bg": "#1f2639", "btn_fg": "#00f3ff", "btn_hover": "#2a3459",
        "highlight": "#ff00ff", "highlight_text": "#0b0c15", "tree_bg": "#0b0c15", "tree_alt": "#121420"
    }
}

# --- LOCALIZATION ---
LOCALE = {
    "ru": {
        "file": "Файл", "open": "Открыть", "save": "Сохранить", "save_as": "Сохранить как", "close": "Закрыть файл", "exit": "Выход",
        "edit": "Правка", "undo": "Отменить", "redo": "Повторить", "cut": "Вырезать", "copy": "Копировать", "paste": "Вставить",
        "find": "Найти", "goto": "Перейти", "select_all": "Выделить всё", "hex": "Hex", "text": "Текст", "search": "Поиск",
        "ready": "Готов", "processing": "Обработка...", "search_res": "Результаты поиска", "not_found": "Не найдено",
        "update_avail": "Доступно обновление!", "no_update": "У вас последняя версия.",
        "calc": "Рассчитать", "checksum_title": "Контрольные суммы",
        "view": "Вид", "inspector": "Инспектор", "bookmarks": "Закладки", "theme": "Тема", "lang": "Язык",
        "help": "Справка", "about": "О программе", "check_updates": "Проверить обновления", 
        "program": "Программа", "suite": "STORM SUITE", "hex_editor": "HEX EDITOR", "tile_manager": "TILE MANAGER", "game_dict": "GAME DICTIONARY",
        "multi_proc": "Мультиобработка", "supervisor": "Супервизор", "settings": "Настройки",
        "tools": "Инструменты", "checksum": "Контрольные суммы", "signature": "Сигнатуры", "strings": "Строки",
        "base_conv": "Конвертер", "bitwise": "Бит. опер.", "remove": "Удалить", "add_bm": "Добавить закладку",
        "analyze": "Анализ", "extract": "Извлечь", "min_len": "Мин. длина:", "result": "Результат",
        "detected": "Обнаружено:", "unknown": "Неизвестный тип", "desc": "Описание",
        "ascii": "ASCII", "unicode": "Unicode", "offset": "Смещение", "type": "Тип", "string": "Строка",
        "found": "Найдено {} строк", "extracting": "Извлечение...", "entropy": "Энтропия", "auto_update": "Авто-обновление",
        "update_err": "Ошибка обновления", "update_fail": "Не удалось проверить обновления:",
        "new_ver": "Доступна новая версия:", "current": "Текущая:", "open_page": "Открыть страницу загрузки?",
        "diff": "Сравнение", "regex_search": "Regex Поиск", "structures": "Структуры", "patches": "Патчи",
        "byte_map": "Карта байтов", "offset_calc": "Калькулятор", "new_tab": "Новая вкладка", "close_tab": "Закрыть",
        "compare": "Сравнить", "create_patch": "Создать патч", "apply_patch": "Применить патч",
        "histogram": "Гистограмма", "alignment": "Выравнивание", "base_addr": "Базовый адрес",
        "differences": "Различия", "no_diff": "Файлы идентичны", "select_file": "Выберите файл",
        "wildcard": "Маска (?? = любой)", "pattern": "Паттерн", "find_all": "Найти все",
        "export_patch": "Экспорт патча", "import_patch": "Импорт патча",
        "current_edits": "Текущие правки", "calculate": "Рассчитать", "align": "Выровнять", "aligned": "Выровнено", "warning": "Предупреждение",
        "open_file_first": "Сначала откройте файл", "offset_plus": "Смещение (+/-):",
        "no_edits": "Нет изменений для экспорта", "patch_saved": "Патч сохранён",
        "patch_applied": "Патч применён", "success": "Успех", "invalid_input": "Неверный ввод",
        "preview": "Предпросмотр", "file_a": "Файл A", "file_b": "Файл B",
        "auto": "Авто-анализ",
        "auto_sigs": "Сигнатуры файлов", "auto_strings": "Строки (ASCII > 5)", "auto_values": "Потенц. значения (Int32)",
        "auto_values_tip": "Находит малые целые числа (100-1M)", "start_analysis": "Начать анализ",
        "scanning": "Сканирование...", "found_items": "Найдено {} элементов", "analysis_complete": "Анализ завершен",
        "analysis_msg": "Найдено {} элементов.\n\nРезультаты подсвечены в Hex View.\nНаведите для описания.",
        "scalars": "Скаляры", "structures": "Структуры", "struct_fmt": "Формат (Python):",
        "parse_at_cursor": "Разобрать", "field": "Поле", "value": "Значение",
        "operation": "Операция:", "operand": "Операнд (Hex):", 
        "decimal": "Десятичное (Dec):", "hexadecimal": "Шестнадцатеричное (Hex):",
        "binary": "Двоичное (Bin):", "octal": "Восьмеричное (Oct):",
        "sig_analysis": "Анализ сигнатур", "bytes_32": "Первые 32 байта:", "no_match": "Сигнатуры не найдены",
        "history": "История", "tm_det_fmt": "Формат: {}",
        # Tile Manager
        "tm_tools": "Инструменты", "tm_draw": "Рисовать", "tm_fill": "Заливка", "tm_format": "Формат", "tm_palette": "Палитра",
        "tm_import": "Импорт BMP", "tm_export": "Экспорт BMP", "tm_zoom": "Зум", "sel": "Выд.", "hex": "Hex",
        "tm_width": "Ширина (тайлы):", "tm_auto": "Авто-скан", "tm_auto_tip": "Определить формат и ширину",
        "tm_imp_pal": "Импорт палитры", "tm_exp_pal": "Экспорт палитры", "grid": "Сетка", "grid_size": "Размер сетки",
        "animation": "Анимация",
        # Game Dictionary
        "gd_test": "Тест / Поиск", "gd_input_hint": "Вставьте Hex или Текст...", "gd_decode": "Hex → Текст",
        "gd_encode": "Текст → Hex", "gd_result": "Результат...", "gd_open_tbl": "Открыть TBL", "gd_save_tbl": "Сохранить TBL",
        "gd_hex_hint": "Hex (напр. 0A)", "gd_char_hint": "Символ", "gd_add": "Добавить", "gd_hex": "Hex", "gd_char": "Символ",
        "gd_warn_binary": "Бинарный файл? TBL обычно текстовые.", "gd_auto_ascii": "ASCII Таблица",
        "gd_ascii_done": "Создано {} ASCII записей.",
        "rom_tools": "ROM Инструменты", "open_rom": "Открыть ROM", "search_rom": "Поиск в ROM",
        "auto_detect": "Авто-определение кодировки", "export_script": "Экспорт скрипта", "import_script": "Импорт скрипта",
        # Hex Editor
        "hotspots": "Горячие точки", "clear": "Очистить",
        # Common Dialogs
        "import_img": "Импорт изобр.", "export_img": "Экспорт изобр.", "file_saved": "Файл сохранён", "error": "Ошибка",
        "info": "Инфо", "yes": "Да", "no": "Нет", "img_filter": "Изображения (*.png *.bmp *.jpg)", "all_files": "Все файлы (*.*)",
        "download_ask": "{} не найден.\nСкачать с GitHub?", "downloading": "Загрузка...", 
        "download_success": "Загружено: {}\nГотово к запуску!", "download_fail": "Ошибка загрузки:\n{}", "launch_err": "Не удалось запустить:"
    },
    "en": {
        "file": "File", "open": "Open", "save": "Save", "save_as": "Save As", "close": "Close File", "exit": "Exit",
        "edit": "Edit", "undo": "Undo", "redo": "Redo", "cut": "Cut", "copy": "Copy", "paste": "Paste",
        "find": "Find", "goto": "Go To", "select_all": "Select All", "hex": "Hex", "text": "Text", "search": "Search",
        "ready": "Ready", "processing": "Processing...", "search_res": "Search Results", "not_found": "Not found",
        "update_avail": "Update Available!", "no_update": "You have the latest version.",
        "calc": "Calculate", "checksum_title": "Checksums",
        "view": "View", "inspector": "Inspector", "bookmarks": "Bookmarks", "theme": "Theme", "lang": "Language",
        "help": "Help", "about": "About", "check_updates": "Check Updates", 
        "program": "Program", "suite": "STORM SUITE", "hex_editor": "HEX EDITOR", "tile_manager": "TILE MANAGER", "game_dict": "GAME DICTIONARY",
        "multi_proc": "Multi-processing", "supervisor": "Supervisor", "settings": "Settings",
        "tools": "Tools", "checksum": "Checksum", "signature": "Signature", "strings": "Strings",
        "base_conv": "Converter", "bitwise": "Bitwise Op.", "remove": "Remove", "add_bm": "Add Bookmark",
        "analyze": "Analyze", "extract": "Extract", "min_len": "Min. Length:", "result": "Result",
        "detected": "Detected:", "unknown": "Unknown type", "desc": "Description",
        "ascii": "ASCII", "unicode": "Unicode", "offset": "Offset", "type": "Type", "string": "String",
        "found": "Found {} strings", "extracting": "Extracting...", "entropy": "Entropy", "auto_update": "Auto-update",
        "update_err": "Update error", "update_fail": "Failed to check updates:",
        "new_ver": "New version available:", "current": "Current:", "open_page": "Open download page?",
        "diff": "Diff", "regex_search": "Regex Search", "structures": "Structures", "patches": "Patches",
        "byte_map": "Byte Map", "offset_calc": "Calculator", "new_tab": "New Tab", "close_tab": "Close",
        "compare": "Compare", "create_patch": "Create Patch", "apply_patch": "Apply Patch",
        "histogram": "Histogram", "alignment": "Alignment", "base_addr": "Base Address",
        "differences": "Differences", "no_diff": "Files are identical", "select_file": "Select File",
        "wildcard": "Wildcard (?? = any)", "pattern": "Pattern", "find_all": "Find All",
        "export_patch": "Export Patch", "import_patch": "Import Patch",
        "current_edits": "Current Edits", "calculate": "Calculate", "align": "Align", "aligned": "Aligned", "warning": "Warning",
        "open_file_first": "Open file first", "offset_plus": "Offset (+/-):",
        "no_edits": "No edits to export", "patch_saved": "Patch saved",
        "patch_applied": "Patch applied", "success": "Success", "invalid_input": "Invalid input",
        "preview": "Preview", "file_a": "File A", "file_b": "File B",
        "auto": "Auto Analysis",
        "auto_sigs": "File Signatures", "auto_strings": "Strings (ASCII > 5)", "auto_values": "Potential Vals (Int32)",
        "auto_values_tip": "Finds small integers (100-1M)", "start_analysis": "Start Analysis",
        "scanning": "Scanning...", "found_items": "Found {} items", "analysis_complete": "Analysis Complete",
        "analysis_msg": "Found {} items.\n\nResults highlighted in Hex View.\nHover for description.",
        "scalars": "Scalars", "structures": "Structures", "struct_fmt": "Struct Format (Python):",
        "parse_at_cursor": "Parse at Cursor", "field": "Field", "value": "Value",
        "operation": "Operation:", "operand": "Operand (Hex):", 
        "decimal": "Decimal (Dec):", "hexadecimal": "Hexadecimal (Hex):",
        "binary": "Binary (Bin):", "octal": "Octal (Oct):",
        "sig_analysis": "Signature Analysis", "bytes_32": "First 32 bytes:", "no_match": "Common signatures not matched",
        "history": "History", "tm_det_fmt": "Detected format: {}",
        # Tile Manager
        "tm_tools": "Tools", "tm_draw": "Draw", "tm_fill": "Fill", "tm_format": "Format", "tm_palette": "Palette",
        "tm_import": "Import BMP", "tm_export": "Export BMP", "tm_zoom": "Zoom", "sel": "Sel", "hex": "Hex",
        "tm_width": "Width (tiles):", "tm_auto": "Auto-Scan", "tm_auto_tip": "Detect format and width",
        "tm_imp_pal": "Import Palette", "tm_exp_pal": "Export Palette", "grid": "Grid", "grid_size": "Grid Size",
        "animation": "Animation",
        # Game Dictionary
        "gd_test": "Test / Search", "gd_input_hint": "Paste Hex or Text here...", "gd_decode": "Hex → Text",
        "gd_encode": "Text → Hex", "gd_result": "Result...", "gd_open_tbl": "Open TBL", "gd_save_tbl": "Save TBL",
        "gd_hex_hint": "Hex (e.g. 0A)", "gd_char_hint": "Char", "gd_add": "Add", "gd_hex": "Hex", "gd_char": "Char",
        "gd_warn_binary": "Binary file? TBLs are usually text.", "gd_auto_ascii": "ASCII Table",
        "gd_ascii_done": "Generated {} ASCII entries.",
        "rom_tools": "ROM Tools", "open_rom": "Open ROM", "search_rom": "Search in ROM",
        "auto_detect": "Auto-detect Encoding", "export_script": "Export Script", "import_script": "Import Script",
        # Hex Editor
        "hotspots": "Hotspots", "clear": "Clear",
        # Common Dialogs
        "import_img": "Import Image", "export_img": "Export Image", "file_saved": "File saved", "error": "Error",
        "info": "Info", "yes": "Yes", "no": "No", "img_filter": "Images (*.png *.bmp *.jpg)", "all_files": "All Files (*.*)",
        "download_ask": "{} not found.\nDownload from GitHub?", "downloading": "Downloading...", 
        "download_success": "Downloaded: {}\nReady to launch!", "download_fail": "Download failed:\n{}", "launch_err": "Could not launch:"
    }
}

class StormApp(QMainWindow):
    """Base class for all Storm Suite applications"""
    def __init__(self, app_key, parent=None):
        super().__init__(parent)
        self.app_key = app_key # e.g. "hex_editor"
        self.github_repo = APP_REPOS.get(app_key, "storm-hex-editor")
        self.settings = QSettings("StormSuite", self.app_key)
        self.global_settings = QSettings("StormSuite", "Global")
        
        self.current_lang = self.global_settings.value("lang", "ru")
        self.current_theme_name = self.global_settings.value("theme", "Dark (Default)")
        
        self.init_common_ui()
        
    def init_common_ui(self):
        # Common window setup
        icon_file = APP_ICONS.get(self.app_key, "stormhexeditor.ico")
        icon_path = resource_path(icon_file)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1200, 800)
        
        # Load geometry if saved
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
            
        # Program Menu (Switcher)
        bar = self.menuBar()
        self.menu_program = bar.addMenu(LOCALE[self.current_lang]["program"])
        
        actions = [
            ("suite", LOCALE[self.current_lang]["suite"]),
            ("hex_editor", LOCALE[self.current_lang]["hex_editor"]),
            ("tile_manager", LOCALE[self.current_lang]["tile_manager"]),
            ("game_dict", LOCALE[self.current_lang]["game_dict"]),
        ]
        
        for key, name in actions:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, k=key: self.switch_app(k))
            # Mark current app as disabled or checked
            if key == self.app_key:
                action.setEnabled(False) 
                action.setCheckable(True)
                action.setChecked(True)
            self.menu_program.addAction(action)
            
    def switch_app(self, app_key):
        """Switch to another application in the suite"""
        import subprocess
        
        script_map = {
            "hex_editor": "stormhexeditor.py",
            "tile_manager": "stormtilemanager.py",
            "game_dict": "stormgamedictionary.py",
            "suite": "stormsuite.py"
        }
        
        script = script_map.get(app_key)
        if not script:
            return

        # Simple separate process launch
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script)
        subprocess.Popen([sys.executable, script_path], cwd=os.path.dirname(script_path))
        
        # Optional: Close this app? User asked for multi-processing.
        # "Сделай возможность запускать разные программы, влкючая несколько копий."
        # So we KEEP the current one open.

    def apply_theme(self, theme_name=None):
        if theme_name:
            self.current_theme_name = theme_name
            self.global_settings.setValue("theme", theme_name)
            
        theme = THEMES.get(self.current_theme_name, THEMES["Dark (Default)"])
        
        # Global Stylesheet
        qss = f"""
            QMainWindow, QDialog, QWidget {{ 
                background-color: {theme['bg']}; color: {theme['fg']}; font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox {{
                background-color: {theme['input_bg']}; color: {theme['input_fg']}; 
                border: 1px solid {theme['input_border']}; padding: 4px; border-radius: 4px;
            }}
            QPushButton {{
                background-color: {theme['btn_bg']}; color: {theme['btn_fg']};
                border: 1px solid {theme['input_border']}; padding: 6px 12px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {theme['btn_hover']}; }}
            QMenuBar {{ background-color: {theme['menu_bg']}; color: {theme['menu_fg']}; }}
            QMenuBar::item:selected {{ background-color: {theme['highlight']}; color: {theme['highlight_text']}; }}
            QMenu {{ background-color: {theme['menu_bg']}; border: 1px solid {theme['input_border']}; color: {theme['menu_fg']}; }}
            QMenu::item:selected {{ background-color: {theme['highlight']}; color: {theme['highlight_text']}; }}
            QTabWidget::pane {{ border: 1px solid {theme['input_border']}; }}
            QTabBar::tab {{ background-color: {theme['btn_bg']}; color: {theme['btn_fg']}; padding: 6px; }}
            QTabBar::tab:selected {{ background-color: {theme['input_bg']}; border-bottom: 2px solid {theme['highlight']}; }}
            QHeaderView::section {{ background-color: {theme['btn_bg']}; padding: 4px; border: none; }}
            QTableWidget {{ gridline-color: {theme['input_border']}; }}
            QSplitter::handle {{ background-color: {theme['input_border']}; }}
        """
        self.setStyleSheet(qss)
        
    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)
