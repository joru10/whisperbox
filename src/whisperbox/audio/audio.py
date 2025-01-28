import os
import sys
import time
import wave
import yaml
import pyaudio
import select
import platform
import traceback
import threading
from array import array
import sounddevice as sd
from pydub import AudioSegment
from ..utils.logger import log
from rich.prompt import Prompt
from rich.console import Console
from ..core.config import config
from InquirerPy.prompts.list import ListPrompt


def get_platform():
    """Get the current operating system platform."""
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    return "unknown"


def get_system_audio_device_index():
    """Get system audio capture device index based on platform."""
    platform = get_platform()
    
    if platform == "mac":
        # On macOS, look for BlackHole
        return _get_blackhole_device_index()
    elif platform == "linux":
        # On Linux, look for common loopback devices
        return _get_linux_loopback_device_index()
    elif platform == "windows":
        # On Windows, look for stereo mix or similar
        return _get_windows_loopback_device_index()
    return None


def _get_blackhole_device_index():
    """Find BlackHole audio device on macOS."""
    p = pyaudio.PyAudio()
    try:
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = str(device_info.get("name", "")).lower()
            if "blackhole" in device_name:
                log.debug("Found BlackHole audio device")
                return i
        return None
    finally:
        p.terminate()


def _get_linux_loopback_device_index():
    """Find system audio loopback device on Linux."""
    p = pyaudio.PyAudio()
    try:
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = str(device_info.get("name", "")).lower()
            if any(name in device_name for name in ["pulse", "monitor", "loopback"]):
                return i
        return None
    finally:
        p.terminate()


def _get_windows_loopback_device_index():
    """Find system audio loopback device on Windows."""
    p = pyaudio.PyAudio()
    try:
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = str(device_info.get("name", "")).lower()
            if any(name in device_name for name in ["stereo mix", "wave out", "cable", "virtual"]):
                return i
        return None
    finally:
        p.terminate()


def print_system_audio_setup_instructions():
    """Print platform-specific instructions for system audio capture setup."""
    platform = get_platform()
    
    if platform == "mac":
        log.warning("To capture system audio on macOS:")
        log.info("1. Install BlackHole: brew install blackhole-2ch")
        log.info("2. Set up a Multi-Output Device in Audio MIDI Setup")
        log.info("3. Select BlackHole as your system output")
        log.info("\nFor detailed instructions, visit: https://github.com/ExistentialAudio/BlackHole")
    elif platform == "linux":
        log.warning("To capture system audio on Linux:")
        log.info("Option 1 - Using PulseAudio:")
        log.info("1. Install PulseAudio (if not already installed)")
        log.info("2. Load module-loopback:")
        log.info("   pactl load-module module-loopback latency_msec=1")
        log.info("3. Use pavucontrol to manage audio routing")
        log.info("\nOption 2 - Using JACK:")
        log.info("1. Install JACK: sudo apt-get install jackd2")
        log.info("2. Install QjackCtl for GUI control")
        log.info("3. Configure JACK to capture system audio")
    elif platform == "windows":
        log.warning("To capture system audio on Windows:")
        log.info("Option 1 - Using Stereo Mix (if available):")
        log.info("1. Right-click the speaker icon in the system tray")
        log.info("2. Open Sound settings > Recording")
        log.info("3. Right-click in the device list and enable 'Show Disabled Devices'")
        log.info("4. Enable 'Stereo Mix' if available")
        log.info("\nOption 2 - Using VB-Cable (recommended):")
        log.info("1. Download VB-Cable from: https://vb-audio.com/Cable/")
        log.info("2. Install and restart your computer")
        log.info("3. Set CABLE Output as your default playback device")
        log.info("4. Select CABLE Input as your recording device in WhisperBox")


def get_system_audio_devices():
    """Get list of potential system audio capture devices."""
    p = pyaudio.PyAudio()
    system_devices = []
    
    try:
        for i in range(p.get_device_count()):
            try:
                device_info = p.get_device_info_by_index(i)
                device_name = str(device_info.get("name", "")).lower()
                max_inputs = int(device_info.get("maxInputChannels", 0))
                
                # Skip devices with no input channels
                if max_inputs == 0:
                    continue
                    
                # Check if device is a potential system audio capture device
                platform = get_platform()
                is_system_device = False
                
                if platform == "mac" and "blackhole" in device_name:
                    is_system_device = True
                elif platform == "linux" and any(name in device_name for name in ["pulse", "monitor", "loopback"]):
                    is_system_device = True
                elif platform == "windows" and any(name in device_name for name in ["stereo mix", "wave out", "cable", "virtual"]):
                    is_system_device = True
                    
                if is_system_device:
                    system_devices.append({
                        'name': device_info.get("name"),
                        'index': i,
                        'channels': max_inputs,
                        'sample_rate': int(device_info.get("defaultSampleRate", 44100))
                    })
                    
            except Exception as e:
                log.debug(f"Error processing device {i}: {e}")
                continue
                
        return system_devices
    finally:
        p.terminate()


