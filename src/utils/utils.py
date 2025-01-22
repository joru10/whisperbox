import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union
import platform
import subprocess
from datetime import datetime
# Application name - this will be used for the app directory
APP_NAME = "WhisperBox"

def get_app_dir() -> Path:
    """Get the application directory in the user's Documents folder."""
    documents_dir = Path.home() / "Documents"
    return documents_dir / APP_NAME

def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_app_dir() / "config.yaml"

def get_meetings_dir() -> Path:
    """Get the meetings directory path."""
    return get_app_dir() / "meetings"

def get_monologues_dir() -> Path:
    """Get the monologues directory path."""
    return get_app_dir() / "monologues"

def get_models_dir() -> Path:
    """Get the models directory path."""
    return get_app_dir() / "models"

def create_session_dir(session_type: str) -> Path:
    """Create a new directory for a meeting or monologue session.
    
    Args:
        session_type (str): Either 'meeting' or 'monologue'
        
    Returns:
        Path: Path to the created session directory
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_dir = get_meetings_dir() if session_type == "meeting" else get_monologues_dir()
    session_dir = base_dir / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def is_first_run() -> bool:
    """Check if this is the first time the app is being run."""
    return not get_config_path().exists()

def create_app_directory_structure() -> None:
    """Create the application directory structure."""
    # Create main app directory in Documents
    app_dir = get_app_dir()
    app_dir.mkdir(exist_ok=True, parents=True)
    
    # Create main subdirectories
    get_meetings_dir().mkdir(exist_ok=True)
    get_monologues_dir().mkdir(exist_ok=True)
    get_models_dir().mkdir(exist_ok=True)

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to the config file."""
    with open(get_config_path(), 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def load_config() -> Dict[str, Any]:
    """Load configuration from the config file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    return {} 

def reveal_in_file_manager(path: Union[str, Path]):
    """Reveal the file in the system's file manager (Finder/Explorer/etc)."""
    path = str(path)
    
    if platform.system() == "Darwin":  # macOS
        # Use AppleScript to reveal in Finder
        subprocess.run(["osascript", "-e", f'tell application "Finder" to reveal POSIX file "{path}"'])
        subprocess.run(["osascript", "-e", 'tell application "Finder" to activate'])
    elif platform.system() == "Windows":
        # Windows Explorer's select functionality
        subprocess.run(["explorer", "/select,", path])
    else:  # Linux
        # Most file managers support showing containing folder
        folder_path = os.path.dirname(path)
        try:
            subprocess.run(["xdg-open", folder_path])
        except FileNotFoundError:
            # Fallback for systems without xdg-open
            subprocess.run(["gio", "open", folder_path])
