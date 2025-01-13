import os
import yaml
from typing import Dict, Any, Optional

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file.
        
        Args:
            config_path (str): Path to the config.yaml file
        """
        self._config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load_config()
        
    def load_config(self) -> None:
        """Load configuration from YAML file."""
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(f"Configuration file not found: {self._config_path}")
            
        with open(self._config_path, 'r') as f:
            self._config = yaml.safe_load(f)
            
        # Create directories if they don't exist
        os.makedirs(self.output.audio_directory, exist_ok=True)
        os.makedirs(self.output.transcript_directory, exist_ok=True)
        os.makedirs(self.system.temp_directory, exist_ok=True)
        
        # Load API keys from environment variables if available
        self._load_api_keys_from_env()
    
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
    def hotkeys(self):
        """Access hotkey settings."""
        return ConfigSection(self._config.get('hotkeys', {}))

class ConfigSection:
    """Helper class to provide dot notation access to config sections."""
    def __init__(self, section_dict: Dict[str, Any]):
        self._section = section_dict
        
    def __getattr__(self, key: str) -> Any:
        if key not in self._section:
            raise AttributeError(f"Configuration key '{key}' not found")
        return self._section[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with a default."""
        return self._section.get(key, default)

# Create a global config instance
config = Config()

# # Usage example:
# if __name__ == "__main__":
#     # Test the configuration
#     try:
#         print(f"Audio sample rate: {config.audio.sample_rate}")
#         print(f"Transcription language: {config.transcription.language}")
#         print(f"Output directory: {config.output.transcript_directory}")
#         print(f"Debug mode: {config.system.debug_mode}")
#     except Exception as e:
#         print(f"Error: {e}") 