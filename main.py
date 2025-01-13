from src.config import config
from src.hotkeys import HotkeyManager
import logging

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO if not config.system.debug_mode else logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Initialize hotkey manager
    hotkey_manager = HotkeyManager(config)

    # Define your handler functions
    def start_recording():
        logger.info("Starting recording...")
        # Your recording start logic here

    def stop_recording():
        logger.info("Stopping recording...")
        # Your recording stop logic here

    def pause_recording():
        logger.info("Toggling recording pause...")
        # Your pause/resume logic here

    def quit_app():
        logger.info("Quitting application...")
        hotkey_manager.stop()
        # Your cleanup logic here

    # Register handlers
    hotkey_manager.register_handler("start_recording", start_recording)
    hotkey_manager.register_handler("stop_recording", stop_recording)
    hotkey_manager.register_handler("pause_recording", pause_recording)
    hotkey_manager.register_handler("quit", quit_app)

    # Start listening for hotkeys
    logger.info("Starting hotkey listener... Press ctrl+shift+q to quit")
    hotkey_manager.start()

if __name__ == "__main__":
    main()
