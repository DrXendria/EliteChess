"""
Application themes and styling.
4 themes: Light, Dark, Modern Dark, System.
"""
import sys
from enum import Enum


class AppTheme(Enum):
    LIGHT = "light"
    DARK = "dark"
    MODERN_DARK = "modern_dark"
    SYSTEM = "system"

    @property
    def display_name(self) -> str:
        names = {
            AppTheme.LIGHT: "Açık (Light)",
            AppTheme.DARK: "Koyu (Dark)",
            AppTheme.MODERN_DARK: "Modern Koyu",
            AppTheme.SYSTEM: "Sistem",
        }
        return names[self]


def detect_system_theme() -> str:
    """Detect OS theme preference."""
    try:
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
    except Exception:
        pass
    return "light"


def get_stylesheet(theme: AppTheme) -> str:
    """Get QSS stylesheet for the given theme."""
    if theme == AppTheme.SYSTEM:
        detected = detect_system_theme()
        if detected == "dark":
            return _dark_stylesheet()
        return _light_stylesheet()
    elif theme == AppTheme.LIGHT:
        return _light_stylesheet()
    elif theme == AppTheme.DARK:
        return _dark_stylesheet()
    elif theme == AppTheme.MODERN_DARK:
        return _modern_dark_stylesheet()
    return ""


# ─── LIGHT ───────────────────────────────────────────────────────────────────

def _light_stylesheet() -> str:
    return """
    * {
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #f0f2f5;
        color: #1f2937;
    }
    QCheckBox {
        color: #1f2937;
    }
    QMenuBar {
        background-color: #ffffff;
        border-bottom: 1px solid #d1d5db;
        padding: 2px;
    }
    QMenuBar::item {
        padding: 6px 12px;
        background: transparent;
        color: #1f2937;
    }
    QMenuBar::item:selected {
        background-color: #e5e7eb;
        border-radius: 4px;
    }
    QMenu {
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        color: #1f2937;
    }
    QMenu::item:selected {
        background-color: #dbeafe;
        border-radius: 4px;
    }
    QTabWidget::pane {
        border: 1px solid #d1d5db;
        background: #ffffff;
        border-radius: 8px;
    }
    QTabBar::tab {
        background: #e5e7eb;
        color: #4b5563;
        padding: 8px 20px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        color: #1e40af;
        border-bottom: 2px solid #2563eb;
    }
    QTabBar::tab:hover {
        background: #f3f4f6;
    }
    QTableWidget, QTableView {
        background-color: #ffffff;
        color: #1f2937;
        alternate-background-color: #f9fafb;
        gridline-color: #e5e7eb;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        selection-background-color: #dbeafe;
        selection-color: #1e3a5f;
    }
    QHeaderView::section {
        background-color: #1e3a5f;
        color: #ffffff;
        padding: 6px 10px;
        border: none;
        font-weight: 600;
    }
    QPushButton {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 500;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #1d4ed8;
    }
    QPushButton:pressed {
        background-color: #1e40af;
    }
    QPushButton:disabled {
        background-color: #9ca3af;
    }
    QPushButton[secondary="true"] {
        background-color: #e5e7eb;
        color: #374151;
    }
    QPushButton[secondary="true"]:hover {
        background-color: #d1d5db;
    }
    QPushButton[danger="true"] {
        background-color: #dc2626;
    }
    QPushButton[danger="true"]:hover {
        background-color: #b91c1c;
    }
    QLineEdit, QSpinBox, QComboBox {
        padding: 7px 12px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        background: #ffffff;
        color: #1f2937;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 2px solid #2563eb;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QComboBox QAbstractItemView, QListWidget {
        background: #ffffff;
        color: #1f2937;
        selection-background-color: #dbeafe;
    }
    QGroupBox {
        font-weight: 600;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        background: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 6px;
        color: #1e40af;
    }
    QStatusBar {
        background: #ffffff;
        border-top: 1px solid #d1d5db;
        color: #6b7280;
    }
    QToolBar {
        background: #ffffff;
        border-bottom: 1px solid #d1d5db;
        spacing: 4px;
        padding: 4px;
    }
    QLabel {
        color: #1f2937;
    }
    QScrollBar:vertical {
        width: 8px;
        background: #f0f2f5;
    }
    QScrollBar::handle:vertical {
        background: #9ca3af;
        border-radius: 4px;
        min-height: 20px;
    }
    """


# ─── DARK ────────────────────────────────────────────────────────────────────

