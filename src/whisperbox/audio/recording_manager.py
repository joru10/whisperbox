import os
from datetime import datetime
from rich.console import Console
from .audio import AudioRecorder
from ..core.config import config
from ..ai.transcribe import Shallowgram
from ..ai.transcribe import export_to_markdown
from ..utils.logger import log
from ..utils.utils import create_session_dir
import traceback

console = Console()

class RecordingManager:
    def __init__(self):
        """Initialize the recording manager."""
        from ..core.config import config
        log.debug("RecordingManager initialized with config:")
        log.debug(str(config._config))
        self.recorder = AudioRecorder()
        self.transcriber = Shallowgram()
        self.is_recording = False
        self.is_paused = False
        self.current_recording = None
        self.current_session_dir = None

    def _get_output_filename(self):
        """Generate output filename based on timestamp."""
        try:
            # Get timestamp format, use default if None
            timestamp_format = config.output.timestamp_format
            if timestamp_format is None:
                timestamp_format = "%Y-%m-%d_%H-%M-%S"
            else:
                timestamp_format = timestamp_format.strip('"').strip("'")

            timestamp = datetime.now().strftime(timestamp_format)

            # Create a new session directory if we don't have one
            if not self.current_session_dir:
                self.current_session_dir = create_session_dir()

            # Convert to string and join paths safely
            session_dir = str(self.current_session_dir)
            return os.path.join(session_dir, "recording.wav")

        except Exception as e:
            log.error(f"Error generating filename: {e}")
            # Fallback to basic timestamp format
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not self.current_session_dir:
                self.current_session_dir = create_session_dir()
            session_dir = str(self.current_session_dir)
            return os.path.join(session_dir, "recording.wav")

    def start_recording(self):
        """Start a new recording if not already recording."""
        if self.is_recording:
            log.error("Recording already in progress")
            return

        self.current_recording = self._get_output_filename()

        try:
            self.recorder.start()
            self.is_recording = True
            log.show_recording_status(True, False)
        except Exception as e:
            log.error(f"Error starting recording: {e}")

    def stop_recording(self):
        """Stop the current recording and transcribe it."""
        if not self.is_recording:
            log.error("No recording in progress")
            return

        try:
            log.debug("=== Starting Recording Stop Sequence ===")
            log.debug("Stopping recorder...")
            log.debug("Calling recorder.stop()...")
            self.recorder.stop()

            log.debug("Recorder stopped, now saving...")
            log.info("Saving recording...")
            log.debug(f"Saving to file: {self.current_recording}")
            self.recorder.save(self.current_recording)

            log.debug("Recording saved successfully")
            self.is_recording = False
            self.is_paused = False
            log.save(f"Recording saved to: {self.current_recording}")

            log.debug("=== Starting Transcription Process ===")
            # Transcribe the recording
            log.transcribing("Starting transcription...")
            try:
                # Get model name with robust fallback
                model_name = config.get_with_retry("transcription", "whisper", "model")
                if not model_name:
                    from ..core.config import DEFAULT_CONFIG
                    default_model = DEFAULT_CONFIG["transcription"]["whisper"]["model"]
                    log.warning(f"Could not get model from config after retries, using default: {default_model}")
                    model_name = default_model
                    # Update config with default model
                    if "transcription" not in config._config:
                        config._config["transcription"] = {}
                    if "whisper" not in config._config["transcription"]:
                        config._config["transcription"]["whisper"] = {}
                    config._config["transcription"]["whisper"]["model"] = model_name
                    config.save()
                    log.debug(f"Updated config with default model: {model_name}")
                
                log.debug(f"Using Whisper model: {model_name}")
                result = self.transcriber.transcribe(
                    self.current_recording,
                    model=model_name,
                    full_analysis=True
                )

                if not result:
                    log.error("Transcription returned no results")
                    return

                log.debug("Saving results to markdown...")

                # Save processed results to markdown
                self._save_results_to_markdown(result)

                log.debug("=== Recording Process Complete ===")
                # Return the path for potential further processing
                return self.current_recording

            except Exception as e:
                log.error(f"Error during transcription: {e}")
                log.debug(traceback.format_exc())

        except Exception as e:
            log.error(f"Error stopping recording: {e}")
            log.debug(traceback.format_exc())

    def _save_results_to_markdown(self, result):
        """Save transcription results to markdown files in the session directory."""
        if not self.current_session_dir:
            log.error("No session directory available")
            return

        try:
            # Convert to string first to handle Path objects safely
            session_dir = str(self.current_session_dir)
            
            # Save main transcript with timestamps
            transcript_path = os.path.join(session_dir, "transcript.md")
            with open(transcript_path, "w") as f:
                f.write(f"# Transcript\n\n")
                f.write(result["text"])
            log.save(f"Transcript saved to: {transcript_path}")
            
            # Save clean text version without timestamps
            text_path = os.path.join(session_dir, "transcript_text.md")
            with open(text_path, "w") as f:
                # Remove timestamps using a simple regex
                import re
                clean_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}\]', '', result["text"])
                # Remove extra whitespace and empty lines
                clean_text = "\n".join(line.strip() for line in clean_text.split("\n") if line.strip())
                f.write(clean_text)
            log.save(f"Clean text saved to: {text_path}")
            
        except Exception as e:
            log.error(f"Error saving markdown files: {e}")
            log.debug(traceback.format_exc())

    def toggle_pause(self):
        """Toggle recording pause state."""
        if not self.is_recording:
            log.warning("No recording in progress")
            return

        self.is_paused = not self.is_paused
        self.recorder.is_paused = self.is_paused
        log.show_recording_status(True, self.is_paused)
