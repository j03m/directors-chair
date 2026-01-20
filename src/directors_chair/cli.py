import sys
import os
import shutil
import psutil
import platform
import time
from rich.console import Console
from rich.panel import Panel
import questionary
from directors_chair.config.loader import load_config, save_config, get_prompt
from directors_chair.model_manager import download_model
from directors_chair.factory import get_generator

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

def manage_models():
    config = load_config()
    models = config.get("model_ids", {})
    
    choices = list(models.keys()) + ["Download New Model", "Back"]
    
    choice = questionary.select(
        "Model Management:",
        choices=choices
    ).ask()
    
    if choice == "Back":
        return
        
    if choice == "Download New Model":
        console.print("[yellow]Please manually add model ID to config.json first.[/yellow]")
        time.sleep(2)
        return

    # Check if model exists locally
    model_id = models[choice]
    model_dir = os.path.join(config["directories"]["models"], choice)
    
    if os.path.exists(model_dir):
        # Even if empty, let them delete it to clean up state
        file_count = len(os.listdir(model_dir))
        status_msg = f"[green]✓ Model '{choice}' found at {model_dir} ({file_count} files)[/green]" if file_count > 0 else f"[yellow]! Model folder exists but is empty: {model_dir}[/yellow]"
        console.print(status_msg)
        
        action = questionary.select(
            f"Actions for {choice}:",
            choices=["Set as Default", "Delete", "Back"]
        ).ask()
        
        if action == "Set as Default":
            config["system"]["default_generator"] = choice
            save_config(config)
            console.print(f"[green]Set {choice} as default generator.[/green]")
            time.sleep(1)
        elif action == "Delete":
            if questionary.confirm(f"Are you sure you want to delete {choice}?").ask():
                shutil.rmtree(model_dir)
                console.print(f"[green]Deleted {model_dir}[/green]")
                time.sleep(1)
    else:
        console.print(f"[yellow]! Model '{choice}' not found locally.[/yellow]")
        if questionary.confirm(f"Download {choice} ({model_id}) now?").ask():
            # Trigger download
            success = download_model(model_id, model_dir)
            if success:
                if questionary.confirm("Set as default generator?").ask():
                    config["system"]["default_generator"] = choice
                    save_config(config)
                input("\nPress Enter to continue...")
            else:
                input("\nDownload failed. Press Enter to continue...")


def generate_images():
    config = load_config()
    themes = config.get("themes", {})
    available_generators = list(config.get("model_ids", {}).keys())
    default_generator = config["system"].get("default_generator", "zimage-turbo")
    
    theme_choices = ["Create New Theme"] + list(themes.keys()) + ["Back"]
    
    choice = questionary.select(
        "Select Theme:",
        choices=theme_choices
    ).ask()
    
    if choice == "Back":
        return
        
    name, trigger, prompt_text, count, generator_choice, steps, guidance = "", "", "", 1, default_generator, 25, 3.5
    
    if choice == "Create New Theme":
        name = questionary.text("Character/Subject Name (e.g. 'gorilla'):").ask()
        trigger = questionary.text("Trigger Word (e.g. 'viking'):").ask()
        prompt_text = questionary.text("Prompt Concept:").ask()
        count = int(questionary.text("Number of Images:", default="20").ask())
        
        # Extended Attributes
        generator_choice = questionary.select("Select Generator:", choices=available_generators, default=default_generator).ask()
        steps = int(questionary.text("Steps:", default="25").ask())
        guidance = float(questionary.text("Guidance Scale:", default="3.5").ask())
        
        if questionary.confirm("Save this theme?").ask():
            theme_key = f"{trigger}_{name}".replace(" ", "_")
            config["themes"][theme_key] = {
                "trigger": trigger,
                "prompt_file": prompt_text,
                "count": count,
                "generator": generator_choice,
                "parameters": {
                    "steps": steps,
                    "guidance": guidance
                }
            }
            save_config(config)
            console.print(f"[green]Theme saved as {theme_key}[/green]")
            
    elif choice in themes:
        theme = themes[choice]
        console.print(f"Loaded Theme: [cyan]{choice}[/cyan]")
        name = choice.split("_")[-1] # simplistic
        trigger = theme["trigger"]
        prompt_text = get_prompt(theme["prompt_file"])
        count = theme.get("count", 20)
        generator_choice = theme.get("generator", default_generator)
        
        params = theme.get("parameters", {})
        steps = params.get("steps", 25)
        guidance = params.get("guidance", 3.5)
        
        console.print(f"Generator: {generator_choice} | Steps: {steps} | Guidance: {guidance}")
        
        # Display the full prompt construction so the user understands
        full_prompt_preview = f"{trigger} {name}, {prompt_text}"
        console.print(Panel(f"[bold]Effective Prompt:[/bold]\n{full_prompt_preview}", title="Prompt Preview", border_style="cyan"))

        # Allow override
        if not questionary.confirm(f"Generate {count} images with these settings?").ask():
             if questionary.confirm("Change settings?").ask():
                prompt_text = questionary.text("Prompt Concept:", default=prompt_text).ask()
                count = int(questionary.text("Number of Images:", default=str(count)).ask())
                generator_choice = questionary.select("Select Generator:", choices=available_generators, default=generator_choice).ask()
                steps = int(questionary.text("Steps:", default=str(steps)).ask())

    # Execution
    console.print(f"\n[bold]Plan:[/bold] Generate {count} images for '{name}' using {generator_choice}.")
    if questionary.confirm("Start Generation?").ask():
         output_dir = os.path.join(config["directories"]["training_data"], f"{trigger}_{name}")
         if not os.path.exists(output_dir):
             os.makedirs(output_dir)

         # Construct full prompt
         full_prompt = f"{trigger} {name}, {prompt_text}"

         # Instantiate Generator
         generator = get_generator(generator_choice)
         
         for i in range(count):
            image = generator.generate(prompt=full_prompt, steps=steps, seed=42)
            image.save(os.path.join(output_dir, f"{name}-{i}.png"))

         console.print("[bold green]Generation Complete![/bold green]")
         console.print(f"Images saved to: {output_dir}")
         input("\nPress Enter to continue...")

def main_menu():
    while True:
        print_header()
        
        choice = questionary.select(
            "Main Menu",
            choices=[
                "1. System Setup & Health Check",
                "2. Manage Models",
                "3. Generate Training Images",
                "4. Exit"
            ]
        ).ask()
        
        if not choice: # Handle cancellation (Ctrl+C)
            sys.exit(0)
            
        if "1." in choice:
            system_check()
        elif "2." in choice:
            manage_models()
        elif "3." in choice:
            generate_images()
        elif "4." in choice:
            console.print("Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Exiting...[/red]")
        sys.exit(0)