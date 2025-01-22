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
from src.ai.process_transcript import process_transcript
from src.ai.ai_service import AIService
from src.utils.profile_parser import load_profile_yaml, get_available_profiles
from src.utils.profile_executor import run_profile_actions


def cli_mode(ai_provider=None, debug=False, profile=None):
    """Run the application in CLI mode."""
    # Initialize logging
    log.debug_mode = debug or config.system.debug_mode

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
        except ValueError as e:
            logger.error(f"Error initializing AI service: {e}")
            return

    # If the user passes in a profile name, load it
    profile_data = {}
    if profile:
        profile_data = load_profile_yaml(profile)
        logging.info(f"Loaded profile: {profile_data.get('name')}")

    # Define handler functions
    def start_recording():
        log.recording("Starting recording...")
        recording_manager.start_recording()

    def stop_recording():
        log.recording("Stopping recording...")
        transcript_path = recording_manager.stop_recording()

        if transcript_path and profile:
            logger.info(f"Processing transcript with profile: {profile}...")
            # run AI
            processed_output = process_transcript(
                transcript_path,
                ai_provider=ai_provider,
                prompt=profile_data.get("prompt", ""),
            )
            # run the actions
            run_profile_actions(profile_data, processed_output)

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
        "help": lambda: (
            log.print_help(),
            input(),
            log.print_header(),
            log.print_instructions(),
        ),
        "config": lambda: (
            os.system(f"open {config._config_path}"),
            log.print_header(),
            log.print_instructions(),
        ),
        "devices": lambda: (list_audio_devices(), log.print_instructions()),
        "quit": quit_app,
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
                    action = config.commands[command]["action"]
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
    parser = argparse.ArgumentParser(
        description="WhisperBox - Record and transcribe audio"
    )
    parser.add_argument("--app", action="store_true", help="Launch in GUI mode")
    parser.add_argument(
        "--list-devices", action="store_true", help="List available audio devices"
    )
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--ai-provider",
        choices=["ollama", "groq", "anthropic", "openai"],
        default="ollama",
        help="Specify which AI provider to use",
    )
    parser.add_argument(
        "--profile",
        help="Specify a YAML profile to use for processing",
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available profiles"
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
    elif args.list_profiles:
        profiles = get_available_profiles()
        if profiles:
            print("Available profiles:")
            for profile in profiles:
                print(f"  - {profile}")
        else:
            print("No profiles found")
        return 0
    elif args.app:
        return app_mode()
    else:
        cli_mode(
            ai_provider=args.ai_provider,
            debug=args.debug,
            profile=args.profile,
        )


if __name__ == "__main__":
    main()
