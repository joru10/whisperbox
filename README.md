# Hacker Transcriber

A powerful command-line tool for transcribing and analyzing audio recordings with AI assistance. Record meetings, lectures, or any audio directly from your terminal and get instant transcriptions with summaries, sentiment analysis, and topic detection.

## Features

- Live audio recording through terminal
- Multiple transcription models via Whisper AI
- AI-powered analysis including:
  - Text summarization
  - Sentiment analysis
  - Intent detection
  - Topic extraction
- Support for multiple AI providers:
  - Anthropic Claude
  - OpenAI GPT-4
  - Groq
  - Ollama (local models)
- Export to Markdown (with optional Obsidian vault integration)
- Rich terminal UI with color-coded output
- Configurable audio settings and output formats

## Prerequisites

- Python 3.10 or higher
- FFmpeg (required for audio processing)
- Poetry (for dependency management)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/hacker-transcriber.git
cd hacker-transcriber
```

2. Install dependencies using Poetry:

```bash
poetry install
```

3. Install FFmpeg if not already installed:

```bash
# On macOS using Homebrew
brew install ffmpeg

# On Ubuntu/Debian
sudo apt-get install ffmpeg
```

4. Configure your API keys:
   - Copy `config.yaml` to create your local configuration
   - Add your API keys for the services you plan to use:
     - OpenAI
     - Anthropic
     - Groq
   - Alternatively, set them as environment variables:
     - `OPENAI_API_KEY`
     - `ANTHROPIC_API_KEY`
     - `GROQ_API_KEY`

## Usage

### Basic Transcription

1. Start recording:

```bash
poetry run transcribe
```

2. Press Enter to stop recording when finished.

### Advanced Options

- Specify a Whisper model:

```bash
poetry run transcribe --model large
```

- Enable full analysis (summary, sentiment, intent, topics):

```bash
poetry run transcribe --analyze
```

- Export to Obsidian vault:

```bash
poetry run transcribe --vault ~/Documents/ObsidianVault
```

- Enable verbose output:

```bash
poetry run transcribe --verbose
```

## Configuration

The `config.yaml` file allows you to customize:

- API settings for AI providers
- Audio recording parameters
- Transcription settings
- Output formats and directories
- Display preferences
- AI prompt templates

See the example `config.yaml` for all available options.

## Project Structure

```
hacker-transcriber/
├── pyproject.toml       # Poetry project configuration
├── config.yaml         # Application configuration
├── main.py            # Entry point
└── src/
    ├── ai_service.py   # AI provider integrations
    ├── config.py       # Configuration management
    ├── transcribe.py   # Core transcription logic
    └── audio.py        # Audio recording utilities
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Whisper AI](https://github.com/openai/whisper) for the transcription models
- [Rich](https://github.com/Textualize/rich) for the terminal UI
- All the AI providers supported by this tool

## Authors

- Ty Fiero <tyfierodev@gmail.com>
- Mike Bird <tooluseai@gmail.com>