def _dark_stylesheet() -> str:
    return """
    * {
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #1a1a2e;
    }
    QMenuBar {
        background-color: #16213e;
        border-bottom: 1px solid #0f3460;
        padding: 2px;
    }
    QMenuBar::item {
        padding: 6px 12px;
        background: transparent;
        color: #e2e8f0;
    }
    QMenuBar::item:selected {
        background-color: #0f3460;
        border-radius: 4px;
    }
    QMenu {
        background-color: #16213e;
        border: 1px solid #0f3460;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        color: #e2e8f0;
    }
    QMenu::item:selected {
        background-color: #0f3460;
        border-radius: 4px;
    }
    QTabWidget::pane {
        border: 1px solid #0f3460;
        background: #16213e;
        border-radius: 8px;
    }
    QTabBar::tab {
        background: #1a1a2e;
        color: #94a3b8;
        padding: 8px 20px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
    }
    QTabBar::tab:selected {
        background: #16213e;
        color: #60a5fa;
        border-bottom: 2px solid #3b82f6;
    }
    QTabBar::tab:hover {
        background: #1e2a4a;
    }
    QTableWidget, QTableView {
        background-color: #16213e;
        alternate-background-color: #1a2744;
        gridline-color: #0f3460;
        border: 1px solid #0f3460;
        border-radius: 6px;
        color: #e2e8f0;
        selection-background-color: #1e40af;
        selection-color: #ffffff;
    }
    QHeaderView::section {
        background-color: #0f3460;
        color: #e2e8f0;
        padding: 6px 10px;
        border: none;
        font-weight: 600;
    }
    QPushButton {
        background-color: #3b82f6;
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 500;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #2563eb;
    }
    QPushButton:pressed {
        background-color: #1d4ed8;
    }
    QPushButton:disabled {
        background-color: #475569;
        color: #94a3b8;
    }
    QPushButton[secondary="true"] {
        background-color: #334155;
        color: #e2e8f0;
    }
    QPushButton[secondary="true"]:hover {
        background-color: #475569;
    }
    QPushButton[danger="true"] {
        background-color: #dc2626;
    }
    QPushButton[danger="true"]:hover {
        background-color: #b91c1c;
    }
    QLineEdit, QSpinBox, QComboBox {
        padding: 7px 12px;
        border: 1px solid #334155;
        border-radius: 6px;
        background: #1e293b;
        color: #e2e8f0;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 2px solid #3b82f6;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QComboBox QAbstractItemView {
        background: #1e293b;
        color: #e2e8f0;
        selection-background-color: #0f3460;
    }
    QGroupBox {
        font-weight: 600;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        background: #16213e;
        color: #e2e8f0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 6px;
        color: #60a5fa;
    }
    QStatusBar {
        background: #16213e;
        border-top: 1px solid #0f3460;
        color: #94a3b8;
    }
    QToolBar {
        background: #16213e;
        border-bottom: 1px solid #0f3460;
        spacing: 4px;
        padding: 4px;
    }
    QLabel {
        color: #e2e8f0;
    }
    QScrollBar:vertical {
        width: 8px;
        background: #1a1a2e;
    }
    QScrollBar::handle:vertical {
        background: #475569;
        border-radius: 4px;
        min-height: 20px;
    }
    """


# ─── MODERN DARK ─────────────────────────────────────────────────────────────

def _modern_dark_stylesheet() -> str:
    return """
    * {
        font-family: 'Segoe UI', 'Arial', sans-serif;
    }
    QMainWindow, QDialog {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
    }
    QMenuBar {
        background-color: rgba(15, 12, 41, 200);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2px;
    }
    QMenuBar::item {
        padding: 6px 12px;
        background: transparent;
        color: #e0e0ff;
    }
    QMenuBar::item:selected {
        background-color: rgba(139, 92, 246, 0.3);
        border-radius: 4px;
    }
    QMenu {
        background-color: rgba(15, 12, 41, 240);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        color: #e0e0ff;
    }
    QMenu::item:selected {
        background-color: rgba(139, 92, 246, 0.4);
        border-radius: 4px;
    }
    QTabWidget::pane {
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(36, 36, 62, 180);
        border-radius: 10px;
    }
    QTabBar::tab {
        background: rgba(15, 12, 41, 150);
        color: #a0a0cc;
        padding: 8px 20px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 500;
    }
    QTabBar::tab:selected {
        background: rgba(139, 92, 246, 0.2);
        color: #c4b5fd;
        border-bottom: 2px solid #8b5cf6;
    }
    QTabBar::tab:hover {
        background: rgba(139, 92, 246, 0.15);
    }
    QTableWidget, QTableView {
        background-color: rgba(36, 36, 62, 200);
        alternate-background-color: rgba(48, 43, 99, 100);
        gridline-color: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        color: #e0e0ff;
        selection-background-color: rgba(139, 92, 246, 0.35);
        selection-color: #ffffff;
    }
    QHeaderView::section {
        background-color: rgba(139, 92, 246, 0.25);
        color: #c4b5fd;
        padding: 6px 10px;
        border: none;
        font-weight: 600;
    }
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #7c3aed, stop:1 #a855f7);
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 8px;
        font-weight: 600;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #6d28d9, stop:1 #9333ea);
    }
    QPushButton:pressed {
        background-color: #5b21b6;
    }
    QPushButton:disabled {
        background-color: rgba(100, 100, 140, 0.4);
        color: #666;
    }
    QPushButton[secondary="true"] {
        background: rgba(255, 255, 255, 0.08);
        color: #c4b5fd;
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    QPushButton[secondary="true"]:hover {
        background: rgba(139, 92, 246, 0.2);
    }
    QPushButton[danger="true"] {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #dc2626, stop:1 #ef4444);
    }
    QPushButton[danger="true"]:hover {
        background-color: #b91c1c;
    }
    QLineEdit, QSpinBox, QComboBox {
        padding: 7px 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        background: rgba(15, 12, 41, 150);
        color: #e0e0ff;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 2px solid #8b5cf6;
    }
    QComboBox::drop-down {
        border: none;
        padding-right: 8px;
    }
    QComboBox QAbstractItemView {
        background: rgba(15, 12, 41, 240);
        color: #e0e0ff;
        selection-background-color: rgba(139, 92, 246, 0.4);
        border-radius: 6px;
    }
    QGroupBox {
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 16px;
        background: rgba(36, 36, 62, 150);
        color: #e0e0ff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 6px;
        color: #c4b5fd;
    }
    QStatusBar {
        background: rgba(15, 12, 41, 200);
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        color: #a0a0cc;
    }
    QToolBar {
        background: rgba(15, 12, 41, 200);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        spacing: 4px;
        padding: 4px;
    }
    QLabel {
        color: #e0e0ff;
    }
    QScrollBar:vertical {
        width: 8px;
        background: rgba(15, 12, 41, 100);
    }
    QScrollBar::handle:vertical {
        background: rgba(139, 92, 246, 0.4);
        border-radius: 4px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(139, 92, 246, 0.6);
    }
    """
