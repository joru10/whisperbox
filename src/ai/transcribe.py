#!/usr/bin/env python
import argparse
import subprocess
import os
import time
import pyaudio
import wave
from pydub import AudioSegment
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
import select
import sys
from .ai_service import AIService
from urllib.request import urlretrieve
from ..core.config import config
from ..audio.audio import AudioRecorder, convert_to_wav
from ..utils.logger import log
console = Console()

OLLAMA_MODEL = config.ai.default_model
DEFAULT_WHISPER_MODEL = config.transcription.whisper.model
WHISPER_BASE_URL = config.transcription.whisper.base_url

ASCII_ART = """
Hacker Transcriber
"""


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.error("Error: FFmpeg is not installed.")
        log.warning("Please install FFmpeg using:")
        log.info("  brew install ffmpeg")
        return False


def install_whisper_model(model_name, whisperfile_path):
    full_model_name = f"whisper-{model_name}.llamafile"
    url = f"{WHISPER_BASE_URL}{full_model_name}"
    output_path = os.path.join(whisperfile_path, full_model_name)

    # Create the directory if it doesn't exist
    os.makedirs(whisperfile_path, exist_ok=True)
    
    log.info(f"Downloading {full_model_name}...")
    # Create a progress bar
    progress = console.status("[bold green]Downloading...", spinner="dots")
    progress.start()
    
    def show_progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min((downloaded / total_size) * 100, 100)
            progress.update(f"[bold green]Downloading... {percent:.1f}%")
    

    try:
        urlretrieve(url, output_path, show_progress)
        progress.stop()
        os.chmod(output_path, 0o755)
        log.success(f"{full_model_name} installed successfully.")
    except Exception as e:
        progress.stop()
        log.error(f"Error downloading model: {str(e)}")
        raise


def get_whisper_model_path(model_name, whisperfile_path, verbose):
    full_model_name = f"whisper-{model_name}.llamafile"
    # Expand user path if necessary
    whisperfile_path = os.path.expanduser(whisperfile_path)
    model_path = os.path.join(whisperfile_path, full_model_name)
    
    log.info(f"Looking for Whisper model at: {model_path}")
    
    if not os.path.exists(model_path):
        log.warning(f"Whisper model {full_model_name} not found.")
        log.warning(f"Would you like to download it from {WHISPER_BASE_URL}?")

        if input("Download model? (y/n): ").lower() == "y":
            install_whisper_model(model_name, whisperfile_path)
        else:
            raise FileNotFoundError(
                f"Whisper model {full_model_name} not found and download was declined."
            )
    else:
        log.success(f"Found Whisper model at: {model_path}")
        

    # Check if the file is executable
    if not os.access(model_path, os.X_OK):
        log.warning("Making model file executable...")
        os.chmod(model_path, 0o755)

    return model_path


def transcribe_audio(model_name, whisperfile_path, audio_file, verbose):
    try:
        model_path = get_whisper_model_path(model_name, whisperfile_path, verbose)
        gpu_flag = "--gpu auto" if config.transcription.whisper.gpu_enabled else ""
        command = f"{model_path} -f {audio_file} {gpu_flag}"

        if verbose:
            log.info(f"Attempting to run command: {command}")

        # Check if file exists and is readable
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
            
        log.info("Running transcription command...")

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            log.error(f"Command failed with return code {process.returncode}")
            log.error(f"Error output: {stderr}")

            raise Exception(f"Transcription failed: {stderr}")

        if not stdout.strip():
            log.warning("Warning: Transcription produced empty output")
            return None

        if verbose:
            log.header("Transcription output:")
            log.info(stdout)

        return stdout.strip()

    except Exception as e:
        log.error(f"Error in transcribe_audio: {str(e)}")
        import traceback
        log.error(f"{traceback.format_exc()}")

        raise


def summarize(text):
    ai_service = AIService()
    prompt = config.ai.prompts.summary.format(text=text)
    return ai_service.query(prompt)


def analyze_sentiment(text):
    ai_service = AIService()
    prompt = config.ai.prompts.sentiment.format(text=text)
    sentiment = ai_service.query(prompt).strip().lower()
    return sentiment if sentiment in ["positive", "neutral", "negative"] else "neutral"


