import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from threading import Thread
from ..audio.recording_manager import RecordingManager
from ..utils.hotkeys import HotkeyManager
from ..core.config import config
from ..utils.utils import get_app_dir, get_profiles_dir
from ..utils.profile_parser import get_available_profiles, load_profile_yaml
import time
import os

class HomeScreen(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=COLUMN, padding=10))
        self.app = app
        
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

        # Profile selector
        profiles_box = toga.Box(style=Pack(direction=ROW, padding=5))
        profiles_box.add(toga.Label('Profile:', style=Pack(padding=(0, 5))))
        
        # Get available profiles
        self.profiles = get_available_profiles()
        self.profile_selection = toga.Selection(
            items=self.profiles,
            on_select=self.on_profile_selected,
            style=Pack(flex=1)
        )
        profiles_box.add(self.profile_selection)
        
        # Refresh profiles button
        self.refresh_profiles_button = toga.Button(
            '🔄',
            on_press=self.refresh_profiles,
            style=Pack(padding=(0, 5))
        )
        profiles_box.add(self.refresh_profiles_button)
        
        # Add profiles box
        self.add(profiles_box)

        # Recording button
        self.record_button = toga.Button(
            '🎙️ Start Recording',
            on_press=lambda widget: self.app.record_command.action(widget),
            style=Pack(padding=5)
        )

        # Pause button
        self.pause_button = toga.Button(
            '⏸️ Pause',
            on_press=lambda widget: self.app.pause_command.action(widget),
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

        # Add all widgets to the box
        self.add(self.status_label)
        self.add(self.timer_label)
        self.add(toga.Box(
            children=[self.record_button, self.pause_button],
            style=Pack(direction=ROW, padding=5)
        ))
        self.add(self.mic_label)
        self.add(self.system_label)
        
        # Load initial profile if available
        if self.profiles:
            self.profile_selection.value = self.profiles[0]
            self.on_profile_selected(None)

    def refresh_profiles(self, widget=None):
        """Refresh the list of available profiles."""
        self.profiles = get_available_profiles()
        self.profile_selection.items = self.profiles
        if self.profiles:
            self.profile_selection.value = self.profiles[0]
            self.on_profile_selected(None)
        else:
            self.app.main_window.info_dialog(
                'No Profiles Found',
                f'No profile files found in {get_profiles_dir()}'
            )

    def on_profile_selected(self, widget):
        """Handle profile selection."""
        if not self.profile_selection.value:
            return
            
        try:
            profile = load_profile_yaml(self.profile_selection.value)
            self.app.current_profile = profile
            # Update status to show selected profile
            self.status_label.text = f'⏹️ Ready to Record - {profile.get("name", self.profile_selection.value)}'
        except Exception as e:
            self.app.main_window.error_dialog(
                'Profile Error',
                f'Error loading profile: {str(e)}'
            )
            # Reset profile selection
            if self.profiles and self.profile_selection.value != self.profiles[0]:
                self.profile_selection.value = self.profiles[0]

class FileViewerScreen(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=ROW, padding=0, flex=1))
        self.app = app
        self.current_file = None
        
        # Create a split view with flex to fill space
        self.split_container = toga.SplitContainer(style=Pack(flex=1))
        
        # Left side - Tree view for folders
        self.tree = toga.Tree(
            headings=['Name'],
            accessors=['name'],
            style=Pack(flex=1, width=250)
        )
        self.tree.on_select = self.on_file_selected
        
        # Right side container
        self.right_container = toga.Box(style=Pack(flex=1, direction=COLUMN))
        
        # File path and rename controls
        self.file_header = toga.Box(style=Pack(direction=ROW, padding=5))
        self.file_label = toga.TextInput(
            readonly=False,  # Always editable
            style=Pack(flex=1, padding=(0, 5))
        )
        self.rename_button = toga.Button(
            '💾 Save Name',
            on_press=self.rename_file,  # Directly call rename_file
            enabled=False,
            style=Pack(padding=(0, 5))
        )
        self.file_header.add(self.file_label)
        self.file_header.add(self.rename_button)
        
        # Editor toolbar
        self.toolbar = toga.Box(style=Pack(direction=ROW, padding=5))
        self.save_button = toga.Button(
            '💾 Save',
            on_press=self.save_file,
            enabled=False,
            style=Pack(padding=(0, 5))
        )
        self.toolbar.add(self.save_button)
        
        # Text view for file contents
        self.content_view = toga.MultilineTextInput(
            style=Pack(flex=1),
            readonly=False,  # Make it editable
            on_change=self.on_content_changed
        )
        
        # Add components to right container
        self.right_container.add(self.file_header)
        self.right_container.add(self.toolbar)
        self.right_container.add(self.content_view)
        
        # Set up split container with better proportions
        self.split_container.content = [(self.tree, 0.25), (self.right_container, 0.75)]
        
        # Add the split container to fill the entire box
        self.add(self.split_container)
        
        # Load initial files
        self.refresh_files()
    
    def refresh_files(self):
        """Refresh the file tree with current contents of app directory."""
        app_dir = get_app_dir()
        data = self._build_tree_data(app_dir)
        self.tree.data = toga.sources.TreeSource(
            accessors=['name', 'full_path'],
            data=data
        )
    
    def _build_tree_data(self, root_path):
        """Build tree data structure for the given root path."""
        try:
            items = []
            for entry in sorted(os.listdir(root_path)):
                if entry.startswith('.'):  # Skip hidden files
                    continue
                    
                item_path = os.path.join(root_path, entry)
                rel_path = os.path.relpath(item_path, get_app_dir())
                
                if os.path.isdir(item_path):
                    # For directories, recursively get children
                    children = self._build_tree_data(item_path)
                    if children:  # Only add non-empty directories
                        items.append(({
                            "name": entry,
                            "full_path": rel_path
                        }, children))
                else:
                    # For files, add as leaf node
                    items.append(({
                        "name": entry,
                        "full_path": rel_path
                    }, None))
            return items
        except Exception as e:
            print(f"Error loading directory {root_path}: {e}")
            return []
    
    def _is_text_file(self, file_path):
        """Check if the file is a viewable/editable text file."""
        text_extensions = {'.txt', '.md', '.yaml', '.yml', '.json', '.py', '.js', '.html', '.css', '.sh', '.log'}
        return os.path.splitext(file_path)[1].lower() in text_extensions
    
    def _format_file_content(self, file_path, content):
        """Format the file content based on its type."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in {'.md', '.markdown'}:
            # Add some basic markdown formatting hints
            if not content.strip():
                return "# New Markdown File\n\nStart writing here..."
        elif ext in {'.yaml', '.yml'}:
            # Add YAML formatting hints
            if not content.strip():
                return "# YAML Configuration\n\nkey: value\nlist:\n  - item1\n  - item2"
        
        return content
    
    def on_content_changed(self, widget):
        """Handle content changes in the editor."""
        if self.current_file:
            self.save_button.enabled = True
    
    def save_file(self, widget):
        """Save the current file."""
        if not self.current_file:
            return
            
        try:
            with open(self.current_file, 'w') as f:
                f.write(self.content_view.value)
            self.save_button.enabled = False
            self.app.main_window.info_dialog(
                'File Saved',
                f'Successfully saved {os.path.basename(self.current_file)}'
            )
        except Exception as e:
            self.app.main_window.error_dialog(
                'Save Error',
                f'Error saving file: {str(e)}'
            )
    
    def rename_file(self, widget=None):
        """Rename the current file or directory."""
        if not self.current_file and not hasattr(self, 'original_name'):
            return
            
        try:
            # Get the new name and construct paths
            new_name = self.file_label.value
            if not new_name or new_name == self.original_name:
                return
            
            # Get the current path (either current_file for files, or from tree selection for directories)
            current_path = self.current_file or os.path.join(get_app_dir(), self.tree.selection.full_path)
            old_dir = os.path.dirname(current_path)
            new_path = os.path.join(old_dir, new_name)
            
            # Don't rename if the name hasn't changed
            if new_path == current_path:
                return
            
            # Check if it's a root directory
            if os.path.dirname(os.path.relpath(current_path, get_app_dir())) == '':
                self.app.main_window.error_dialog(
                    'Rename Error',
                    'Cannot rename root directories.'
                )
                # Restore original name
                self.file_label.value = os.path.basename(current_path)
                return
                
            # Check if target already exists
            if os.path.exists(new_path):
                self.app.main_window.error_dialog(
                    'Rename Error',
                    f'An item named "{new_name}" already exists.'
                )
                # Restore original name
                self.file_label.value = os.path.basename(current_path)
                return
            
            # Perform the rename
            os.rename(current_path, new_path)
            if self.current_file:  # Update current_file if we're renaming a file
                self.current_file = new_path
            
            # Update the tree view
            self.refresh_files()
            
            self.app.main_window.info_dialog(
                'Item Renamed',
                f'Successfully renamed to "{new_name}"'
            )
            
        except Exception as e:
            self.app.main_window.error_dialog(
                'Rename Error',
                f'Error renaming item: {str(e)}'
            )
            # Restore original name
            self.file_label.value = self.original_name
    
    def on_file_selected(self, tree, **kwargs):
        """Handle file selection in the tree."""
        try:
            # Get the selected node
            node = tree.selection

            
            try:
                # Get the full path from the node's data
                full_path = os.path.join(get_app_dir(), node.full_path)
                
                # Update file label and enable rename
                self.file_label.value = node.name
                
                # Enable rename for files and non-root directories
                is_root = os.path.dirname(node.full_path) == ''
                self.rename_button.enabled = not is_root  # Disable for root directories
                
                # Store original name for rename operation
                self.original_name = node.name
                
                # Check if it's a file
                is_file = os.path.isfile(full_path)
                
                if is_file:
                    # Check if it's a text file
                    is_text = self._is_text_file(full_path)

                    if is_text:
                        try:
                            print("8. Attempting to read file")
                            with open(full_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                                # Set content and enable editing
                                self.content_view.value = content
                                
                                self.content_view.readonly = False
                                self.current_file = full_path
                                self.save_button.enabled = False
                        except Exception as e:
                            print(f"Error reading file: {str(e)}")
                            self.content_view.value = f"Error reading file: {str(e)}"
                            self.content_view.readonly = True
                            self.current_file = None
                    else:
                        print("Not a text file")
                        self.content_view.value = f"Cannot edit {node.name}.\nOnly text files can be edited."
                        self.content_view.readonly = True
                        self.current_file = None
                else:
                    # For directories, show some info
                    try:
                        # Count both files and subdirectories
                        items = os.listdir(full_path)
                        files = [f for f in items if os.path.isfile(os.path.join(full_path, f)) and not f.startswith('.')]
                        dirs = [d for d in items if os.path.isdir(os.path.join(full_path, d)) and not d.startswith('.')]
                        
                        info = [
                            f"Directory: {node.name}",
                            f"Contains {len(files)} files and {len(dirs)} subdirectories",
                            "\nFiles:",
                            *[f"  • {f}" for f in sorted(files)],
                            "\nSubdirectories:",
                            *[f"  • {d}" for d in sorted(dirs)]
                        ]
                        
                        self.content_view.value = "\n".join(info)
                        self.content_view.readonly = True
                        self.current_file = None
                    except Exception as e:
                        print(f"Error reading directory: {str(e)}")
                        self.content_view.value = f"Error reading directory: {str(e)}"
                        self.current_file = None
                
                # Update save button state
                self.save_button.enabled = False
                
            except AttributeError as e:
                print(f"Attribute error accessing node: {str(e)}")
                print(f"Node attributes available: {dir(node)}")
                
        except Exception as e:
            print(f"Error in file selection: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(traceback.format_exc())
            self.content_view.value = f"Error: {str(e)}"
            self.current_file = None

class SettingsScreen(toga.Box):
    def __init__(self, app):
        super().__init__(style=Pack(direction=COLUMN, padding=10))
        self.app = app
        
        # Create settings sections
        self.add(toga.Label('Audio Settings', style=Pack(padding=(0, 5))))
        
        # Microphone selection
        self.mic_selection = toga.Selection(items=['Default Microphone'])
        self.add(toga.Box(
            children=[
                toga.Label('Microphone: '),
                self.mic_selection
            ],
            style=Pack(direction=ROW, padding=5)
        ))
        
        # System audio selection
        self.system_selection = toga.Selection(items=['BlackHole'])
        self.add(toga.Box(
            children=[
                toga.Label('System Audio: '),
                self.system_selection
            ],
            style=Pack(direction=ROW, padding=5)
        ))
        
        # Hotkey settings
        self.add(toga.Label('Hotkey Settings', style=Pack(padding=(10, 5))))
        
        # Add hotkey fields
        self.hotkey_boxes = {}
        hotkeys = {
            'Start/Stop Recording': 'cmd+shift+r',
            'Pause/Resume': 'cmd+shift+p'
        }
        
        for name, default in hotkeys.items():
            input_box = toga.TextInput(value=default)
            self.hotkey_boxes[name] = input_box
            self.add(toga.Box(
                children=[
                    toga.Label(f'{name}: '),
                    input_box
                ],
                style=Pack(direction=ROW, padding=5)
            ))
        
        # Save button
        self.add(toga.Button(
            'Save Settings',
            on_press=self.save_settings,
            style=Pack(padding=5)
        ))
    
    def save_settings(self, widget):
        # TODO: Implement settings save
        self.app.main_window.info_dialog(
            'Settings Saved',
            'Your settings have been saved successfully.'
        )

class TranscriberApp(toga.App):
    def __init__(self):
        super().__init__('Hacker Transcriber', 'com.hackertranscriber')
        self.recording_manager = RecordingManager()
        self.hotkey_manager = HotkeyManager(config)
        self.is_recording = False
        self.recording_start_time = None
        self.record_command = None
        self.pause_command = None
        self.current_profile = None  # Store the current profile

    def startup(self):
        # Create main window
        self.main_window = toga.MainWindow(title=self.formal_name)
        
        # Create commands
        self.record_command = toga.Command(
            self.toggle_recording,
            text='Record',
            tooltip='Start/Stop Recording',
            shortcut=toga.Key.MOD_1 + 'r',
            group=toga.Group.COMMANDS,
            section=0,
            order=0,
        )
        
        self.pause_command = toga.Command(
            self.toggle_pause,
            text='Pause',
            tooltip='Pause/Resume Recording',
            shortcut=toga.Key.MOD_1 + 'p',
            group=toga.Group.COMMANDS,
            section=0,
            order=1,
            enabled=False
        )
        
        self.commands.add(self.record_command, self.pause_command)
        
        # Add commands to toolbar
        self.main_window.toolbar.add(self.record_command, self.pause_command)
        
        # Create screens
        self.home_screen = HomeScreen(self)
        self.file_viewer_screen = FileViewerScreen(self)
        self.settings_screen = SettingsScreen(self)
        
        # Create tab container
        self.tabs = toga.OptionContainer(
            content=[
                ('Home', self.home_screen),
                ('Files', self.file_viewer_screen),
                ('Settings', self.settings_screen)
            ]
        )
        
        # Add the tabs to the main window
        self.main_window.content = self.tabs
        
        # Setup hotkeys and timer
        self.setup_hotkeys()
        self.timer_thread = Thread(target=self.update_timer, daemon=True)
        self.timer_thread.start()
        
        # Show the main window
        self.main_window.show()

    def setup_hotkeys(self):
        """Setup global hotkeys."""
        self.hotkey_manager.register_handler("start_recording", lambda: self.toggle_recording(self.record_command))
        self.hotkey_manager.register_handler("pause_recording", lambda: self.toggle_pause(self.pause_command))
        Thread(target=self.hotkey_manager.start, daemon=True).start()

    def toggle_recording(self, command, **kwargs):
        """Toggle recording state."""
        if not self.is_recording:
            # Check if a profile is selected
            if not self.current_profile:
                self.main_window.error_dialog(
                    'No Profile Selected',
                    'Please select a profile before starting recording.'
                )
                return True
                
            # Start recording
            self.recording_manager.start_recording()
            self.is_recording = True
            self.recording_start_time = time.time()
            self.home_screen.record_button.label = '⏹️ Stop Recording'
            self.home_screen.status_label.text = '⏺️ Recording'
            self.home_screen.pause_button.enabled = True
            self.pause_command.enabled = True
        else:
            # Stop recording
            self.recording_manager.stop_recording()
            self.is_recording = False
            self.recording_start_time = None
            self.home_screen.record_button.label = '🎙️ Start Recording'
            self.home_screen.status_label.text = '⏹️ Ready to Record'
            self.home_screen.pause_button.enabled = False
            self.home_screen.pause_button.label = '⏸️ Pause'
            self.pause_command.enabled = False
            # Refresh file viewer
            self.file_viewer_screen.refresh_files()
        return True

    def toggle_pause(self, command, **kwargs):
        """Toggle pause state."""
        if self.is_recording:
            self.recording_manager.toggle_pause()
            if self.recording_manager.is_paused:
                self.home_screen.status_label.text = '⏸️ Paused'
                self.home_screen.pause_button.label = '▶️ Resume'
            else:
                self.home_screen.status_label.text = '⏺️ Recording'
                self.home_screen.pause_button.label = '⏸️ Pause'
        return True

    def update_timer(self):
        """Update the timer label."""
        while True:
            if self.is_recording and self.recording_start_time:
                elapsed = time.time() - self.recording_start_time
                time_str = time.strftime("%M:%S", time.gmtime(elapsed))
                self.home_screen.timer_label.text = time_str
            time.sleep(0.1)

def main():
    app = TranscriberApp()
    return app.main_loop() 