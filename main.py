import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import apply_theme

app = QApplication(sys.argv)
apply_theme(app)

win = MainWindow()
win.show()

sys.exit(app.exec())
