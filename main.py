import os
import time
import logging
import argparse
from threading import Thread
from src.core.config import config
from src.utils.hotkeys import HotkeyManager
from src.audio.recording_manager import RecordingManager
from src.utils.logger import log
from src.core.setup import setup
from src.audio.audio import list_audio_devices
from src.utils.utils import is_first_run, create_app_directory_structure
from src.ai.process import process_transcript, get_available_processors
from src.ai.ai_service import AIService


def cli_mode(process_method=None, ai_provider=None):
    """Run the application in CLI mode."""
    # Initialize logging
    log.debug_mode = config.system.debug_mode

    logging.basicConfig(
        level=logging.INFO if not config.system.debug_mode else logging.DEBUG
    )
    logger = logging.getLogger(__name__)
    
    # Print header and instructions
    log.print_header()
    log.print_instructions()

    # Initialize managers
    recording_manager = RecordingManager()
    hotkey_manager = HotkeyManager(config)

    # Initialize AI service if provider specified
    if ai_provider:
        try:
            ai_service = AIService(service_type=ai_provider)
            logger.info(f"Using AI provider: {ai_provider}")
        except ValueError as e:
            logger.error(f"Error initializing AI service: {e}")
            return



    # Define handler functions
    def start_recording():
        log.recording("Starting recording...")
        recording_manager.start_recording()

    def stop_recording():
        log.recording("Stopping recording...")
        transcript_path = recording_manager.stop_recording()

        # If --process flag is set and we have a transcript, process it
        if process_method and transcript_path:
            logger.info(f"Processing transcript with method: {process_method}...")
            process_transcript(
                transcript_path, method=process_method, ai_provider=ai_provider
            )


        # If --process flag is set and we have a transcript, process it
        if process_method and transcript_path:
            logger.info(f"Processing transcript with method: {process_method}...")
            process_transcript(
                transcript_path, method=process_method, ai_provider=ai_provider
            )

    def pause_recording():
        log.recording("Toggling recording pause...")
        recording_manager.toggle_pause()

    def quit_app():
        log.info("Quitting application...")
        if recording_manager.is_recording:
            recording_manager.stop_recording()
        hotkey_manager.stop()
        return True  # Signal to exit

    # Register handlers
    hotkey_manager.register_handler("start_recording", start_recording)
    hotkey_manager.register_handler("stop_recording", stop_recording)
    hotkey_manager.register_handler("pause_recording", pause_recording)

    # Start hotkey listener in a separate thread
    hotkey_thread = Thread(target=hotkey_manager.start, daemon=True)
    hotkey_thread.start()

    # Command handlers
    command_handlers = {
        'help': lambda: (log.print_help(), input(), log.print_header(), log.print_instructions()),
        'config': lambda: (os.system(f"open {config._config_path}"), log.print_header(), log.print_instructions()),
        'devices': lambda: (list_audio_devices(), log.print_instructions()),
        'quit': quit_app
    }

    try:
        # # Start UI update thread
        # ui_thread = Thread(target=update_ui, daemon=True)
        # ui_thread.start()

        # Main command loop
        running = True
        while running:
            try:
                command = input().strip().lower()
                if command in config.commands:
                    action = config.commands[command]['action']
                    if action in command_handlers:
                        result = command_handlers[action]()
                        if result:  # For quit handler
                            running = False
                            break
            except (EOFError, KeyboardInterrupt):
                running = False
                quit_app()
                break

    except KeyboardInterrupt:
        log.warning("\nReceived keyboard interrupt, shutting down...")
        if recording_manager.is_recording:
            recording_manager.stop_recording()
        hotkey_manager.stop()

    log.warning("\nShutting down...")
    if recording_manager.is_recording:
        recording_manager.stop_recording()
    hotkey_manager.stop()
    log.success("Goodbye!")

def app_mode():
    """Run the application in GUI mode."""
    try:
        from src.ui.app import TranscriberApp
        app = TranscriberApp()
        return app.main_loop()
    except ImportError as e:
        log.error("Could not load GUI mode. Make sure toga is installed.")
        log.error(f"Error details: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="WhisperBox - Record and transcribe audio")
    parser.add_argument('--app', action='store_true', help='Launch in GUI mode')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices')
    parser.add_argument('--setup', action='store_true', help='Run setup wizard')

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
    
    # Create basic directory structure
    create_app_directory_structure()
    
    # Run setup if it's the first time or explicitly requested
    if is_first_run() or args.setup:
        setup()
        return 0  # Exit after setup to ensure clean config loading
    
    if args.list_devices:

        list_audio_devices()
    elif args.app:
        return app_mode()
    else:
        cli_mode(process_method=args.process, ai_provider=args.ai_provider)

if __name__ == "__main__":
    main()

