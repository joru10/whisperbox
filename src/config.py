import os
import yaml
from typing import Dict, Any, Optional
from .utils import get_config_path, get_recordings_dir, get_transcripts_dir, get_models_dir, save_config, load_config

DEFAULT_CONFIG = {
    'commands': {
        'help': {
            'description': 'Show help menu',
            'action': 'help'
        },
        'config': {
            'description': 'Configure application settings',
            'action': 'config'
        },
        'devices': {
            'description': 'List available audio devices',
            'action': 'devices'
        }
    },
    'ai': {
        'default_provider': 'ollama',
        'default_model': 'llama3.2'
    },
    'hotkeys': {
        'start_recording': 'ctrl+r',
        'stop_recording': 'ctrl+s',
        'pause_recording': 'ctrl+shift+p',
    },
    'output': {
        'audio_directory': str(get_recordings_dir()),
        'transcript_directory': str(get_transcripts_dir()),
    },
    'transcription': {
        'whisper': {
            'models_path': str(get_models_dir()),
            'base_url': 'https://huggingface.co/Mozilla/whisperfile/resolve/main/',
            'gpu_enabled': True
        }
    },
    'system': {
        'temp_directory': '/tmp/whisperbox',
        'debug_mode': False
    }
}

class Config:
    def __init__(self):
        """Initialize configuration from YAML file."""
        self._config_path = get_config_path()
        self._config: Dict[str, Any] = {}
        self._config.update(DEFAULT_CONFIG)  # Start with defaults
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from YAML file."""
        file_config = load_config()
        self._config.update(file_config)
            
        # Create directories if they don't exist
        os.makedirs(self.output.audio_directory, exist_ok=True)
        os.makedirs(self.output.transcript_directory, exist_ok=True)
        os.makedirs(self.system.temp_directory, exist_ok=True)
        
        # Load API keys from environment variables if available
        self._load_api_keys_from_env()
    
    def save(self) -> None:
        """Save current configuration to file."""
        save_config(self._config)

    def _load_api_keys_from_env(self) -> None:
        """Load API keys from environment variables if they exist."""
        env_mapping = {
            'OPENAI_API_KEY': ('api', 'openai', 'api_key'),
            'ANTHROPIC_API_KEY': ('api', 'anthropic', 'api_key'),
            'GROQ_API_KEY': ('api', 'groq', 'api_key'),
        }
        
        for env_var, config_path in env_mapping.items():
            if env_value := os.getenv(env_var):
                # Create nested structure if it doesn't exist
                current = self._config
                for part in config_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[config_path[-1]] = env_value

    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for the specified service.
        
        Args:
            service (str): Service name (openai, anthropic, groq)
            
        Returns:
            Optional[str]: API key if found, None otherwise
        """
        try:
            return self.api.get(service, {}).get('api_key')
        except AttributeError:
            return None

    @property
    def api(self):
        """Access API settings."""
        return ConfigSection(self._config.get('api', {}))

    @property
    def ai(self):
        """Access AI settings."""
        return ConfigSection(self._config.get('ai', {}))

    @property
    def audio(self):
        """Access audio recording settings."""
        return ConfigSection(self._config.get('audio', {}))
    
    @property
    def transcription(self):
        """Access transcription settings."""
        return ConfigSection(self._config.get('transcription', {}))
    
    @property
    def output(self):
        """Access output settings."""
        return ConfigSection(self._config.get('output', {}))
    
    @property
    def display(self):
        """Access display settings."""
        return ConfigSection(self._config.get('display', {}))
    
    @property
    def system(self):
        """Access system settings."""
        return ConfigSection(self._config.get('system', {}))

    @property
    def commands(self):
        """Access command settings."""
        return ConfigSection(self._config.get('commands', {}))

    @property
    def hotkeys(self):
        """Access hotkey settings."""
        return ConfigSection(self._config.get('hotkeys', {}))

class ConfigSection:
    """Helper class to provide dot notation access to config sections."""
    def __init__(self, section_dict: Dict[str, Any]):
        self._section = section_dict
        
    def __getattr__(self, key: str) -> Any:
        if key not in self._section:
            return None
        value = self._section[key]
        if isinstance(value, dict):
            return ConfigSection(value)
        return value
    
    def __getitem__(self, key: str) -> Any:
        """Support dictionary-style access."""
        return self._section[key]
    
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return key in self._section
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with a default."""
        return self._section.get(key, default)
        
    def items(self):
        """Make the config section iterable like a dict."""
        return self._section.items()

# Create a global config instance
config = Config()
