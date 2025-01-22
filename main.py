from src.config import config
from src.hotkeys import HotkeyManager
from src.recording_manager import RecordingManager
from src.logger import log
from src.setup import setup
from src.audio import list_audio_devices
from src.utils import is_first_run, create_app_directory_structure
import argparse
import time
from threading import Thread
import os

def cli_mode():
    """Run the application in CLI mode."""
    # Initialize logging
    log.debug_mode = config.system.debug_mode
    
    # Print header and instructions
    log.print_header()
    log.print_instructions()

    # Initialize managers
    recording_manager = RecordingManager()
    hotkey_manager = HotkeyManager(config)

    # Define handler functions
    def start_recording():
        log.recording("Starting recording...")
        recording_manager.start_recording()

    def stop_recording():
        log.recording("Stopping recording...")
        recording_manager.stop_recording()

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

    log.warning("\nShutting down...")
    if recording_manager.is_recording:
        recording_manager.stop_recording()
    hotkey_manager.stop()
    log.success("Goodbye!")

def app_mode():
    """Run the application in GUI mode."""
    try:
        from src.app import TranscriberApp
        app = TranscriberApp()
        return app.main_loop()
    except ImportError as e:
        print("[red]Error: Could not load GUI mode. Make sure toga is installed.[/red]")
        print(f"Error details: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="WhisperBox - Record and transcribe audio")
    parser.add_argument('--app', action='store_true', help='Launch in GUI mode')
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices')
    parser.add_argument('--setup', action='store_true', help='Run setup wizard')
    args = parser.parse_args()
    
    # Create basic directory structure
    create_app_directory_structure()
    
    # Run setup if it's the first time or explicitly requested
    if is_first_run() or args.setup:
        setup()
        return 0  # Exit after setup to ensure clean config loading
    
    if args.list_devices:
        from src.audio import list_audio_devices
        list_audio_devices()
    elif args.app:
        return app_mode()
    else:
        cli_mode()

if __name__ == "__main__":
    main()
