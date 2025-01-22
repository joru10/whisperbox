from rich.console import Console
from .ai_service import AIService
from ..core.config import config
from typing import Optional, List

console = Console()


def get_available_processors() -> List[str]:
    """Get list of available processing methods from config."""
    return list(config.ai.prompts.processing.keys())


def process_transcript(
    transcript_path: str,
    method: Optional[str] = None,
    ai_provider: Optional[str] = None,
    prompt: Optional[str] = None,
) -> None:
    """Process a transcript with AI to generate additional insights.

    Args:
        transcript_path (str): Path to the markdown transcript file
        method (str, optional): Processing method to use. Must be one defined in config.ai.prompts.processing
        ai_provider (str, optional): AI provider to use (ollama, groq, anthropic, or openai)
        prompt (str, optional): Custom prompt to use for processing
    """
    try:
        with open(transcript_path, "r") as f:
            transcript_text = f.read()

        # Remove the markdown header to get clean text
        clean_text = transcript_text.replace("# Meeting Transcription\n\n", "").strip()

        # Use custom prompt if provided, otherwise get from config
        if prompt:
            final_prompt = prompt.format(text=clean_text)
        else:
            if not method or not hasattr(config.ai.prompts.processing, method):
                available = get_available_processors()
                raise ValueError(
                    f"Unknown processing method: {method}. Available methods: {', '.join(available)}"
                )
            final_prompt = config.ai.prompts.processing[method].format(text=clean_text)

        # Process with AI service
        ai_service = AIService(service_type=ai_provider)
        result = ai_service.query(final_prompt)

        # Save the processed result
        output_path = transcript_path.replace(".md", f"_{method}.md")
        with open(output_path, "w") as f:
            title = (
                "Whisperbox Output"
                if method is None
                else f"Whisperbox Output ({method.replace('-', ' ').title()})"
            )
            f.write(f"# {title}\n\n")
            f.write(result)

        console.print(
            f"[green]Processed transcript ({method}) saved to: {output_path}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error processing transcript: {str(e)}[/red]")
        raise
