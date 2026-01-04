import subprocess
import threading
import tempfile
import os
import time
import wave
import numpy as np
from pydub import AudioSegment
import atexit
import sounddevice as sd

try:
    import pyaudiowpatch as pyaudio
    WASAPI_AVAILABLE = True
except ImportError:
    try:
        import pyaudio
        WASAPI_AVAILABLE = False
    except ImportError:
        pyaudio = None
        WASAPI_AVAILABLE = False

SYSTEM_AUDIO_DELAY_MS = 240

class FFmpegProcessManager:
    def __init__(self):
        self.processes = []
        atexit.register(self.cleanup_all)
    
    def start_process(self, cmd, description=""):
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.processes.append({'process': process, 'description': description})
            return process
        except Exception:
            return None
    
    def stop_process(self, process):
        if process and process.poll() is None:
            try:
                process.stdin.write(b"q")
                process.stdin.flush()
                process.wait(timeout=3)
            except:
                try:
                    process.terminate()
                except:
                    pass
            finally:
                self.processes = [p for p in self.processes if p['process'] != process]
    
    def cleanup_all(self):
        for item in self.processes[:]:
            self.stop_process(item['process'])

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self.system_audio_thread = None
        self.mic_audio_thread = None
        self.system_audio_process = None
        self.temp_dir = tempfile.mkdtemp(prefix="screen_recorder_audio_")
        self.system_segments = []
        self.mic_segments = []
        self.sample_rate = 48000
        self.ffmpeg_manager = FFmpegProcessManager()
        
    def start_recording(self, system_audio_enabled, mic_audio_enabled):
        """Start recording audio streams."""
        self.is_recording = True
        self.is_paused = False
        
        print(f"\n[AUDIO START] System: {system_audio_enabled}, Mic: {mic_audio_enabled}")
        
        if system_audio_enabled:
            print("[DEBUG] Starting system audio thread...")
            self.system_audio_thread = threading.Thread(target=self._record_system_audio, daemon=True)
            self.system_audio_thread.start()
            print("[DEBUG] System audio thread started")
        
        if mic_audio_enabled:
            print("[DEBUG] Starting mic audio thread...")
            self.mic_audio_thread = threading.Thread(target=self._record_mic_audio, daemon=True)
            self.mic_audio_thread.start()
            print("[DEBUG] Mic audio thread started")
            
    def _record_system_audio(self):
        """Capture system audio using WASAPI loopback."""
        print("[SYSTEM AUDIO] Thread started")
        
        try:
            if not WASAPI_AVAILABLE or pyaudio is None:
                print("[ERROR] pyaudiowpatch not available - cannot capture system audio")
                return
            
            device_info = None
            p = pyaudio.PyAudio()
            
            for i in range(p.get_device_count()):
                dev_info = p.get_device_info_by_index(i)
                if dev_info.get('isLoopback', False) or 'loopback' in dev_info.get('name', '').lower():
                    device_info = dev_info
                    break
            
            if not device_info:
                print("[ERROR] No loopback device found")
                p.terminate()
                return
            
            print(f"[SYSTEM AUDIO] Using device: {device_info['name']}")
            print(f"[SYSTEM AUDIO] Sample rate: {device_info['defaultSampleRate']}")
            
            channels = 2
            chunk_size = 1024
            
            while self.is_recording:
                if not self.is_paused:
                    segment_idx = len(self.system_segments)
                    output_file = os.path.join(self.temp_dir, f"system_audio_{segment_idx:04d}.wav")
                    
                    print(f"[SYSTEM AUDIO] Starting segment {segment_idx}")
                    
                    audio_data = []
                    
                    try:
                        stream = p.open(
                            format=pyaudio.paInt16,
                            channels=channels,
                            rate=int(device_info['defaultSampleRate']),
                            input=True,
                            input_device_index=device_info['index'],
                            frames_per_buffer=chunk_size
                        )
                        
                        print(f"[SYSTEM AUDIO] Stream opened, recording...")
                        
                        while not self.is_paused and self.is_recording:
                            try:
                                data = stream.read(chunk_size, exception_on_overflow=False)
                                audio_data.append(data)
                            except Exception as e:
                                print(f"[SYSTEM AUDIO] Read error: {e}")
                                break
                        
                        stream.stop_stream()
                        stream.close()
                        
                        print(f"[SYSTEM AUDIO] Stopped segment {segment_idx}, chunks: {len(audio_data)}")
                        
                        if audio_data:
                            with wave.open(output_file, 'wb') as wf:
                                wf.setnchannels(channels)
                                wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                                wf.setframerate(int(device_info['defaultSampleRate']))
                                wf.writeframes(b''.join(audio_data))
                            
                            file_size = os.path.getsize(output_file)
                            print(f"[SYSTEM AUDIO] Saved {output_file}: {file_size} bytes")
                            
                            if file_size > 1000:
                                self.system_segments.append(output_file)
                            else:
                                print(f"[SYSTEM AUDIO] Segment too small, skipping")
                        else:
                            print(f"[SYSTEM AUDIO] No data captured")
                            
                    except Exception as e:
                        print(f"[SYSTEM AUDIO] Stream error: {e}")
                
                time.sleep(0.05)
            
            p.terminate()
            print("[SYSTEM AUDIO] Thread ended")
            
        except Exception as e:
            print(f"[SYSTEM AUDIO] Fatal error: {e}")
            
    def _record_mic_audio(self):
        """Record microphone audio using sounddevice."""
        print("[MIC AUDIO] Thread started")
        
        try:
            while self.is_recording:
                if not self.is_paused:
                    segment_idx = len(self.mic_segments)
                    output_file = os.path.join(self.temp_dir, f"mic_audio_{segment_idx:04d}.wav")
                    
                    print(f"[MIC AUDIO] Starting segment {segment_idx}")
                    
                    audio_data = []
                    
                    def callback(indata, frames, time_info, status):
                        if status:
                            print(f"[MIC AUDIO] Status: {status}")
                        if not self.is_paused:
                            audio_data.append(indata.copy())
                    
                    try:
                        with sd.InputStream(channels=2, samplerate=self.sample_rate, callback=callback):
                            print(f"[MIC AUDIO] Recording...")
                            while not self.is_paused and self.is_recording:
                                time.sleep(0.05)
                        
                        print(f"[MIC AUDIO] Stopped segment {segment_idx}, chunks: {len(audio_data)}")
                        
                        if audio_data:
                            self._save_mic_audio_data(audio_data, output_file)
                            file_size = os.path.getsize(output_file)
                            print(f"[MIC AUDIO] Saved {output_file}: {file_size} bytes")
                            self.mic_segments.append(output_file)
                        else:
                            print(f"[MIC AUDIO] No data captured")
                            
                    except Exception as e:
                        print(f"[MIC AUDIO] Stream error: {e}")
                        
                time.sleep(0.05)
                
            print("[MIC AUDIO] Thread ended")
            
        except Exception as e:
            print(f"[MIC AUDIO] Fatal error: {e}")
            
    def _save_mic_audio_data(self, audio_data, filename):
        if audio_data:
            audio_array = np.concatenate(audio_data, axis=0)
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes((audio_array * 32767).astype(np.int16).tobytes())
    
    def pause(self): self.is_paused = True
    def resume(self): self.is_paused = False
    
    def stop(self):
        self.is_recording = False
        self.is_paused = True
        if self.system_audio_process:
            self.ffmpeg_manager.stop_process(self.system_audio_process)
        if self.system_audio_thread: self.system_audio_thread.join(timeout=1)
        if self.mic_audio_thread: self.mic_audio_thread.join(timeout=1)
    
    def combine_audio_segments(self, output_path, sys_volume=1.0, mic_volume=1.0):
        """Combine system and mic audio segments by padding shorter tracks with silence."""
        try:
            system_combined = None
            mic_combined = None
            
            if self.system_segments:
                for segment in self.system_segments:
                    if os.path.exists(segment) and os.path.getsize(segment) > 0:
                        audio = AudioSegment.from_wav(segment)
                        audio = AudioSegment.silent(duration=SYSTEM_AUDIO_DELAY_MS) + audio
                        if sys_volume != 1.0:
                            gain = 20 * np.log10(max(sys_volume, 0.01))
                            audio = audio.apply_gain(gain)
                        system_combined = audio if system_combined is None else system_combined + audio

            if self.mic_segments:
                for segment in self.mic_segments:
                    if os.path.exists(segment) and os.path.getsize(segment) > 0:
                        audio = AudioSegment.from_wav(segment)
                        if mic_volume != 1.0:
                            gain = 20 * np.log10(max(mic_volume, 0.01))
                            audio = audio.apply_gain(gain)
                        mic_combined = audio if mic_combined is None else mic_combined + audio

            final_audio = None
            
            if system_combined and mic_combined:
                sys_samples = np.array(system_combined.get_array_of_samples()).astype(np.float32)
                mic_samples = np.array(mic_combined.get_array_of_samples()).astype(np.float32)
                max_samples = max(len(sys_samples), len(mic_samples))
                sys_samples = np.pad(sys_samples, (0, max_samples - len(sys_samples)), 'constant')
                mic_samples = np.pad(mic_samples, (0, max_samples - len(mic_samples)), 'constant')
                
                mixed_samples = sys_samples + mic_samples
                
                max_val = np.abs(mixed_samples).max()
                if max_val > 32767:
                    mixed_samples = mixed_samples * (32767 / max_val)
                
                final_audio = AudioSegment(
                    mixed_samples.astype(np.int16).tobytes(),
                    frame_rate=system_combined.frame_rate,
                    sample_width=system_combined.sample_width,
                    channels=system_combined.channels
                )
                
            elif system_combined:
                final_audio = system_combined
            elif mic_combined:
                final_audio = mic_combined

            if final_audio:
                normalized_audio = final_audio.normalize(headroom=0.1)
                normalized_audio.export(output_path, format="wav")
                print(f"Combined audio saved to: {output_path}")
                return output_path
                
        except Exception as e:
            print(f"Error combining audio segments: {e}")
        
        return None
    
    def cleanup(self):
        import shutil
        self.ffmpeg_manager.cleanup_all()
        if os.path.exists(self.temp_dir): shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.system_segments = []; self.mic_segments = []
        self.temp_dir = tempfile.mkdtemp(prefix="screen_recorder_audio_")
