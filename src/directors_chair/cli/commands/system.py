import psutil
from directors_chair.cli.utils import console

def system_check():
    console.print("[bold]Running System Health Check...[/bold]")
    
    # Check RAM
    total_ram = psutil.virtual_memory().total / (1024 ** 3)
    console.print(f"• RAM: {total_ram:.1f} GB")
    
    if total_ram < 16:
        console.print("[red]! Warning: Low RAM for Flux. Expect slow performance or crashes.[/red]")
    elif total_ram < 40:
        console.print("[yellow]! Recommendation: Use Quantized (4-bit) models for best performance.[/yellow]")
    else:
        console.print("[green]✓ RAM sufficient for full models.[/green]")
        
    # Check Dependencies
    dependencies = ["torch", "diffusers", "transformers", "mflux"]
    for dep in dependencies:
        try:
            __import__(dep)
            console.print(f"[green]✓ {dep} installed[/green]")
        except ImportError:
            console.print(f"[red]✗ {dep} NOT installed[/red]")
            
    input("\nPress Enter to return to menu...")
