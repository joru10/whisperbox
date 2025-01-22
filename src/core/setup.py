import os
import yaml
import subprocess
from rich.prompt import Prompt, Confirm
from .config import Config, DEFAULT_CONFIG
from ai.transcribe import install_whisper_model, check_ffmpeg
from utils.utils import (
    create_app_directory_structure, save_config, get_config_path, 
    get_models_dir, get_app_dir, reveal_in_file_manager
)
from typing import Dict, Any, Union
from pathlib import Path
from InquirerPy import inquirer
from utils.logger import log
import time

WHISPER_MODELS = {
    "tiny.en": {"description": "Fastest, least accurate, ~1GB RAM"},
    "base.en": {"description": "Fast, decent accuracy, ~1GB RAM"},
    "small.en": {"description": "Balanced speed/accuracy, ~2GB RAM"},
    "medium.en": {"description": "More accurate, slower, ~5GB RAM"},
    "large": {"description": "Most accurate, slowest, ~10GB RAM"},
}

AI_PROVIDERS = {
    "ollama": {
        "description": "Local AI models (requires Ollama installation)",
        "default_model": "llama2"
    },
    "openai": {
        "description": "OpenAI's GPT models (requires API key)",
        "default_model": "gpt-4-0125-preview"
    },
    "anthropic": {
        "description": "Anthropic's Claude models (requires API key)",
        "default_model": "claude-3-sonnet-20240229"
    },
    "groq": {
        "description": "Groq's fast inference API (requires API key)",
        "default_model": "mixtral-8x7b-32768"
    }
}

def check_ollama() -> bool:
    """Check if Ollama is installed and accessible."""
    try:
        subprocess.run(['ollama', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def setup_config() -> Dict[str, Any]:
    """Interactive configuration setup."""
    log.header("Welcome to WhisperBox!")
    time.sleep(1)
    log.info("Let's get you set up.")
    time.sleep(0.5)
    
    # Create application directory structure
    create_app_directory_structure()
    log.success(f"Created WhisperBox directory at: {get_app_dir()}")
    log.info("Your recordings and transcripts will be saved here.")
    
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Check FFmpeg
    log.info("Checking FFmpeg installation...")
    time.sleep(0.5)
    if not check_ffmpeg():
        if not Confirm.ask("Would you like to continue anyway?"):
            raise SystemExit("Setup cancelled")
    else:
        log.success("FFmpeg is installed.")

    # Select Whisper model
    log.header("Whisper Model Selection")
    model_choices = [
        f"{model_name} - {model_info['description']}"
        for model_name, model_info in WHISPER_MODELS.items()
    ]
    
    selection = inquirer.select(
        message="Select a Whisper model:",
        choices=model_choices,
        default=model_choices[0]
    ).execute()
    
    # Extract model name from selection
    selected_model = selection.split(" - ")[0]
    
    # Update config with model selection
    if "transcription" not in config:
        config["transcription"] = {}
    if "whisper" not in config["transcription"]:
        config["transcription"]["whisper"] = {}
    
    config["transcription"]["whisper"]["model"] = selected_model
    config["transcription"]["whisper"]["models_path"] = str(get_models_dir())
    
    # Save initial config
    save_config(config)
    
    # Download the model immediately after selection
    download_model(config)
    
    time.sleep(0.5)
    # Configure AI Settings
    log.header("AI Configuration")
    time.sleep(0.5)
    
    # Select AI provider
    provider_choices = [
        f"{provider} - {info['description']}"
        for provider, info in AI_PROVIDERS.items()
    ]
    
    provider_selection = inquirer.select(
        message="Select your preferred AI provider:",
        choices=provider_choices,
        default=provider_choices[0]
    ).execute()
    
    # Extract provider name from selection
    selected_provider = provider_selection.split(" - ")[0]
    
    # Initialize AI config
    if "ai" not in config:
        config["ai"] = {}
    
    config["ai"]["default_provider"] = selected_provider
    
    # Handle provider-specific setup
    if selected_provider == "ollama":
        if not check_ollama():
            log.warning("Ollama is not installed. Please visit ollama.com to install it")
            log.warning("and download a model before using WhisperBox with Ollama.")
        model = inquirer.text(
            message="Enter the Ollama model name (e.g., llama3.2):",
            default=AI_PROVIDERS["ollama"]["default_model"]
        ).execute()
        config["ai"]["default_model"] = model
    else:
        # For other providers, handle API key and model selection
        if "api" not in config:
            config["api"] = {}
        if selected_provider.lower() not in config["api"]:
            config["api"][selected_provider.lower()] = {}
        
        # Get API key
        key = inquirer.secret(
            message=f"Enter your {selected_provider} API key:",
            validate=lambda x: len(x) > 0,
            invalid_message="API key cannot be empty"
        ).execute()
        
        config["api"][selected_provider.lower()]["api_key"] = key
        
        # Get model name
        model = inquirer.text(
            message=f"Enter the {selected_provider} model name, as it appears in the API documentation for that provider:",
            default=AI_PROVIDERS[selected_provider]["default_model"]
        ).execute()
        
        config["ai"]["default_model"] = model

    # Save final config
    save_config(config)
    config_path = get_config_path()
    log.info(f"Configuration saved to: {config_path}")
    log.info("This file contains your settings and API keys.")
    
    # Ask if user wants to view config file
    if Confirm.ask("Would you like to view the config file location to customize additional settings?"):
        try:
            reveal_in_file_manager(config_path)
            log.info("Opening folder containing config.yaml...")
            log.info("You can edit this file with your preferred text editor to customize additional settings.")
            log.info("Changes will take effect the next time you run the application.")
        except Exception as e:
            log.error(f"Error revealing config file: {e}")
            log.info(f"You can find the config file at: {config_path}")

    return config

def download_model(config: Dict[str, Any]) -> None:
    """Download the selected Whisper model."""
    model_name = config["transcription"]["whisper"]["model"]
    models_path = Path(config["transcription"]["whisper"]["models_path"])
    model_file = models_path / f"whisper-{model_name}.llamafile"
    
    log.info(f"Checking for Whisper model: {model_name}")
    
    if model_file.exists():
        log.warning(f"Warning: Model {model_name} already exists at: {model_file}")
        if not Confirm.ask("Would you like to download and overwrite it?"):
            log.info("Using existing model.")
            return
        log.warning("Proceeding with download...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            install_whisper_model(model_name, str(models_path))
            log.success("Model downloaded successfully!")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                log.warning(f"Error downloading model (attempt {attempt + 1}/{max_retries}): {e}")
                log.warning("Retrying...")
            else:
                log.error(f"Error downloading model: {e}")
                if not Confirm.ask("Would you like to continue without downloading the model?"):
                    raise SystemExit("Setup cancelled")
                log.warning("Continuing without model. You can download it later using the setup command.")

def setup():
    """Run the complete setup process."""
    try:
        config = setup_config()
        
        log.success("Setup completed successfully!")
        log.info("You can now run the transcriber with:")
        log.info("[blue]transcribe[/blue]")
        
    except Exception as e:
        log.error(f"Setup failed: {e}")
        raise SystemExit(1) 