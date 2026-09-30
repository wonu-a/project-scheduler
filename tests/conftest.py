import os

# UI tests run headless. Must be set before any QApplication exists.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
