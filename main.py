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
from src.utils.utils import is_first_run, create_app_directory_structure, get_transcript_path, get_app_dir, reveal_in_file_manager
from src.ai.process_transcript import process_transcript
from src.ai.ai_service import AIService
from src.utils.profile_parser import load_profile_yaml, get_available_profiles
from src.utils.profile_executor import run_profile_actions
import traceback


def cli_mode(ai_provider=None, debug=False, profile=None):
    """Run the application in CLI mode."""
    try:
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
            try:
                profile_data = load_profile_yaml(profile)
                log.info(f"Using profile: {profile_data.get('name')}")
            except ValueError as e:
                # Profile errors are already logged with friendly messages
                # Just exit gracefully
                return
            except Exception as e:
                log.error(f"Unexpected error loading profile: {str(e)}")
                if debug:
                    log.debug(traceback.format_exc())
                return

        # Define handler functions
        def start_recording():
            log.recording("Starting recording...")
            recording_manager.start_recording()

        def stop_recording_and_process():
            log.recording("Stopping recording...")
            log.info("(Due to a temporary bug, you may need to press a key to continue if it gets stuck here)")
            audio_file_path = recording_manager.stop_recording()
            transcript_path = get_transcript_path(audio_file_path)

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
                
                time.sleep(1)
                log.done("All done! Ready for the next recording 🫡")

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
        hotkey_manager.register_handler("stop_recording", stop_recording_and_process)
        hotkey_manager.register_handler("pause_recording", pause_recording)

        # Start hotkey listener in a separate thread
        hotkey_thread = Thread(target=hotkey_manager.start, daemon=True)
        hotkey_thread.start()

        try:
            # Main loop - just wait for keyboard interrupt
            while True:
                try:
                    time.sleep(0.1)  # Reduce CPU usage
                except (EOFError, KeyboardInterrupt):
                    break

        except KeyboardInterrupt:
            log.warning("\nReceived keyboard interrupt, shutting down...")
            if recording_manager.is_recording:
                recording_manager.stop_recording()
            hotkey_manager.stop()

        log.info("\nShutting down...")
        if recording_manager.is_recording:
            recording_manager.stop_recording()
        hotkey_manager.stop()
        log.success("Goodbye!")

    except Exception as e:
        log.error(f"Unexpected error in cli_mode: {str(e)}")
        if debug:
            log.debug(traceback.format_exc())


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
    """Main entry point for the application."""
    args = None  # Initialize args outside try block
    try:
        parser = argparse.ArgumentParser(
            description="WhisperBox - Audio Recording and Transcription Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run initial setup
  wb --setup

  # Record and transcribe a meeting with Ollama
  wb --ai-provider ollama --profile meeting_summary

  # Record and create a blog post with OpenAI
  wb --ai-provider openai --profile meeting_to_blogpost

  # List and configure audio devices
  wb --devices


For more information, visit: https://github.com/ToolUse/whisperbox
"""
        )

        # Setup and configuration group
        setup_group = parser.add_argument_group('Setup and Configuration')
        setup_group.add_argument(
            "--setup",
            action="store_true",
            help="Run the initial setup process (configure AI, audio devices, etc.)",
        )
        setup_group.add_argument(
            "--config",
            action="store_true",
            help="Open the configuration file in your default editor",
        )
        setup_group.add_argument(
            "--devices",
            action="store_true",
            help="List and select audio input devices (microphone and system audio)",
        )
        setup_group.add_argument(
            "--open",
            action="store_true",
            help="Open the WhisperBox data folder in Documents",
        )

        # Recording and Processing group
        processing_group = parser.add_argument_group('Recording and Processing')
        processing_group.add_argument(
            "--ai-provider",
            type=str,
            choices=['ollama', 'groq', 'anthropic', 'openai'],
            help="AI provider to use for processing transcripts",
        )
        processing_group.add_argument(
            "--profile",
            type=str,
            help="Profile to use for processing (e.g. meeting_summary, meeting_to_blogpost)",
        )

        # Debug group
        debug_group = parser.add_argument_group('Debugging')
        debug_group.add_argument(
            "--debug", 
            action="store_true", 
            help="Enable debug logging for troubleshooting",
        )

        args = parser.parse_args()

        # Initialize logging
        log.debug_mode = args.debug or config.system.debug_mode
        logging.basicConfig(
            level=logging.INFO if not config.system.debug_mode else logging.DEBUG
        )

        # Handle special commands first
        if args.setup or is_first_run():
            setup()
            return

        if args.config:
            os.system(f"open {config._config_path}")
            return

        if args.devices:
            list_audio_devices()
            return

        if args.open:
            reveal_in_file_manager(get_app_dir())
            return

        # Run in CLI mode if no special commands
        cli_mode(
            ai_provider=args.ai_provider,
            debug=args.debug,
            profile=args.profile,
        )

    except KeyboardInterrupt:
        log.warning("\nReceived keyboard interrupt, shutting down...")
    except Exception as e:
        log.error(f"An error occurred: {str(e)}")
        if args and args.debug:  # Check if args exists and debug is True
            log.debug(traceback.format_exc())



if __name__ == "__main__":
    main()