def select_system_audio_device():
    """Interactive system audio device selection."""
    devices = get_system_audio_devices()
    platform = get_platform()
    
    if not devices:
        log.warning("No system audio capture devices found!")
        print_system_audio_setup_instructions()
        return None
        
    # Create device choices with formatted strings
    choices = []
    for d in devices:
        choice_str = (
            f"{d['name']}\n"
            f"   Channels: {d['channels']}, Sample Rate: {d['sample_rate']}Hz"
        )
        choices.append(choice_str)
        
    # Add option to disable system audio capture
    choices.append("Disable system audio capture")
    
    # Show device selection prompt
    prompt = ListPrompt(
        message="Select system audio capture device (or disable):",
        choices=choices
    )
    selection = prompt.execute()
    
    if selection == "Disable system audio capture":
        config._config["audio"]["capture_system_audio"] = False
        config.save()
        log.info("System audio capture disabled")
        return None
        
    # Get the selected device (extract name before the newline)
    selected_name = selection.split("\n")[0]
    selected_device = next(d for d in devices if d["name"] == selected_name)
    
    # Update config
    try:
        if "audio" not in config._config:
            config._config["audio"] = {}
        if "devices" not in config._config["audio"]:
            config._config["audio"]["devices"] = {}
            
        config._config["audio"]["devices"]["system"] = {
            "name": selected_device["name"],
            "index": selected_device["index"],
            "channels": selected_device["channels"],
            "sample_rate": selected_device["sample_rate"]
        }
        config._config["audio"]["capture_system_audio"] = True
        config.save()
        
        log.success(
            f"Updated config: Using {selected_device['name']} for system audio capture\n"
            f"Settings - Channels: {selected_device['channels']}, "
            f"Sample Rate: {selected_device['sample_rate']}Hz"
        )
        
        return selected_device["index"]
        
    except Exception as e:
        log.error(f"Error updating config: {e}")
        log.debug(traceback.format_exc())
        return None


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
        # Use the new platform-specific detection
        return get_system_audio_device_index()

    def _setup_audio_stream(self):
        """Setup audio stream with appropriate input device."""
        try:
            log.debug("Starting audio stream setup...")
            log.debug(
                f"Current config - Channels: {config.audio.channels}, Rate: {config.audio.sample_rate}"
            )

            # Try to get loopback device first
            loopback_index = self._get_loopback_device_index()
            self.system_stream = None

            # Get default input device info first
            try:
                default_input = self.p.get_default_input_device_info()
                log.debug(f"Default input device: {default_input['name']}")
                log.debug(f"Max input channels: {default_input['maxInputChannels']}")
                self.mic_channels = min(
                    int(default_input["maxInputChannels"]), config.audio.channels
                )
                log.debug(f"Using {self.mic_channels} channels for microphone")
            except Exception as e:
                log.error(f"Error getting default input device info: {e}")
                raise

            # Create microphone stream with non-blocking
            self.mic_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.mic_channels,
                rate=config.audio.sample_rate,
                input=True,
                frames_per_buffer=config.audio.chunk_size,
                stream_callback=None,
                start=False,
            )
            log.debug("Microphone stream created successfully")

            # Only try system audio setup after mic is working
            if loopback_index is not None and config.audio.capture_system_audio:
                try:
                    device_info = self.p.get_device_info_by_index(loopback_index)
                    system_channels = min(
                        int(device_info["maxInputChannels"]), config.audio.channels
                    )
                    log.debug(f"System audio device: {device_info['name']}")
                    log.debug(f"Using {system_channels} channels for system audio")

                    self.system_stream = self.p.open(
                        format=pyaudio.paInt16,
                        channels=system_channels,
                        rate=config.audio.sample_rate,
                        input=True,
                        input_device_index=loopback_index,
                        frames_per_buffer=config.audio.chunk_size,
                        stream_callback=None,
                        start=False,
                    )
                    log.debug("System audio stream created successfully")
                except Exception as e:
                    self.system_stream = None
                    log.warning(f"Failed to initialize system audio capture: {e}")

            if self.system_stream is None and config.audio.capture_system_audio:
                log.warning(
                    "No loopback device found or failed to initialize. To capture system audio:"
                )
                log.info("1. Install BlackHole: brew install blackhole-2ch")
                log.info("2. Set up a Multi-Output Device in Audio MIDI Setup")
                log.info("3. Select BlackHole as your system output")

        except Exception as e:
            log.error(f"Error setting up audio streams: {e}")
            log.debug(traceback.format_exc())
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
        mic_audio = array("h", mic_data)
        system_audio = array("h", system_data)

        # Adjust system audio volume (increase clarity)
        system_gain = 1.2  # Adjust this value between 1.0-2.0 to find the sweet spot

        # Mix with adjusted system audio gain
        mixed = array(
            "h",
            [
                max(
                    min(m + int(s * system_gain), 32767),  # Apply gain to system audio
                    -32768,
                )
                for m, s in zip(mic_audio, system_audio)
            ],
        )

        return mixed.tobytes()

    def _record(self):
        """Record audio in chunks."""
        log.debug("Starting recording thread")
        while not self._stop_event.is_set():
            if not self.is_paused:
                try:
                    # Check if streams are still active
                    if not self.mic_stream or not self.mic_stream.is_active():
                        log.debug("Microphone stream no longer active")
                        break

                    # Use a timeout when reading to make the thread more responsive to stop events
                    try:
                        mic_data = self.mic_stream.read(
                            config.audio.chunk_size, exception_on_overflow=False
                        )
                    except Exception as e:
                        log.debug(f"Error reading from mic stream: {e}")
                        break

                    # Read from system audio if available
                    system_data = None
                    if self.system_stream and self.system_stream.is_active():
                        try:
                            system_data = self.system_stream.read(
                                config.audio.chunk_size, exception_on_overflow=False
                            )
                        except Exception as e:
                            log.debug(f"Error reading from system stream: {e}")
                            system_data = None

                    # Mix the audio if we have both streams
                    if system_data:
                        mixed_data = self._mix_audio(mic_data, system_data)
                        self.frames.append(mixed_data)
                    else:
                        self.frames.append(mic_data)

                except Exception as e:
                    log.warning(f"Warning in recording thread: {str(e)}")
                    if "Input overflowed" not in str(e):  # Ignore overflow warnings
                        log.debug(f"Recording thread error: {str(e)}")
                        break  # Exit on other errors

            # Add a small sleep to make the thread more responsive to stop events
            if self._stop_event.wait(0.001):  # 1ms wait
                log.debug("Stop event detected in recording thread")
                break

        log.debug("Recording thread exiting")
        log.debug("Recording thread stopped")

    def stop(self):
        """Stop recording and save to file."""
        if not self.is_recording:
            log.debug("Stop called but not recording")
            return

        log.debug("=== Audio Recorder Stop Sequence ===")
        
        # First set the stop event to prevent any new data from being read
        log.debug("Setting stop event...")
        self._stop_event.set()
        
        # Give a short pause to let the recording thread notice the stop event
        time.sleep(0.1)
        
        # Now stop the streams
        log.debug("Stopping audio streams...")
        try:
            if hasattr(self, "mic_stream") and self.mic_stream:
                log.debug("Stopping microphone stream...")
                self.mic_stream.stop_stream()
                log.debug("Microphone stream stopped")
        except Exception as e:
            log.warning(f"Error stopping mic stream: {e}")
            
        try:
            if hasattr(self, "system_stream") and self.system_stream:
                log.debug("Stopping system stream...")
                self.system_stream.stop_stream()
                log.debug("System stream stopped")
        except Exception as e:
            log.warning(f"Error stopping system stream: {e}")

        # Now join the thread with a shorter timeout
        if hasattr(self, "record_thread"):
            log.debug("Waiting for recording thread to finish...")
            try:
                self.record_thread.join(timeout=1)
                if self.record_thread.is_alive():
                    log.warning("Recording thread still alive after timeout")
                else:
                    log.debug("Recording thread joined successfully")
            except Exception as e:
                log.warning(f"Error joining record thread: {e}")

        # Close the streams
        log.debug("Closing audio streams...")
        try:
            if hasattr(self, "mic_stream") and self.mic_stream:
                log.debug("Closing microphone stream...")
                self.mic_stream.close()
                self.mic_stream = None
                log.debug("Microphone stream closed")
        except Exception as e:
            log.warning(f"Error closing mic stream: {e}")
            
        try:
            if hasattr(self, "system_stream") and self.system_stream:
                log.debug("Closing system stream...")
                self.system_stream.close()
                self.system_stream = None
                log.debug("System stream closed")
        except Exception as e:
            log.warning(f"Error closing system stream: {e}")

        self.is_recording = False
        log.debug("=== Audio Recorder Stop Complete ===")
        log.success("Recording stopped successfully")

    def save(self, output_file):
        """Save recorded audio to file and convert to 16kHz mono WAV."""
        if not self.frames:
            log.error("No frames to save")
            return
            
        log.debug(f"Saving {len(self.frames)} frames to {output_file}")
        
        # Create temp file path
        temp_file = output_file + ".temp.wav"
        
        try:
            # Save initial WAV file
            with wave.open(temp_file, "wb") as wf:
                wf.setnchannels(self.mic_channels)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(config.audio.sample_rate)
                wf.writeframes(b"".join(self.frames))
            
            # Convert to 16kHz mono WAV using a context manager
            audio = None
            try:
                audio = AudioSegment.from_wav(temp_file)
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                audio.export(output_file, format="wav")
            finally:
                # Explicitly delete AudioSegment object
                del audio
                
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
            log.debug(f"Successfully converted audio to 16kHz mono WAV: {output_file}")
            
        except Exception as e:
            log.error(f"Error saving audio: {e}")
            # If conversion fails, try to keep the original file
            if os.path.exists(temp_file):
                try:
                    os.rename(temp_file, output_file)
                    log.warning("Keeping original audio format")
                except Exception as rename_error:
                    log.error(f"Error saving original audio: {rename_error}")
        finally:
            # Clean up frames and ensure temp file is removed
            self.frames = []
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as cleanup_error:
                    log.error(f"Error cleaning up temp file: {cleanup_error}")
                    
    def __del__(self):
        """Cleanup PyAudio."""
        try:
            if hasattr(self, 'p'):
                self.p.terminate()
        except Exception as e:
            # Silently fail on cleanup
            pass


