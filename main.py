from src.config import config
from src.hotkeys import HotkeyManager
from src.recording_manager import RecordingManager
from src.ui import TranscriberUI
from src.process import process_transcript, get_available_processors
from src.ai_service import AIService
from rich.console import Console
import logging
import argparse
from rich.live import Live
import time
from threading import Thread

console = Console()


def main(process_method=None, ai_provider=None):
    # Setup logging
    logging.basicConfig(
        level=logging.INFO if not config.system.debug_mode else logging.DEBUG
    )
    logger = logging.getLogger(__name__)

    # Initialize managers
    recording_manager = RecordingManager()
    hotkey_manager = HotkeyManager(config)
    ui = TranscriberUI()

    # Initialize AI service if provider specified
    if ai_provider:
        try:
            ai_service = AIService(service_type=ai_provider)
            logger.info(f"Using AI provider: {ai_provider}")
        except ValueError as e:
            logger.error(f"Error initializing AI service: {e}")
            return

    # UI update thread
    def update_ui():
        while not hotkey_manager._stop_event.is_set():
            ui.update_content()
            time.sleep(0.1)

    # Define handler functions
    def start_recording():
        logger.info("Starting recording...")
        recording_manager.start_recording()
        ui.start_recording()

    def stop_recording():
        logger.info("Stopping recording...")
        transcript_path = recording_manager.stop_recording()
        ui.stop_recording()

        # If --process flag is set and we have a transcript, process it
        if process_method and transcript_path:
            logger.info(f"Processing transcript with method: {process_method}...")
            process_transcript(
                transcript_path, method=process_method, ai_provider=ai_provider
            )

    def pause_recording():
        logger.info("Toggling recording pause...")
        recording_manager.toggle_pause()
        ui.toggle_pause()

    def quit_app():
        logger.info("Quitting application...")
        if recording_manager.is_recording:
            recording_manager.stop_recording()
        hotkey_manager.stop()

    # Register handlers
    hotkey_manager.register_handler("start_recording", start_recording)
    hotkey_manager.register_handler("stop_recording", stop_recording)
    hotkey_manager.register_handler("pause_recording", pause_recording)
    hotkey_manager.register_handler("quit", quit_app)

    # Start UI
    with Live(ui.layout, refresh_per_second=10, screen=True):
        try:
            # Start UI update thread
            ui_thread = Thread(target=update_ui, daemon=True)
            ui_thread.start()

            # Start hotkey listener
            hotkey_manager.start()

        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Received keyboard interrupt, shutting down...[/yellow]"
            )
            if recording_manager.is_recording:
                recording_manager.stop_recording()
            hotkey_manager.stop()
            console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list-devices", action="store_true", help="List available audio devices"
    )
    parser.add_argument(
        "--process",
        choices=get_available_processors(),
        help="Process transcript with specified method after recording",
    )
    parser.add_argument(
        "--ai-provider",
        choices=["ollama", "groq", "anthropic", "openai"],
        default="ollama",
        help="Specify which AI provider to use",
    )
    args = parser.parse_args()

    if args.list_devices:
        from src.audio import list_audio_devices

        list_audio_devices()
    else:
        main(process_method=args.process, ai_provider=args.ai_provider)
