"""Dark retro theme for ChiptuneStudio."""

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication

# Colour constants (also used by paint code)
BG        = "#0d0d0d"
BG_PANEL  = "#141414"
BG_STRIP  = "#1a1a1a"
BG_INPUT  = "#222222"
GREEN     = "#00ff88"
CYAN      = "#00ccff"
YELLOW    = "#ffee00"
RED       = "#ff4455"
FG        = "#e0e0e0"
FG_DIM    = "#666666"
BORDER    = "#2a2a2a"
ACCENT    = "#333333"

QSS = f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {BG};
    color: {FG};
    font-family: "Courier New", monospace;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

/* ── Toolbar ─────────────────────────────────────────────────────────────── */
#Toolbar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_INPUT};
    color: {FG};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 3px 10px;
    min-height: 24px;
}}
QPushButton:hover {{
    border-color: {GREEN};
    color: {GREEN};
}}
QPushButton:pressed {{
    background-color: #1a1a1a;
}}
QPushButton#PlayBtn {{
    color: {GREEN};
    border-color: {GREEN};
    font-weight: bold;
}}
QPushButton#PlayBtn:checked {{
    background-color: #003322;
}}
QPushButton#StopBtn {{
    color: {RED};
    border-color: {RED};
}}
QPushButton#MuteBtn {{
    color: {FG_DIM};
    border-color: {BORDER};
    padding: 2px 6px;
    min-width: 28px;
}}
QPushButton#MuteBtn:checked {{
    color: {YELLOW};
    border-color: {YELLOW};
    background-color: #1a1500;
}}

/* ── LineEdit / ComboBox ─────────────────────────────────────────────────── */
QLineEdit, QComboBox {{
    background-color: {BG_INPUT};
    color: {FG};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 2px 6px;
    selection-background-color: {GREEN};
    selection-color: #000000;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {GREEN};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {FG};
    font-size: 13px;
    selection-background-color: {BG_STRIP};
    border: 1px solid {BORDER};
}}

/* ── Sliders ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -4px 0;
    background-color: {GREEN};
    border-radius: 6px;
}}
QSlider::sub-page:horizontal {{
    background-color: {GREEN};
    border-radius: 2px;
}}
QSlider::groove:vertical {{
    width: 4px;
    background-color: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    width: 12px;
    height: 12px;
    margin: 0 -4px;
    background-color: {GREEN};
    border-radius: 6px;
}}
QSlider::sub-page:vertical {{
    background-color: {GREEN};
    border-radius: 2px;
}}

/* ── ScrollArea ──────────────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
}}
QScrollBar:horizontal, QScrollBar:vertical {{
    background-color: {BG_PANEL};
    border: none;
}}
QScrollBar::handle:horizontal, QScrollBar::handle:vertical {{
    background-color: {ACCENT};
    border-radius: 3px;
    min-width: 20px;
    min-height: 20px;
}}
QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {{
    background-color: {FG_DIM};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0;
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel#AppTitle {{
    color: {GREEN};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 2px;
}}
QLabel#SectionHeader {{
    color: {FG_DIM};
    font-size: 10px;
    letter-spacing: 1px;
}}

/* ── Status Bar ──────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_PANEL};
    color: {FG_DIM};
    border-top: 1px solid {BORDER};
}}

/* ── Channel Settings Panel ──────────────────────────────────────────────── */
#ChannelSettingsPanel {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
"""


def apply_theme(app: QApplication) -> None:
    # Set the application font in point units first.
    # Qt's QComboBox popup window calls font.pointSize() when it inherits the font;
    # if the font was only ever set via a px-based stylesheet, pointSize() returns -1
    # and triggers "QFont::setPointSize: Point size <= 0 (-1)".
    # An explicit pt font on the app object gives every widget a valid pointSize().
    app.setFont(QFont("Courier New", 10))
    app.setStyleSheet(QSS)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(FG))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_STRIP))
    palette.setColor(QPalette.ColorRole.Text,            QColor(FG))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BG_INPUT))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(FG))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(GREEN))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    app.setPalette(palette)
