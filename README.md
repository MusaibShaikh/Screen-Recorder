# Minimal Screen Recorder (Windows)

A lightweight Windows screen recorder focused on speed, simplicity, and unrestricted recording.

Built as an alternative to OBS and freemium screen recorders when you just want to open an app and start recording — without overlays, scenes, or artificial time limits.

---

## Why This Exists

Most screen recorders fall into one of two categories:

- **Too complex** (OBS)
- **Too restrictive** (time limits, watermarks, subscriptions)

This project was built to solve both.

---

## Key Features

- One-click screen recording
- Fullscreen or region capture
- Simultaneous **system audio + microphone** recording
- Pause / resume recording
- Global hotkeys
- Minimal UI (no scenes, no profiles)
- System tray integration
- Hardware-accelerated encoding when available (NVIDIA / Intel / AMD)

---

## Audio Handling (The Hard Part)

System audio is captured using **WASAPI loopback** on Windows and mixed with microphone input in post-processing.

This approach:

- Avoids FFmpeg sync issues
- Allows independent volume control
- Handles pause / resume reliably
- Produces a clean final audio track

---

## Tech Stack

- Python
- Tkinter (UI)
- FFmpeg (video capture & encoding)
- WASAPI loopback (system audio)
- sounddevice + PyAudio (mic & audio capture)
- NumPy + pydub (audio mixing)
- pystray (system tray integration)

---

## Requirements (Source Users)

- Windows 10 or newer
- Python 3.9+
- FFmpeg installed and available in PATH

---

## Usage (Source)

```bash
python run.py
```

---

## Global Hotkeys

| Shortcut | Action |
|--------|--------|
| Alt + S | Start / Stop recording |
| Alt + P | Pause / Resume |
| F1 | Show hotkey help |

---

## Output

Recordings are saved as MP4 files with:

- H.264 video
- AAC audio
- Hardware encoding when available

---

## Limitations

- Windows-only (WASAPI dependency)
- Keyframe-based video segments during pause / resume
- Not intended as a full video editor

---

## Motivation

This project prioritizes **usability over features**.

If you want scenes, filters, streaming, or plugins — use OBS.  
If you want to record your screen immediately, this tool exists.

---

## License

MIT
