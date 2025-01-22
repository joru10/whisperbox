import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from threading import Thread
from .recording_manager import RecordingManager
from .hotkeys import HotkeyManager
from .config import config
import time

class TranscriberApp(toga.App):
    def __init__(self):
        super().__init__('Hacker Transcriber', 'com.hackertranscriber')
        self.recording_manager = RecordingManager()
        self.hotkey_manager = HotkeyManager(config)
        self.is_recording = False
        self.recording_start_time = None

    def startup(self):
        # Create main window
        self.main_window = toga.MainWindow(title=self.name)

        # Status label with emoji
        self.status_label = toga.Label(
            '⏹️ Ready to Record',
            style=Pack(padding=(0, 5))
        )

        # Timer label
        self.timer_label = toga.Label(
            '00:00',
            style=Pack(padding=(0, 5))
        )

        # Recording button
        self.record_button = toga.Button(
            '🎙️ Start Recording',
            on_press=self.toggle_recording,
            style=Pack(padding=5)
        )

        # Pause button
        self.pause_button = toga.Button(
            '⏸️ Pause',
            on_press=self.toggle_pause,
            enabled=False,
            style=Pack(padding=5)
        )

        # Audio source info
        self.mic_label = toga.Label(
            'Microphone: Default',
            style=Pack(padding=(0, 5))
        )
        self.system_label = toga.Label(
            'System Audio: BlackHole',
            style=Pack(padding=(0, 5))
        )

        # Create main box
        main_box = toga.Box(
            children=[
                self.status_label,
                self.timer_label,
                toga.Box(
                    children=[self.record_button, self.pause_button],
                    style=Pack(direction=ROW, padding=5)
                ),
                self.mic_label,
                self.system_label
            ],
            style=Pack(
                direction=COLUMN,
                padding=10,
                alignment='center'
            )
        )

        # Add the content to the main window
        self.main_window.content = main_box

        # Start hotkey listener in a separate thread
        self.setup_hotkeys()
        
        # Show the main window
        self.main_window.show()

        # Start the timer update thread
        self.timer_thread = Thread(target=self.update_timer, daemon=True)
        self.timer_thread.start()

    def setup_hotkeys(self):
        """Setup global hotkeys."""
        self.hotkey_manager.register_handler("start_recording", self.toggle_recording)
        self.hotkey_manager.register_handler("pause_recording", self.toggle_pause)
        Thread(target=self.hotkey_manager.start, daemon=True).start()

    def toggle_recording(self, widget=None):
        """Toggle recording state."""
        if not self.is_recording:
            # Start recording
            self.recording_manager.start_recording()
            self.is_recording = True
            self.recording_start_time = time.time()
            self.record_button.label = '⏹️ Stop Recording'
            self.status_label.text = '⏺️ Recording'
            self.pause_button.enabled = True
        else:
            # Stop recording
            self.recording_manager.stop_recording()
            self.is_recording = False
            self.recording_start_time = None
            self.record_button.label = '🎙️ Start Recording'
            self.status_label.text = '⏹️ Ready to Record'
            self.pause_button.enabled = False
            self.pause_button.label = '⏸️ Pause'

    def toggle_pause(self, widget=None):
        """Toggle pause state."""
        if self.is_recording:
            self.recording_manager.toggle_pause()
            if self.recording_manager.is_paused:
                self.status_label.text = '⏸️ Paused'
                self.pause_button.label = '▶️ Resume'
            else:
                self.status_label.text = '⏺️ Recording'
                self.pause_button.label = '⏸️ Pause'

    def update_timer(self):
        """Update the timer label."""
        while True:
            if self.is_recording and self.recording_start_time:
                elapsed = time.time() - self.recording_start_time
                time_str = time.strftime("%M:%S", time.gmtime(elapsed))
                self.timer_label.text = time_str
            time.sleep(0.1)

def main():
    app = TranscriberApp()
    return app.main_loop() 