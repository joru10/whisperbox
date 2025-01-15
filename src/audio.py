import os
import wave
import pyaudio
import select
import sys
import threading
from array import array
from pydub import AudioSegment
from rich.console import Console
from .config import config

console = Console()

class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.is_paused = False
        self._stop_event = threading.Event()
        
    def _get_loopback_device_index(self):
        """Find the system audio loopback device."""
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            device_name = str(device_info.get('name', '')).lower()
            # Look for BlackHole first, then fall back to other loopback devices
            if 'blackhole' in device_name:
                console.print("[green]Found BlackHole audio device[/green]")
                return i
            elif any(name in device_name for name in ['stereo mix', 'wave out', 'loopback', 'cable']):
                return i
        return None

    def _setup_audio_stream(self):
        """Setup audio stream with appropriate input device."""
        try:
            # Try to get loopback device first
            loopback_index = self._get_loopback_device_index()
            
            if loopback_index is not None and config.audio.capture_system_audio:
                # Create a stream for system audio with non-blocking
                self.system_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=config.audio.channels,
                    rate=config.audio.sample_rate,
                    input=True,
                    input_device_index=loopback_index,
                    frames_per_buffer=config.audio.chunk_size,
                    stream_callback=None,
                    start=False  # Don't start yet
                )
                console.print("[green]System audio capture enabled[/green]")
            else:
                self.system_stream = None
                if config.audio.capture_system_audio:
                    console.print("[yellow]No loopback device found. To capture system audio:[/yellow]")
                    console.print("1. Install BlackHole: brew install blackhole-2ch")
                    console.print("2. Set up a Multi-Output Device in Audio MIDI Setup")
                    console.print("3. Select BlackHole as your system output")

            # Create microphone stream with non-blocking
            self.mic_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=config.audio.channels,
                rate=config.audio.sample_rate,
                input=True,
                frames_per_buffer=config.audio.chunk_size,
                stream_callback=None,
                start=False  # Don't start yet
            )
            
        except Exception as e:
            console.print(f"[red]Error setting up audio streams: {e}[/red]")
            raise

    def start(self):
        """Start recording in a separate thread."""
        self._setup_audio_stream()
        self.is_recording = True
        self._stop_event.clear()
        
        # Start the streams
        self.mic_stream.start_stream()
        if self.system_stream:
            self.system_stream.start_stream()
        
        # Start recording thread
        self.record_thread = threading.Thread(target=self._record)
        self.record_thread.start()
        
    def _mix_audio(self, mic_data, system_data):
        """Mix microphone and system audio."""
        if not system_data:
            return mic_data
            
        # Convert bytes to arrays of signed integers
        mic_audio = array('h', mic_data)
        system_audio = array('h', system_data)
        
        # Adjust system audio volume (increase clarity)
        system_gain = 1.2  # Adjust this value between 1.0-2.0 to find the sweet spot
        
        # Mix with adjusted system audio gain
        mixed = array('h', [
            max(min(
                m + int(s * system_gain),  # Apply gain to system audio
                32767), -32768)
            for m, s in zip(mic_audio, system_audio)
        ])
        
        return mixed.tobytes()
        
    def _record(self):
        """Record audio in chunks."""
        while not self._stop_event.is_set():
            if not self.is_paused:
                try:
                    # Use a timeout when reading
                    if self.mic_stream.is_active():
                        mic_data = self.mic_stream.read(config.audio.chunk_size, exception_on_overflow=False)
                    else:
                        break  # Stream is no longer active
                    
                    # Read from system audio if available
                    system_data = None
                    if self.system_stream and self.system_stream.is_active():
                        system_data = self.system_stream.read(config.audio.chunk_size, exception_on_overflow=False)
                    
                    # Mix the audio if we have both streams
                    if system_data:
                        mixed_data = self._mix_audio(mic_data, system_data)
                        self.frames.append(mixed_data)
                    else:
                        self.frames.append(mic_data)
                        
                except Exception as e:
                    console.print(f"[yellow]Warning in recording thread: {str(e)}[/yellow]")
                    if "Input overflowed" not in str(e):  # Ignore overflow warnings
                        break  # Exit on other errors
                    
        console.print("[yellow]Recording thread stopped[/yellow]")
    
    def stop(self):
        """Stop recording and save to file."""
        if not self.is_recording:
            return
            
        console.print("[yellow]Stopping recording thread...[/yellow]")
        self._stop_event.set()
        
        # Stop streams first
        if hasattr(self, 'mic_stream') and self.mic_stream:
            self.mic_stream.stop_stream()
        if hasattr(self, 'system_stream') and self.system_stream:
            self.system_stream.stop_stream()
        
        # Now join the thread
        if hasattr(self, 'record_thread'):
            self.record_thread.join(timeout=2.0)
            if self.record_thread.is_alive():
                console.print("[red]Warning: Recording thread did not stop cleanly[/red]")
        
        console.print("[yellow]Closing audio streams...[/yellow]")
        if hasattr(self, 'mic_stream') and self.mic_stream:
            self.mic_stream.close()
        if hasattr(self, 'system_stream') and self.system_stream:
            self.system_stream.close()
            
        self.is_recording = False
        console.print("[green]Recording stopped successfully[/green]")
        
    def save(self, output_file):
        """Save recorded audio to file."""
        console.print(f"[yellow]Saving {len(self.frames)} frames to {output_file}[/yellow]")
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(config.audio.channels)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(config.audio.sample_rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        console.print(f"[green]Successfully saved audio to {output_file}[/green]")
        self.frames = []  # Clear frames after saving
        
    def __del__(self):
        """Cleanup PyAudio."""
        self.p.terminate()

def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format."""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")

def list_audio_devices():
    """List all available audio devices."""
    p = pyaudio.PyAudio()
    console.print("\n[bold]Available Audio Devices:[/bold]")
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        console.print(f"\nDevice {i}:")
        console.print(f"  Name: {device_info['name']}")
        console.print(f"  Max Input Channels: {device_info['maxInputChannels']}")
        console.print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
        console.print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")
    
    p.terminate()
