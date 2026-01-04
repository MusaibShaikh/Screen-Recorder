import tkinter as tk
from tkinter import ttk, filedialog
import subprocess
import threading
import keyboard
import os
import time
import psutil
from datetime import datetime
import tempfile
import atexit
import ctypes
import shutil

from .audio import AudioRecorder
from .region import RegionSelector
from .video import HotkeyHelpDialog, VIDEO_ENCODER, ENCODER_LABEL
from .tray import setup_tray

class ScreenRecorderApp:
    def __init__(self, root):
        self.root = root
        root.title("Screen Recorder")
        root.minsize(420, 300)
        root.resizable(False, False)

        self.ffmpeg = None
        self.paused = False
        self.region = None
        self.tray_icon = None
        self.video_segments = []
        self.temp_dir = tempfile.mkdtemp(prefix="screen_recorder_video_")
        self.audio_recorder = AudioRecorder()
        
        self.timer_running = False
        self.start_time = 0 
        self.total_session_duration = 0 

        self.video_mode = tk.StringVar(value="fullscreen")
        self.quality = tk.StringVar(value="Medium")
        self.system_audio = tk.BooleanVar()
        self.mic_audio = tk.BooleanVar()
        self.selected_mic = tk.StringVar()
        self.sys_vol = tk.IntVar(value=100)
        self.mic_vol = tk.IntVar(value=100)

        self.save_dir = os.path.join(os.path.expanduser("~"), "Videos", "Screen Recordings")
        os.makedirs(self.save_dir, exist_ok=True)

        if os.name == 'nt':
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        self.build_ui()
        self.update_visibility()
        self.register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.setup_tray()
        atexit.register(self.cleanup_temp_files)

    def build_ui(self):
        self.main = ttk.Frame(self.root, padding=15)
        self.main.pack(fill="x")
        row = 0
        
        # Top header row with encoder info and help button
        header_frame = ttk.Frame(self.main)
        header_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1
        
        # Help button on the right
        ttk.Button(header_frame, text="Hotkeys (F1)", command=self.show_hotkey_help, width=12).pack(side="left")
        ttk.Label(self.main, text=f"Encoder: {ENCODER_LABEL}", foreground="gray").grid(row=row, column=0, sticky="w", pady=(0, 12)); row += 1
        ttk.Label(self.main, text="Video Mode").grid(row=row, column=0, sticky="w"); row += 1
        ttk.Radiobutton(self.main, text="Full Screen", variable=self.video_mode, value="fullscreen", command=self.update_visibility).grid(row=row, column=0, sticky="w"); row += 1
        ttk.Radiobutton(self.main, text="Region", variable=self.video_mode, value="region", command=self.update_visibility).grid(row=row, column=0, sticky="w"); row += 1
        self.region_btn = ttk.Button(self.main, text="Select Region", command=self.select_region)
        self.region_btn.grid(row=row, column=0, sticky="w", pady=(4, 12)); row += 1
        ttk.Label(self.main, text="Quality").grid(row=row, column=0, sticky="w"); row += 1
        ttk.Combobox(self.main, textvariable=self.quality, values=["Low", "Medium", "High", "Very High"], state="readonly", width=20).grid(row=row, column=0, sticky="w", pady=(0, 12)); row += 1
        ttk.Label(self.main, text="Audio").grid(row=row, column=0, sticky="w"); row += 1
        ttk.Checkbutton(self.main, text="System Audio", variable=self.system_audio, command=self.update_visibility).grid(row=row, column=0, sticky="w"); row += 1
        self.sys_frame = self.add_volume_row(self.main, self.sys_vol, "System audio level (recording only)")
        self.sys_frame.grid(row=row, column=0, sticky="w"); row += 1
        ttk.Checkbutton(self.main, text="Mic Audio", variable=self.mic_audio, command=self.update_visibility).grid(row=row, column=0, sticky="w", pady=(8, 0)); row += 1
        self.detect_btn = ttk.Button(self.main, text="Detect Mics", command=self.detect_mics)
        self.detect_btn.grid(row=row, column=0, sticky="w"); row += 1
        self.mic_dropdown = ttk.Combobox(self.main, textvariable=self.selected_mic, state="readonly", width=30)
        self.mic_dropdown.grid(row=row, column=0, sticky="w"); row += 1
        self.mic_frame = self.add_volume_row(self.main, self.mic_vol, "Mic audio level (recording only)")
        self.mic_frame.grid(row=row, column=0, sticky="w", pady=(0, 12)); row += 1
        ttk.Label(self.main, text="Saving to:", foreground="gray").grid(row=row, column=0, sticky="w"); row += 1
        self.save_label = ttk.Label(self.main, text=self.save_dir, wraplength=380, foreground="gray")
        self.save_label.grid(row=row, column=0, sticky="w"); row += 1
        ttk.Button(self.main, text="Select Save Folder", command=self.select_save_folder).grid(row=row, column=0, sticky="w", pady=(4, 12)); row += 1
        self.control_container = ttk.Frame(self.main)
        self.control_container.grid(row=row, column=0, sticky="w")
        
        self.start_btn = ttk.Button(self.control_container, text="Start Recording", command=self.toggle)
        self.start_btn.pack(side="left")
        self.recording_controls = ttk.Frame(self.control_container)
        self.timer_label = ttk.Label(self.recording_controls, text="00:00:00", font=("Arial", 10, "bold"))
        self.timer_label.pack(side="left", padx=(0, 10))
        self.pause_btn = ttk.Button(self.recording_controls, text="Pause", command=self.pause)
        self.pause_btn.pack(side="left", padx=2)
        self.stop_btn = ttk.Button(self.recording_controls, text="Stop", command=self.toggle)
        self.stop_btn.pack(side="left", padx=2)

    def add_volume_row(self, parent, var, label_text):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text=label_text).pack(side="left", padx=(0, 8))
        ttk.Scale(frame, from_=0, to=100, variable=var, length=160).pack(side="left")
        entry = ttk.Entry(frame, width=5, justify="center")
        entry.pack(side="left", padx=(8, 2))
        ttk.Label(frame, text="%").pack(side="left")
        entry.insert(0, str(var.get()))
        def sync(*_): entry.delete(0, "end"); entry.insert(0, str(var.get()))
        var.trace_add("write", sync)
        return frame

    def update_visibility(self):
        self.region_btn.grid() if self.video_mode.get() == "region" else self.region_btn.grid_remove()
        self.sys_frame.grid() if self.system_audio.get() else self.sys_frame.grid_remove()
        if self.mic_audio.get():
            self.detect_btn.grid(); self.mic_dropdown.grid(); self.mic_frame.grid()
        else:
            self.detect_btn.grid_remove(); self.mic_dropdown.grid_remove(); self.mic_frame.grid_remove()
        self.root.geometry("")

    def lock_ui(self, lock):
        state = "disabled" if lock else "normal"
        for child in self.main.winfo_children():
            if child != self.control_container:
                try: child.configure(state=state)
                except: pass

    def update_timer(self):
        if self.timer_running and not self.paused:
            current_elapsed = time.time() - self.start_time
            display_time = int(self.total_session_duration + current_elapsed)
            m, s = divmod(display_time, 60); h, m = divmod(m, 60)
            self.timer_label.config(text=f"{h:02d}:{m:02d}:{s:02d}")
            self.root.after(1000, self.update_timer)

    def start_video_segment(self):
        fps, bitrate = {"Low": ("30", "1500k"), "Medium": ("60", "4500k"), "High": ("60", "8000k"), "Very High": ("60", "12000k")}[self.quality.get()]
        segment_file = os.path.join(self.temp_dir, f"video_segment_{len(self.video_segments):04d}.mp4")
        cmd = ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", fps]
        if self.video_mode.get() == "region" and self.region:
            x, y, w, h = self.region
            cmd += ["-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}"]
        cmd += ["-i", "desktop", "-an", "-c:v", VIDEO_ENCODER, "-b:v", bitrate, "-pix_fmt", "yuv420p", segment_file]
        try:
            time.sleep(0.2)
            startupinfo = None
            
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            self.ffmpeg = subprocess.Popen(cmd, stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0, startupinfo= startupinfo)
            return segment_file
        except: return None

    def stop_video_segment(self):
        if self.ffmpeg:
            try:
                self.ffmpeg.stdin.write(b"q"); self.ffmpeg.stdin.flush()
                self.ffmpeg.wait(timeout=3)
            except: self.ffmpeg.kill()
            finally: self.ffmpeg = None

    def toggle(self):
        if self.timer_running or self.paused:
            self.timer_running = False
            self.stop_video_segment()
            self.audio_recorder.stop()
            self.combine_and_save_segments()
            self.recording_controls.pack_forget()
            self.start_btn.pack(side="left")
            self.lock_ui(False); self.show_window()
            self.video_segments = []; self.total_session_duration = 0; self.paused = False
        else:
            self.video_segments = []; self.total_session_duration = 0
            self.start_time = time.time(); self.timer_running = True; self.paused = False
            self.audio_recorder.start_recording(self.system_audio.get(), self.mic_audio.get())
            sf = self.start_video_segment()
            if sf:
                self.video_segments.append(sf)
                self.start_btn.pack_forget(); self.recording_controls.pack(side="left")
                self.timer_label.config(text="00:00:00", foreground="red")
                self.lock_ui(True); self.update_timer(); self.root.withdraw()

    def pause(self):
        if not self.paused:
            self.total_session_duration += (time.time() - self.start_time)
            self.paused = True; self.audio_recorder.pause(); self.stop_video_segment()
            self.pause_btn.config(text="Resume"); self.timer_label.config(foreground="orange")
        else:
            self.paused = False; self.start_time = time.time()
            self.audio_recorder.resume()
            sf = self.start_video_segment()
            if sf: self.video_segments.append(sf)
            self.pause_btn.config(text="Pause"); self.timer_label.config(foreground="red"); self.update_timer()

    def combine_and_save_segments(self):
        if not self.video_segments: return
        try:
            output = os.path.join(self.save_dir, f"recording_{datetime.now():%Y%m%d_%H%M%S}.mp4")
            list_file = os.path.join(self.temp_dir, "video_list.txt")
            with open(list_file, "w") as f:
                for s in self.video_segments:
                    if os.path.exists(s): f.write(f"file '{s.replace(os.sep, '/')}'")
            
            temp_v = os.path.join(self.temp_dir, "combined_v.mp4")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", temp_v], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            temp_a = self.audio_recorder.combine_audio_segments(os.path.join(self.temp_dir, "combined_a.wav"), self.sys_vol.get()/100.0, self.mic_vol.get()/100.0)
            
            cmd = ["ffmpeg", "-y", "-i", temp_v]
            if temp_a and os.path.exists(temp_a): 
                cmd += [ "-i", temp_a, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-async", "1", "-shortest"]
            else: 
                cmd += ["-c", "copy"]
            cmd.append(output)
            
            subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.cleanup_temp_files()
        except Exception as e: print(f"Merge error: {e}")
            
    def cleanup_temp_files(self):
        self.audio_recorder.cleanup()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = tempfile.mkdtemp(prefix="screen_recorder_video_")
    
    def show_hotkey_help(self):
        HotkeyHelpDialog.toggle(self.root)

    def register_hotkeys(self):
        keyboard.add_hotkey("alt+s", self.toggle)
        keyboard.add_hotkey("alt+p", self.pause)
        keyboard.add_hotkey("f1", self.show_hotkey_help)

    def detect_mics(self):
        import sounddevice as sd
        try:
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            default_name = default_input['name'] if default_input else None
            
            mics = []
            for device in devices:
                if device['max_input_channels'] > 0:
                    if device['name'] not in mics:
                        mics.append(device['name'])
            
            self.mic_dropdown["values"] = mics
            
            if default_name in mics:
                self.selected_mic.set(default_name)
            elif mics:
                self.selected_mic.set(mics[0])
        except Exception as e:
            print(f"Error detecting mics: {e}")

    def select_region(self):
        sel = RegionSelector(self.root); self.root.wait_window(sel); self.region = sel.region

    def select_save_folder(self):
        folder = filedialog.askdirectory()
        if folder: self.save_dir = folder; self.save_label.config(text=folder)

    def setup_tray(self):
        self.tray_icon = setup_tray(self)

    def hide_to_tray(self): self.root.withdraw()
    def show_window(self): self.root.deiconify(); self.root.lift()
    
    def exit_app(self):
        if self.timer_running or self.paused: self.toggle()
        self.cleanup_temp_files()
        if self.tray_icon: self.tray_icon.stop()
        self.root.destroy()
