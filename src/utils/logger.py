from rich.console import Console
from rich.theme import Theme
from rich.style import Style
from datetime import datetime
from typing import Optional
import sys
from rich.table import Table
from ..core.config import config

# Custom theme for consistent colors
THEME = Theme({
    'info': 'cyan',
    'warning': 'yellow', 
    'error': 'red',
    'success': 'green',
    'debug': 'dim blue',
    'timestamp': 'dim white',
    'recording': 'bold red',
    'transcribing': 'bold yellow',
    'done': 'bold green',
    'save': 'green',
    'header': 'bold magenta'  # Added header style
})

class Logger:
    def __init__(self):
        self.console = Console(theme=THEME)
        self.debug_mode = False
        
    def _format_message(self, message: str, style: Optional[str] = None) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[timestamp]{timestamp}[/timestamp] {message}"
        if style:
            formatted = f"[{style}]{message}[/{style}]\n"
        return formatted
        
    def info(self, message: str):
        """Log an informational message"""
        self.console.print(self._format_message(message, "info"))
        
    def warning(self, message: str):
        """Log a warning message"""
        self.console.print(self._format_message(f"⚠️  {message}\n", "warning"))
        
    def error(self, message: str):
        """Log an error message"""
        self.console.print(self._format_message(f"❌ {message}", "error"))
        
    def success(self, message: str):
        """Log a success message"""
        self.console.print(self._format_message(f"✅ {message}", "success"))
        
    def debug(self, message: str):
        """Log a debug message (only in debug mode)"""
        if self.debug_mode:
            self.console.print(self._format_message(f"🔍 {message}", "debug"))
            
    def recording(self, message: str):
        """Log a recording-related message"""
        self.console.print(self._format_message(f"🎤 {message}", "recording"))
        
    def transcribing(self, message: str):
        """Log a transcription-related message"""
        self.console.print(self._format_message(f"📝 {message}", "transcribing"))
        
    def save(self, message: str):
        """Log a transcription-related message"""
        self.console.print(self._format_message(f"💾 {message}", "save"))
        
    def status(self, message: str):
        """Update the current status"""
        self.console.print(self._format_message(message))

    def header(self, message: str):
        """Log a header message that stands out"""
        self.console.print(f"\n[header]═══ {message} ═══[/header]\n")
        
    def clear(self):
        """Clear the console"""
        self.console.clear()

    def print_header(self):
        """Print the app header."""
        self.clear()
        self.console.print("\n[bold blue]🎙️  Hacker Transcriber[/bold blue]")
        
    def print_instructions(self):
        """Print usage instructions."""
        # Print hotkeys
        self.console.print("\n[cyan]Hotkeys:[/cyan]")
        for action, hotkey in config.hotkeys.items():
            desc = action.replace('_', ' ').title()
            key_str = hotkey.replace('+', ' + ')
            self.console.print(f"  [cyan]{key_str:<20}[/cyan] {desc}")

        # Print commands
        self.console.print("\n[cyan]Commands:[/cyan]")
        for cmd, details in config.commands.items():
            if isinstance(details, dict) and 'description' in details:
                self.console.print(f"  [cyan]{cmd:<8}[/cyan] {details['description']}")
        
        self.console.print()

    def show_recording_status(self, is_recording: bool, is_paused: bool):
        """Show the current recording status."""
        if is_recording:
            status = "⏸️  Paused" if is_paused else "🔴  Recording..."
            style = "warning" if is_paused else "recording"
        else:
            status = "⏹️  Ready"
            style = "success"
            
        self.console.print(self._format_message(status, style))
        
    def show_audio_sources(self, mic: str, system: Optional[str] = None):
        """Display current audio sources."""
        self.info(f"Using microphone: {mic}")
        if system:
            self.info(f"System audio: {system}")

    def print_help(self):
        """Print detailed help information."""
        self.clear()
        self.print_header()
        
        # Commands section with table
        self.console.print("\n[bold cyan]Available Commands:[/bold cyan]")
        cmd_table = Table(show_header=False, padding=(0, 2))
        cmd_table.add_column(style="cyan", justify="left")
        cmd_table.add_column(style="white", justify="left")
        
        for cmd, details in config.commands.items():
            if isinstance(details, dict) and 'description' in details:
                cmd_table.add_row(cmd, details['description'])
        self.console.print(cmd_table)
        
        # Hotkeys section with table
        self.console.print("\n[bold cyan]Hotkeys:[/bold cyan]")
        hotkey_table = Table(show_header=False, padding=(0, 2))
        hotkey_table.add_column(style="cyan", justify="left")
        hotkey_table.add_column(style="white", justify="left")
        
        for action, details in config.hotkeys.items():
            if isinstance(details, dict) and 'key' in details and 'description' in details:
                key_str = details['key'].replace('+', ' + ')
                hotkey_table.add_row(key_str, details['description'])
        self.console.print(hotkey_table)
        
        # Features and tips remain the same
        self.console.print("\n[bold cyan]Recording Features:[/bold cyan]")
        self.console.print("  • Records from both microphone and system audio (if available)")
        self.console.print("  • Automatically transcribes after recording stops")
        self.console.print("  • Provides AI-powered summary and analysis")
        self.console.print("  • Saves recordings to the 'recordings' directory")
        
        self.console.print("\n[bold cyan]Tips:[/bold cyan]")
        self.console.print("  • Install BlackHole for system audio capture")
        self.console.print("  • Use 'devices' command to check audio inputs")
        self.console.print("  • Configure Whisper model in config for better accuracy")
        
        self.console.print("\nPress Enter to return to main screen...")

# Global logger instance
log = Logger() 