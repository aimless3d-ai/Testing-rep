"""Modern dark (and light) theme as a Qt style sheet."""
from __future__ import annotations

DARK = {
    "bg": "#12141a",
    "surface": "#1a1d26",
    "surface_alt": "#212533",
    "border": "#2c3140",
    "text": "#e8eaf0",
    "text_dim": "#9aa1b2",
    "accent": "#4f7cff",
    "accent_hover": "#6a91ff",
    "accent_press": "#3c66e0",
    "success": "#3fbf7f",
    "warning": "#e6a935",
    "danger": "#e5544b",
    "input": "#171a23",
}

LIGHT = {
    "bg": "#f4f5f8",
    "surface": "#ffffff",
    "surface_alt": "#eef0f5",
    "border": "#d7dae3",
    "text": "#1b1e26",
    "text_dim": "#5c6377",
    "accent": "#3563e9",
    "accent_hover": "#4a75f0",
    "accent_press": "#2a51c9",
    "success": "#1f9d5b",
    "warning": "#b8791a",
    "danger": "#c33a32",
    "input": "#ffffff",
}

_QSS = """
* {{ font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif; font-size: 13px; }}
QWidget {{ background-color: {bg}; color: {text}; }}
QMainWindow, QDialog {{ background-color: {bg}; }}

QFrame#Card, QGroupBox {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
QGroupBox {{ margin-top: 18px; padding: 14px 12px 12px 12px; font-weight: 600; }}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 6px;
    color: {text_dim};
}}

QLabel#H1 {{ font-size: 24px; font-weight: 700; }}
QLabel#H2 {{ font-size: 17px; font-weight: 600; }}
QLabel#Dim {{ color: {text_dim}; }}
QLabel#Badge {{
    background-color: {surface_alt}; border: 1px solid {border};
    border-radius: 10px; padding: 4px 10px; color: {text_dim};
}}

QPushButton {{
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 16px;
    color: {text};
}}
QPushButton:hover {{ background-color: {border}; }}
QPushButton:pressed {{ background-color: {surface}; }}
QPushButton:disabled {{ color: {text_dim}; background-color: {surface}; }}
QPushButton#Primary {{
    background-color: {accent}; border: 1px solid {accent}; color: #ffffff; font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#Primary:pressed {{ background-color: {accent_press}; }}
QPushButton#Danger {{ color: {danger}; }}
QPushButton#Danger:hover {{ background-color: {danger}; color: #ffffff; }}
QPushButton#Nav {{
    text-align: left; padding: 11px 16px; border: none; border-radius: 9px;
    background-color: transparent; color: {text_dim}; font-size: 14px;
}}
QPushButton#Nav:hover {{ background-color: {surface_alt}; color: {text}; }}
QPushButton#Nav:checked {{ background-color: {accent}; color: #ffffff; font-weight: 600; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {input};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {accent};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {text_dim}; margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {surface}; border: 1px solid {border};
    selection-background-color: {accent}; outline: none;
}}

QListWidget, QTableWidget, QTreeWidget {{
    background-color: {surface}; border: 1px solid {border};
    border-radius: 10px; outline: none;
}}
QListWidget::item {{ padding: 6px; border-radius: 8px; }}
QListWidget::item:selected, QTableWidget::item:selected {{
    background-color: {accent}; color: #ffffff;
}}
QHeaderView::section {{
    background-color: {surface_alt}; color: {text_dim}; border: none;
    border-bottom: 1px solid {border}; padding: 8px;
}}
QTableWidget {{ gridline-color: {border}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {text_dim}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

QProgressBar {{
    background-color: {surface_alt}; border: 1px solid {border};
    border-radius: 8px; height: 16px; text-align: center; color: {text};
}}
QProgressBar::chunk {{ background-color: {accent}; border-radius: 7px; }}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {border};
    border-radius: 4px; background-color: {input};
}}
QCheckBox::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}

QTabWidget::pane {{ border: 1px solid {border}; border-radius: 10px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {text_dim}; padding: 8px 16px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: {surface}; color: {text}; }}

QSplitter::handle {{ background-color: {border}; }}
QStatusBar {{ background-color: {surface}; color: {text_dim}; }}
QToolTip {{
    background-color: {surface_alt}; color: {text};
    border: 1px solid {border}; padding: 6px; border-radius: 6px;
}}
QFrame#DropZone {{
    border: 2px dashed {border}; border-radius: 14px; background-color: {surface};
}}
QFrame#DropZoneActive {{
    border: 2px dashed {accent}; border-radius: 14px; background-color: {surface_alt};
}}
QFrame#Sidebar {{ background-color: {surface}; border-right: 1px solid {border}; }}
"""


def palette(theme: str = "dark") -> dict[str, str]:
    return LIGHT if theme == "light" else DARK


def stylesheet(theme: str = "dark") -> str:
    return _QSS.format(**palette(theme))
