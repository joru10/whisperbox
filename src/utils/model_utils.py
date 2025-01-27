from pathlib import Path
from ..core.config import config
from ..utils.logger import log
from ..core.setup import download_model


def check_whisper_model():
    """Check if Whisper model exists and download if missing."""
    model_name = config.transcription.whisper.model
    models_path = Path(config.transcription.whisper.models_path)
    model_file = models_path / f"whisper-{model_name}.llamafile"

    if not model_file.exists():
        log.warning(f"Whisper model {model_name} not found at: {model_file}")
        log.info("Downloading required model...")
        try:
            download_model(config._config)
        except Exception as e:
            log.error(f"Error downloading model: {e}")
            raise SystemExit("Cannot proceed without Whisper model") 