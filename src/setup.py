import os
import yaml
from rich.console import Console
from rich.prompt import Prompt, Confirm
from .config import Config
from .transcribe import install_whisper_model, check_ffmpeg
from typing import Dict, Any

console = Console()

WHISPER_MODELS = {
    "1": {"name": "tiny.en", "description": "Fastest, least accurate, ~1GB RAM"},
    "2": {"name": "base.en", "description": "Fast, decent accuracy, ~1GB RAM"},
    "3": {"name": "small.en", "description": "Balanced speed/accuracy, ~2GB RAM"},
    "4": {"name": "medium.en", "description": "More accurate, slower, ~5GB RAM"},
    "5": {"name": "large", "description": "Most accurate, slowest, ~10GB RAM"},
}

def setup_config() -> Dict[str, Any]:
    """Interactive configuration setup."""
    console.print("\n[bold blue]Welcome to Hacker Transcriber Setup![/bold blue]")
    
    # Check FFmpeg
    console.print("\n[yellow]Checking FFmpeg installation...[/yellow]")
    if not check_ffmpeg():
        if not Confirm.ask("Would you like to continue anyway?"):
            raise SystemExit("Setup cancelled")

    # Load existing config if available
    config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

    # Select Whisper model
    console.print("\n[bold]Available Whisper Models:[/bold]")
    for key, model in WHISPER_MODELS.items():
        console.print(f"{key}. {model['name']} - {model['description']}")
    
    model_choice = Prompt.ask(
        "Select a model",
        choices=list(WHISPER_MODELS.keys()),
        default="1"
    )
    
    selected_model = WHISPER_MODELS[model_choice]["name"]
    
    # Update config
    if "transcription" not in config:
        config["transcription"] = {}
    if "whisper" not in config["transcription"]:
        config["transcription"]["whisper"] = {}
    
    config["transcription"]["whisper"]["model"] = selected_model
    
    # Configure API keys
    console.print("\n[bold]API Configuration[/bold]")
    console.print("(Press Enter to skip if not using)")
    
    api_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GROQ_API_KEY": "Groq"
    }
    
    for env_var, service in api_keys.items():
        current_key = os.getenv(env_var) or ""
        if not current_key:
            key = Prompt.ask(f"{service} API Key", password=True, default="")
            if key:
                os.environ[env_var] = key

    # Save config
    with open("config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return config

def download_model(config: Dict[str, Any]) -> None:
    """Download the selected Whisper model."""
    model_name = config["transcription"]["whisper"]["model"]
    whisperfile_path = os.path.expanduser(config["transcription"]["whisper"].get("whisperfile_path", "~/.whisperfiles"))
    
    console.print(f"\n[yellow]Downloading Whisper model: {model_name}[/yellow]")
    try:
        install_whisper_model(model_name, whisperfile_path)
        console.print("[green]Model downloaded successfully![/green]")
    except Exception as e:
        console.print(f"[red]Error downloading model: {e}[/red]")
        if not Confirm.ask("Would you like to continue anyway?"):
            raise SystemExit("Setup cancelled")

def setup():
    """Run the complete setup process."""
    try:
        config = setup_config()
        download_model(config)
        
        console.print("\n[bold green]Setup completed successfully![/bold green]")
        console.print("\nYou can now run the transcriber with:")
        console.print("[blue]poetry run transcribe[/blue]")
        
    except Exception as e:
        console.print(f"\n[red]Setup failed: {e}[/red]")
        raise SystemExit(1) 