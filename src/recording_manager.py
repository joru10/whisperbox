import os
from datetime import datetime
from rich.console import Console
from .audio import AudioRecorder
from .config import config
from .transcribe import Shallowgram

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
            f"recording_{timestamp}.{config.audio.format}"
        )

    def start_recording(self):
        """Start a new recording if not already recording."""
        if self.is_recording:
            console.print("[yellow]Recording is already in progress[/yellow]")
            return
            
        self.current_recording = self._get_output_filename()
        os.makedirs(config.output.audio_directory, exist_ok=True)
        
        try:
            self.recorder.start()
            self.is_recording = True
            recording_color = getattr(config.display.colors, "recording", "yellow")
            console.print(f"[{recording_color}]Recording started...[/]")
        except Exception as e:
            error_color = getattr(config.display.colors, "error", "red")
            console.print(f"[{error_color}]Error starting recording: {e}[/]")

    def stop_recording(self):
        """Stop the current recording and transcribe it."""
        if not self.is_recording:
            console.print("[yellow]No recording in progress[/yellow]")
            return

        try:
            console.print("[yellow]Stopping recorder...[/yellow]")
            self.recorder.stop()
            console.print("[yellow]Saving recording...[/yellow]")
            self.recorder.save(self.current_recording)
            self.is_recording = False
            self.is_paused = False
            console.print(f"[{config.display.colors.success}]Recording saved to: {self.current_recording}[/]")
            
            # Transcribe the recording
            console.print("[yellow]Starting transcription process...[/yellow]")
            try:
                console.print(f"[yellow]Using Whisper model: {config.transcription.whisper.model}[/yellow]")
                result = self.transcriber.transcribe(self.current_recording, full_analysis=True)
                
                if not result:
                    console.print("[red]Transcription returned no results[/red]")
                    return
                    
                console.print("[green]Transcription complete! Displaying results:[/green]")
                
                # Display results
                from .transcribe import display_rich_output
                display_rich_output(
                    result['text'],
                    result['summary'],
                    result['sentiment'],
                    result['intent'],
                    result['topics']
                )
                
            except Exception as e:
                console.print(f"[red]Error during transcription: {str(e)}[/red]")
                import traceback
                console.print(f"[red]{traceback.format_exc()}[/red]")
            
        except Exception as e:
            console.print(f"[{config.display.colors.error}]Error stopping recording: {str(e)}[/]")

    def toggle_pause(self):
        """Toggle recording pause state."""
        if not self.is_recording:
            console.print("[yellow]No recording in progress[/yellow]")
            return

        self.is_paused = not self.is_paused
        self.recorder.is_paused = self.is_paused
        status = "paused" if self.is_paused else "resumed"
        console.print(f"[{config.display.colors.system}]Recording {status}[/]") 