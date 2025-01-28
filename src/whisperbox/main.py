import os
import time
import logging
import argparse
from threading import Thread
from .core.config import config
from .audio.recording_manager import RecordingManager
from .utils.logger import log
from .core.setup import setup
from .audio.audio import list_audio_devices
from .utils.utils import (
    is_first_run,
    get_transcript_path,
    get_app_dir,
    reveal_in_file_manager,
)
from .utils.model_utils import check_whisper_model
from .ai.process_transcript import process_transcript
from .ai.ai_service import AIService
from .utils.profile_parser import load_profile_yaml, get_available_profiles
from .utils.profile_executor import run_profile_actions
import traceback
from pathlib import Path


def cli_mode(ai_provider=None, debug=False, profile=None):
    """Run the application in CLI mode."""
    try:
        # Initialize logging
        log.debug_mode = debug or config.system.debug_mode

        logging.basicConfig(
            level=logging.INFO if not config.system.debug_mode else logging.DEBUG
        )
        logger = logging.getLogger(__name__)

        # Check for required Whisper model
        check_whisper_model()

        # Print header and instructions
        log.print_header()
        log.info("\nSimple Recording Controls:")
        log.info("- Press Enter to start recording")
        log.info("- Press Enter again to stop recording")
        log.info("- Press Ctrl+C to quit\n")

        # Initialize recording manager
        recording_manager = RecordingManager()

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
                return
            except Exception as e:
                log.error(f"Unexpected error loading profile: {str(e)}")
                if debug:
                    log.debug(traceback.format_exc())
                return

        try:
            while True:
                try:
                    if not recording_manager.is_recording:
                        input("Press Enter to start recording...")
                        log.recording("Starting recording...")
                        recording_manager.start_recording()
                    else:
                        input("Recording in progress. Press Enter to stop...")
                        log.recording("Stopping recording...")
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

                except EOFError:
                    break

        except KeyboardInterrupt:
            log.warning("\nReceived keyboard interrupt, shutting down...")
            if recording_manager.is_recording:
                recording_manager.stop_recording()

        log.info("\nShutting down...")
        if recording_manager.is_recording:
            recording_manager.stop_recording()
        log.success("Goodbye!")

    except Exception as e:
        log.error(f"Unexpected error in cli_mode: {str(e)}")
        if debug:
            log.debug(traceback.format_exc())




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

        if args.devices:
            list_audio_devices()
            return

        if args.open:
            reveal_in_file_manager(get_app_dir())
            return

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
