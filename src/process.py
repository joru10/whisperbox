from rich.console import Console
from .ai_service import AIService
from .config import config
from typing import Optional, List

console = Console()


def get_available_processors() -> List[str]:
    """Get list of available processing methods from config."""
    return list(config.ai.prompts.processing.keys())


def process_transcript(transcript_path: str, method: Optional[str] = None) -> None:
    """Process a transcript with AI to generate additional insights.

    Args:
        transcript_path (str): Path to the markdown transcript file
        method (str, optional): Processing method to use. Must be one defined in config.ai.prompts.processing
    """
    try:
        with open(transcript_path, "r") as f:
            transcript_text = f.read()

        # Remove the markdown header to get clean text
        clean_text = transcript_text.replace("# Meeting Transcription\n\n", "").strip()

        # Get the appropriate prompt for the method
        if not method or not hasattr(config.ai.prompts.processing, method):
            available = get_available_processors()
            raise ValueError(
                f"Unknown processing method: {method}. Available methods: {', '.join(available)}"
            )

        prompt = config.ai.prompts.processing[method].format(text=clean_text)

        # Process with AI service
        ai_service = AIService()
        result = ai_service.query(prompt)

        # Save the processed result
        output_path = transcript_path.replace(".md", f"_{method}.md")
        with open(output_path, "w") as f:
            f.write(f"# Meeting {method.replace('-', ' ').title()}\n\n")
            f.write(result)

        console.print(
            f"[green]Processed transcript ({method}) saved to: {output_path}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error processing transcript: {str(e)}[/red]")
        raise
