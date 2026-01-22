import os
import shutil
import time
import questionary
from directors_chair.config.loader import load_config, save_config
from directors_chair.assets import download_model
from directors_chair.cli.utils import console

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
