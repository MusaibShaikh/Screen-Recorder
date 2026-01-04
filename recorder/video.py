import subprocess
import tempfile
import os
import tkinter as tk

def detect_encoder():
    """Detect available hardware encoder."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        ).stdout.lower()
    except Exception:
        return "libx264", "CPU"

    if "h264_nvenc" in out:
        return "h264_nvenc", "NVIDIA"
    if "h264_qsv" in out:
        return "h264_qsv", "INTEL"
    if "h264_amf" in out:
        return "h264_amf", "AMD"

    return "libx264", "CPU"

VIDEO_ENCODER, ENCODER_LABEL = detect_encoder()

class HotkeyHelpDialog:
    _instance = None
    
    @classmethod
    def toggle(cls, parent):
        if cls._instance is None or not cls._instance.dialog.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.dialog.destroy()
            cls._instance = None
    
    def __init__(self, parent):
        from tkinter import ttk
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Keyboard Shortcuts")
        self.dialog.geometry("400x250")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (250 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        
        self.dialog.bind("<Escape>", lambda e: self.on_close())
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        self.dialog.focus_set()
        
    def create_widgets(self):
        from tkinter import ttk
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="📋 Keyboard Shortcuts", font=("Arial", 12, "bold")).pack(pady=(0, 15))
        
        shortcuts_frame = ttk.Frame(main_frame)
        shortcuts_frame.pack(fill=tk.BOTH, expand=True)
        
        shortcuts = [
            ("Alt + S", "Start/Stop recording"),
            ("Alt + P", "Pause/Resume recording"),
            ("F1", "Show/Hide this help dialog")
        ]
        
        for key, description in shortcuts:
            row = ttk.Frame(shortcuts_frame)
            row.pack(fill=tk.X, pady=5)
            
            ttk.Label(row, text=key, font=("Courier", 10, "bold"), width=12, anchor="w").pack(side=tk.LEFT)
            ttk.Label(row, text=description, anchor="w").pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        ttk.Button(main_frame, text="Close (or press Esc)", command=self.on_close, width=20).pack()
        
    def on_close(self):
        HotkeyHelpDialog._instance = None
        self.dialog.destroy()
