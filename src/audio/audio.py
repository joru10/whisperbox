import os
import wave
import pyaudio
import select
import sys
import threading
from array import array
from pydub import AudioSegment
from ..utils.logger import log
from ..core.config import config
from rich.prompt import Prompt
from rich.console import Console
import yaml
from InquirerPy import inquirer
import traceback


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
            device_name = str(device_info.get("name", "")).lower()
            if "blackhole" in device_name:
                log.debug("Found BlackHole audio device")
                return i
            elif any(
                name in device_name
                for name in ["stereo mix", "wave out", "loopback", "cable"]
            ):
                return i
        return None

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
        log.debug("Stopping recording thread...")

        # First stop the streams to prevent any more data from being read
        log.debug("Stopping audio streams...")
        if hasattr(self, "mic_stream") and self.mic_stream:
            log.debug("Stopping microphone stream...")
            self.mic_stream.stop_stream()
            log.debug("Microphone stream stopped")
        if hasattr(self, "system_stream") and self.system_stream:
            log.debug("Stopping system stream...")
            self.system_stream.stop_stream()
            log.debug("System stream stopped")

        # Now set the stop event
        log.debug("Setting stop event...")
        self._stop_event.set()

        # Now join the thread with a shorter timeout
        if hasattr(self, "record_thread"):
            log.debug("Waiting for recording thread to finish...")
            self.record_thread.join(timeout=0.5)  # Reduced timeout to 500ms
            if self.record_thread.is_alive():
                log.warning(
                    "Recording thread still alive after timeout, proceeding anyway"
                )
            else:
                log.debug("Recording thread joined successfully")

        log.debug("Closing audio streams...")
        if hasattr(self, "mic_stream") and self.mic_stream:
            log.debug("Closing microphone stream...")
            self.mic_stream.close()
            log.debug("Microphone stream closed")
        if hasattr(self, "system_stream") and self.system_stream:
            log.debug("Closing system stream...")
            self.system_stream.close()
            log.debug("System stream closed")

        self.is_recording = False
        log.debug("=== Audio Recorder Stop Complete ===")
        log.success("Recording stopped successfully")

    def save(self, output_file):
        """Save recorded audio to file."""
        log.debug(f"Saving {len(self.frames)} frames to {output_file}")
        wf = wave.open(output_file, "wb")
        wf.setnchannels(self.mic_channels)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(config.audio.sample_rate)
        wf.writeframes(b"".join(self.frames))
        wf.close()
        self.frames = []  # Clear frames after saving

    def __del__(self):
        """Cleanup PyAudio."""
        self.p.terminate()


def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format."""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")


def get_input_devices():
    """Get list of input devices only."""
    p = pyaudio.PyAudio()
    input_devices = []

    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if int(device_info["maxInputChannels"]) > 0:  # Cast to int to fix type error
            input_devices.append(
                {
                    "index": i,
                    "name": device_info["name"],
                    "channels": device_info["maxInputChannels"],
                    "sample_rate": device_info["defaultSampleRate"],
                }
            )

    p.terminate()
    return input_devices


def select_audio_device():
    """Interactive audio device selection."""
    devices = get_input_devices()

    if not devices:
        log.error("No input devices found!")
        return

    # Create device choices with formatted strings
    choices = [
        f"{d['name']} (Channels: {d['channels']}, Sample Rate: {d['sample_rate']})"
        for d in devices
    ]

    # Show device selection prompt
    selection = inquirer.select(
        message="Select input device:",
        choices=choices,
        default=None,
    ).execute()

    # Get the selected device (extract name before the parentheses)
    selected_name = selection.split(" (")[0]
    selected_device = next(d for d in devices if d["name"] == selected_name)

    # Update config using proper config management
    try:
        if "audio" not in config._config:
            config._config["audio"] = {}
        if "devices" not in config._config["audio"]:
            config._config["audio"]["devices"] = {}

        config._config["audio"]["devices"]["microphone"] = selected_device["name"]
        config.save()

        log.success(f"Updated config: Using {selected_device['name']} as input device")
        print("")

    except Exception as e:
        log.error(f"Error updating config: {e}")


def list_audio_devices():
    """List available input devices and handle selection."""
    select_audio_device()
