from pynput import keyboard
from typing import Callable, Dict
import logging
from threading import Event

class HotkeyManager:
    def __init__(self, config):
        """Initialize the hotkey manager with configuration."""
        self.config = config
        self.handlers: Dict[str, Callable] = {}
        self._setup_logging()
        self._stop_event = Event()
        self._current_keys = set()
        self._listener = None

    def _setup_logging(self):
        """Setup logging for the hotkey manager."""
        self.logger = logging.getLogger(__name__)
        if self.config.system.debug_mode:
            self.logger.setLevel(logging.DEBUG)

    def _parse_hotkey(self, hotkey_str: str) -> frozenset:
        """Convert hotkey string to frozenset of keys."""
        return frozenset(hotkey_str.lower().split('+'))

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register a handler function for a specific hotkey action."""
        if not hasattr(self.config, 'hotkeys'):
            self.logger.error("No hotkey configuration found")
            return

        hotkey = self.config.hotkeys.get(action)
        if not hotkey:
            self.logger.error(f"No hotkey configured for action: {action}")
            return

        hotkey_combo = self._parse_hotkey(hotkey)
        self.handlers[str(hotkey_combo)] = handler  # Convert frozenset to string
        self.logger.debug(f"Registered hotkey {hotkey} for action {action}")

    def _on_press(self, key):
        """Handle key press events."""
        try:
            # Convert key to string representation
            key_str = key.char if hasattr(key, 'char') else key.name
            self._current_keys.add(key_str.lower())
            
            current_combo = str(frozenset(self._current_keys))  # Convert to string
            if current_combo in self.handlers:
                try:
                    self.handlers[current_combo]()
                except Exception as e:
                    self.logger.error(f"Error executing handler: {e}")
        except AttributeError:
            pass

    def _on_release(self, key) -> None:
        """Handle key release events."""
        try:
            # Convert key to string representation
            key_str = key.char if hasattr(key, 'char') else key.name
            self._current_keys.discard(key_str.lower())
            
            # Check for quit combination
            quit_combo = self._parse_hotkey(self.config.hotkeys.quit)
            if quit_combo.issubset(self._current_keys):
                self.stop()
        except AttributeError:
            pass

    def start(self) -> None:
        """Start listening for hotkeys."""
        self.logger.info("Hotkey manager started")
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        """Stop listening for hotkeys and clean up."""
        if self._listener:
            self._listener.stop()
            self._stop_event.set()  # Set the stop event
        self.logger.info("Hotkey manager stopped")
