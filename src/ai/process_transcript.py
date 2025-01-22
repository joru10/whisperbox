from rich.console import Console
from .ai_service import AIService
from typing import Optional

console = Console()


def process_transcript(
    transcript_path: str,
    ai_provider: Optional[str] = None,
    prompt: Optional[str] = None,
) -> str:
    """Process a transcript with AI to generate additional insights.

    Args:
        transcript_path (str): Path to the markdown transcript file
        ai_provider (str, optional): AI provider to use (ollama, groq, anthropic, or openai)
        prompt (str, optional): Custom prompt to use for processing

    Returns:
        str: The processed result from the AI
    """
    try:
        with open(transcript_path, "r") as f:
            transcript_text = f.read()

        # Remove the markdown header to get clean text
        clean_text = transcript_text.replace("# Meeting Transcription\n\n", "").strip()

        if not prompt:
            raise ValueError("No prompt provided for processing")

        final_prompt = prompt.format(text=clean_text)

        # Process with AI service
        ai_service = AIService(service_type=ai_provider)
        result = ai_service.query(final_prompt)

        return result

    except Exception as e:
        console.print(f"[red]Error processing transcript: {str(e)}[/red]")
        raise
