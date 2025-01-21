from rich.console import Console
from .ai_service import AIService
from .config import config

console = Console()


def process_transcript(transcript_path: str) -> None:
    """Process a transcript with AI to generate additional insights.

    Args:
        transcript_path (str): Path to the markdown transcript file
    """
    try:
        with open(transcript_path, "r") as f:
            transcript_text = f.read()

        # Remove the markdown header to get clean text
        clean_text = transcript_text.replace("# Meeting Transcription\n\n", "").strip()

        # Process with AI service
        ai_service = AIService()
        prompt = config.ai.prompts.process_transcript.format(text=clean_text)
        result = ai_service.query(prompt)

        # Save the processed result
        output_path = transcript_path.replace(".md", "_processed.md")
        with open(output_path, "w") as f:
            f.write(result)

        console.print(f"[green]Processed transcript saved to: {output_path}[/green]")

    except Exception as e:
        console.print(f"[red]Error processing transcript: {str(e)}[/red]")
        raise
