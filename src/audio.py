import os
import wave
import pyaudio
import select
import sys
from pydub import AudioSegment
from rich.console import Console
from config import config

console = Console()

# Audio constants
CHUNK = config.audio.chunk_size
FORMAT = pyaudio.paInt16
CHANNELS = config.audio.channels
RATE = config.audio.sample_rate

def record_audio(output_file, verbose=False):
    """Record audio from microphone input."""
    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=config.audio.channels,
        rate=config.audio.sample_rate,
        input=True,
        frames_per_buffer=config.audio.chunk_size
    )

    console.print(f"[{config.display.colors.recording}]Recording... Press Enter to stop.[/]")

    frames = []

    try:
        while True:
            if select.select([sys.stdin], [], [], 0.0)[0]:
                if sys.stdin.readline().strip() == "":
                    break
            data = stream.read(CHUNK)
            frames.append(data)
    except KeyboardInterrupt:
        pass

    console.print("[green]Finished recording.[/green]")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(output_file, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()

    if verbose:
        console.print(f"[yellow]Audio file size: {os.path.getsize(output_file)} bytes[/yellow]")

def convert_to_wav(input_file, output_file):
    """Convert audio file to WAV format."""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")
