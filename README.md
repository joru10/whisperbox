# WhisperBox

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
- Export to Markdown
- Rich terminal UI with color-coded output
- Configurable audio settings and output formats

## Prerequisites

- Python 3.10 or higher
- FFmpeg (required for audio processing)
- Poetry (for dependency management)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/tooluseai/whisperbox.git
cd whisperbox
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

4. Install BlackHole (MacOS only)

```bash
brew install blackhole-2ch
```

5. Configure your API keys:
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

### Setup

The first time you run the app, you will go through the setup wizard.

```bash
poetry run wb
```

Then select the Whisper model you want to use. The smaller models are faster and quicker to download but the larger models are more accurate.
Download times will vary depending on your internet speed.

Then select the AI provider you want to use. Ollama runs locally and does not require an API key.

Then select the model you want to use.

Then you will have the option to view the config file location so you can customize additional settings. This directory also contains the whisper models you downloaded, the meeting, and the monologues.

### Basic Transcription

1. Start recording:

```bash
poetry run wb
```

2. Press Enter to stop recording when finished.

### Advanced Options

- Specify a profile:

```bash
poetry run wb --profile monologue_to_keynote
```

- Specify a Whisper model:

```bash
poetry run wb --model large
```

- Enable full analysis (summary, sentiment, intent, topics):

```bash
poetry run wb --analyze
```

- Enable verbose output:

```bash
poetry run wb --verbose
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
whisperbox/
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
