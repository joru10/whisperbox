import os
from datetime import datetime
from rich.console import Console
from .audio import AudioRecorder
from .config import config
from .transcribe import Shallowgram
from .logger import log
import traceback

console = Console()


class RecordingManager:
    def __init__(self):
        self.is_recording = False
        self.is_paused = False
        self.current_recording = None
        self.recorder = AudioRecorder()
        self.transcriber = Shallowgram()

    def _get_output_filename(self):
        """Generate output filename based on timestamp."""
        timestamp = datetime.now().strftime(config.output.timestamp_format)
        return os.path.join(
            config.output.audio_directory,
            f"recording_{timestamp}.{config.audio.format}",
        )

    def start_recording(self):
        """Start a new recording if not already recording."""
        if self.is_recording:
            log.error("Recording already in progress")
            return

        self.current_recording = self._get_output_filename()
        os.makedirs(config.output.audio_directory, exist_ok=True)

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
            log.status("Stopping recorder...")
            self.recorder.stop()
            log.status("Saving recording...")
            self.recorder.save(self.current_recording)
            self.is_recording = False
            self.is_paused = False
            log.success(f"Recording saved to: {self.current_recording}")
            

            # Transcribe the recording
            log.transcribing("Starting transcription...")
            try:
                log.info(f"Using Whisper model: {config.transcription.whisper.model}")
                result = self.transcriber.transcribe(self.current_recording, full_analysis=True)

                if not result:
                    log.error("Transcription returned no results")
                    return
                    
                log.success("Transcription complete! Displaying results:")
                

                # Display results
                from .transcribe import display_rich_output

                display_rich_output(
                    result["text"],
                    result["summary"],
                    result["sentiment"],
                    result["intent"],
                    result["topics"],
                )
                
                # Return the path for potential further processing
                return self.current_recording
                
            except Exception as e:
                log.error(f"Error during transcription: {e}")
                log.debug(traceback.format_exc())
            
        except Exception as e:
            log.error(f"Error stopping recording: {e}")
            log.debug(traceback.format_exc())

    def toggle_pause(self):
        """Toggle recording pause state."""
        if not self.is_recording:
            log.warning("No recording in progress")
            return

        self.is_paused = not self.is_paused
        self.recorder.is_paused = self.is_paused
        log.show_recording_status(True, self.is_paused) 

