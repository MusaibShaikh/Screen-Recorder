#!/usr/bin/env python3
"""
Screen Recorder - Entry Point
"""

import tkinter as tk
from recorder.app import ScreenRecorderApp

def main():
    root = tk.Tk()
    app = ScreenRecorderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