def detect_intent(text):
    ai_service = AIService()
    prompt = config.ai.prompts.intent.format(text=text)
    return ai_service.query(prompt)


def detect_topics(text):
    ai_service = AIService()
    prompt = config.ai.prompts.topics.format(text=text)
    return ai_service.query(prompt)


def export_to_markdown(text, filename):
    """Export transcription text to a markdown file in the transcriptions directory.

    Args:
        text (str): The transcription text
        filename (str): Name of the file without extension
    """
    # Create transcriptions directory if it doesn't exist
    os.makedirs("transcriptions", exist_ok=True)
    file_path = os.path.join("transcriptions", f"{filename}.md")

    with open(file_path, "w") as f:
        f.write("# Meeting Transcription\n\n")
        f.write(text)

    log.success(f"Transcription saved to {file_path}")


def get_sentiment_color(sentiment):
    return {"positive": "green3", "neutral": "gold1", "negative": "red1"}.get(
        sentiment, "white"
    )


def display_rich_output(transcript, summary, sentiment, intent, topics):
    # Print the ASCII art directly without a border
    console.print(Text(ASCII_ART, style="bold blue"))

    # Clean the transcript text
    transcript_clean = "\n".join(
        line.partition("]")[2].strip()
        for line in transcript.split("\n")
        if line.strip()
    )

    # Create panels using Panel with expand=True
    transcript_panel = Panel(
        transcript_clean,
        title="Transcript",
        border_style="cyan",
        padding=(1, 2),
        expand=True,
    )

    summary_panel = Panel(
        summary,
        title="Summary",
        border_style="cyan",
        padding=(1, 2),
        expand=True,
    )

    # Analysis Results Table
    analysis_table = Table(show_header=False, box=box.SIMPLE, expand=True)
    analysis_table.add_column(style="bold", width=12)
    analysis_table.add_column()
    analysis_table.add_row(
        "Sentiment:",
        Text(sentiment.capitalize(), style=get_sentiment_color(sentiment)),
    )
    analysis_table.add_row("Intent:", Text(intent))
    analysis_table.add_row("Topics:", Text(topics))

    analysis_panel = Panel(
        analysis_table,
        title="Analysis Results",
        border_style="cyan",
        padding=(1, 2),
        expand=True,
    )

    # Print panels sequentially
    panels = [
        transcript_panel,
        summary_panel,
        analysis_panel,
    ]

    for panel in panels:
        console.print(panel)


class Shallowgram:
    def __init__(self, whisperfile_path=None, vault_path=None):
        self.whisperfile_path = whisperfile_path or os.path.expanduser(
            "~/.whisperfiles"
        )
        self.vault_path = vault_path or os.path.expanduser("~/Documents/ObsidianVault")
        self.ai_service = AIService()

    def transcribe(self, audio_file, model=DEFAULT_WHISPER_MODEL, full_analysis=False):
        log.info(f"Starting transcription of {audio_file}")
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        # Convert to wav if needed
        file_ext = os.path.splitext(audio_file)[1].lower()
        if file_ext != ".wav":
            log.info("Converting audio to WAV format...")
            wav_file = "temp_audio.wav"
            convert_to_wav(audio_file, wav_file)
            audio_file = wav_file

        try:
            log.info("Running Whisper transcription...")
            transcript = transcribe_audio(model, self.whisperfile_path, audio_file, True)  # Set verbose=True
            

            if not transcript:
                log.error("Whisper returned empty transcript")
                return None

            # Save transcription to markdown file
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            export_to_markdown(transcript, f"meeting_{timestamp}")

            if full_analysis:
                log.info("Performing AI analysis...")
                summary = summarize(transcript)
                sentiment = analyze_sentiment(transcript)
                intent = detect_intent(transcript)
                topics = detect_topics(transcript)
                
                return {
                    'text': transcript,
                    'summary': summary,
                    'sentiment': sentiment,
                    'intent': intent,
                    'topics': topics
                }
            
            return {'text': transcript}

        except Exception as e:
            log.error(f"Error in transcription: {str(e)}")
            raise
        finally:
            # Cleanup temporary file
            if file_ext != ".wav" and os.path.exists("temp_audio.wav"):
                os.remove("temp_audio.wav")
