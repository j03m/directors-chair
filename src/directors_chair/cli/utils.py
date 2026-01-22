import os
import platform
import psutil
from rich.console import Console
from rich.panel import Panel

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    
    # System Info
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    system_os = platform.system()
    processor = platform.processor()
    
    # Check for MPS
    try:
        import torch
        mps_available = torch.backends.mps.is_available()
        gpu_status = "MPS Available" if mps_available else "CPU Only"
    except ImportError:
        gpu_status = "Torch Not Found"

    header_text = f"""
[bold gold1]🎬 DIRECTOR'S CHAIR 🎬[/bold gold1]
[italic]AI Image Generation & Training Kit[/italic]

[cyan]System:[/cyan] {system_os} ({processor}) | [cyan]RAM:[/cyan] {ram_gb} GB | [cyan]Accelerator:[/cyan] {gpu_status}
    """
    console.print(Panel(header_text.strip(), border_style="gold1"))