def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format."""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")


def get_input_devices():
    """Get list of available input devices."""
    try:
        devices = sd.query_devices()
        input_devices = []
        
        for i, device in enumerate(devices):
            try:
                # Convert device info to a dictionary
                device_info = dict(device)
                max_inputs = int(device_info['max_input_channels'])
                
                if max_inputs > 0:
                    input_devices.append({
                        'name': str(device_info['name']),
                        'index': i,
                        'channels': max_inputs,
                        'sample_rate': float(device_info['default_samplerate']),
                        'input_latency': float(device_info['default_low_input_latency']) * 1000,  # Convert to ms
                        'is_default': i == sd.default.device[0]
                    })
            except (KeyError, ValueError, TypeError) as e:
                log.debug(f"Skipping device {i} due to error: {e}")
                continue
        
        return input_devices
    except Exception as e:
        log.error(f"Error getting input devices: {e}")
        return []


def select_audio_device():
    """Interactive audio device selection with enhanced configuration."""
    devices = get_input_devices()

    if not devices:
        log.error("No input devices found!")
        return

    # Create device choices with formatted strings
    choices = []
    for d in devices:
        default_marker = " (Default)" if d["is_default"] else ""
        choice_str = (
            f"{d['name']}{default_marker}\n"
            f"   Channels: {d['channels']}, Sample Rate: {int(d['sample_rate'])}Hz, "
            f"Latency: {d['input_latency']:.3f}ms"
        )
        choices.append(choice_str)

    # Show device selection prompt
    prompt = ListPrompt(message="Select input device:", choices=choices)
    selection = prompt.execute()

    # Get the selected device (extract name before the newline)
    selected_name = selection.split("\n")[0].replace(" (Default)", "")
    selected_device = next(d for d in devices if d["name"] == selected_name)

    # Update config with detailed device information
    try:
        if "audio" not in config._config:
            config._config["audio"] = {}
        if "devices" not in config._config["audio"]:
            config._config["audio"]["devices"] = {}

        # Update the microphone configuration with all available details
        # Convert float values to integers where needed
        config._config["audio"]["devices"]["microphone"] = {
            "name": selected_device["name"],
            "index": int(selected_device["index"]),  # Convert to int
            "channels": int(selected_device["channels"]),  # Convert to int
            "sample_rate": int(selected_device["sample_rate"]),  # Convert to int
            "input_latency": selected_device["input_latency"],  # Keep as float
            "is_default": selected_device["is_default"],
        }

        # Update the main audio settings to match the device's native capabilities
        config._config["audio"]["channels"] = int(selected_device["channels"])  # Convert to int
        config._config["audio"]["sample_rate"] = int(selected_device["sample_rate"])  # Convert to int

        config.save()

        log.success(
            f"Updated config: Using {selected_device['name']}\n"
            f"Native settings - Channels: {int(selected_device['channels'])}, "  # Convert to int
            f"Sample Rate: {int(selected_device['sample_rate'])}Hz"  # Convert to int
        )
        print("")

    except Exception as e:
        log.error(f"Error updating config: {e}")
        log.debug(traceback.format_exc())


def list_audio_devices():
    """List available input devices and handle selection."""
    select_audio_device()
