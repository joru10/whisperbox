from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.console import Console
from rich.align import Align
from rich import box
from typing import Optional
import time

console = Console()

class TranscriberUI:
    def __init__(self):
        self.layout = Layout()
        self.recording_time = 0
        self.recording_start_time = None
        self.is_recording = False
        self.is_paused = False
        self.current_mic = "Default Microphone"
        self.current_system = "System Audio (BlackHole)"
        self.status_message = ""
        self.setup_layout()
        
    def setup_layout(self):
        """Setup the initial layout structure."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        # Split main area into left and right columns
        self.layout["main"].split_row(
            Layout(name="status", ratio=2),
            Layout(name="controls", ratio=1),
        )
        
    def _make_header(self) -> Panel:
        """Create the header panel."""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        
        grid.add_row(
            Text("🎙️ Hacker Transcriber", style="bold blue", justify="center")
        )
        
        return Panel(grid, style="blue")
        
    def _make_status(self) -> Panel:
        """Create the status panel."""
        status_table = Table(show_header=False, box=box.SIMPLE, expand=True)
        status_table.add_column("Label", style="blue", width=15)
        status_table.add_column("Value")
        
        # Recording status with emoji
        status = "⏺️ Recording" if self.is_recording else "⏹️ Stopped"
        if self.is_paused:
            status = "⏸️ Paused"
            
        status_style = "bold red" if self.is_recording else "bold white"
        status_table.add_row("Status:", Text(status, style=status_style))
        
        # Recording time
        if self.is_recording and self.recording_start_time:
            elapsed = time.time() - self.recording_start_time
            time_str = time.strftime("%M:%S", time.gmtime(elapsed))
            status_table.add_row("Duration:", time_str)
        
        # Audio sources
        status_table.add_row("Microphone:", self.current_mic)
        status_table.add_row("System Audio:", self.current_system)
        
        # Status message (if any)
        if self.status_message:
            status_table.add_row("Message:", Text(self.status_message, style="yellow"))
            
        return Panel(
            Align.center(status_table),
            title="Status",
            border_style="blue",
        )
        
    def _make_controls(self) -> Panel:
        """Create the controls panel."""
        controls_table = Table(show_header=False, box=box.SIMPLE, expand=True)
        controls_table.add_column("Key", style="cyan", width=12)
        controls_table.add_column("Action")
        
        controls_table.add_row("Ctrl+R", "Start Recording")
        controls_table.add_row("Ctrl+S", "Stop Recording")
        controls_table.add_row("Ctrl+Shift+P", "Pause/Resume")
        controls_table.add_row("Ctrl+Shift+Q", "Quit")
        controls_table.add_row("Ctrl+M", "Change Mic")
        controls_table.add_row("Ctrl+A", "Change Audio")
        
        return Panel(
            Align.center(controls_table),
            title="Controls",
            border_style="blue"
        )
        
    def _make_footer(self) -> Panel:
        """Create the footer panel."""
        return Panel(
            Text(
                "Press Ctrl+Shift+Q to quit",
                justify="center",
                style="italic"
            ),
            style="blue"
        )
        
    def update_content(self):
        """Update all layout content."""
        self.layout["header"].update(self._make_header())
        self.layout["status"].update(self._make_status())
        self.layout["controls"].update(self._make_controls())
        self.layout["footer"].update(self._make_footer())
        
    def set_status(self, message: str):
        """Update the status message."""
        self.status_message = message
        
    def start_recording(self):
        """Update UI for recording start."""
        self.is_recording = True
        self.is_paused = False
        self.recording_start_time = time.time()
        self.status_message = "Recording in progress..."
        
    def stop_recording(self):
        """Update UI for recording stop."""
        self.is_recording = False
        self.is_paused = False
        self.recording_start_time = None
        self.status_message = "Recording stopped"
        
    def toggle_pause(self):
        """Update UI for pause toggle."""
        if self.is_recording:
            self.is_paused = not self.is_paused
            self.status_message = "Recording paused" if self.is_paused else "Recording resumed"
            
    def set_audio_sources(self, mic: str, system: Optional[str] = None):
        """Update audio source information."""
        self.current_mic = mic
        if system:
            self.current_system = system 