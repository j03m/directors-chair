import os
import questionary
from rich.panel import Panel
from directors_chair.config.loader import load_config, save_config
from directors_chair.training.manager import get_training_manager
from directors_chair.cli.utils import console

def train_lora_command():
    config = load_config()
    training_root = config["directories"]["training_data"]
    
    # 1. Select Dataset
    if not os.path.exists(training_root):
        console.print(f"[red]Training data directory not found: {training_root}[/red]")
        return

    datasets = [d for d in os.listdir(training_root) if os.path.isdir(os.path.join(training_root, d))]
    
    if not datasets:
        console.print("[yellow]No datasets found. Generate images first![/yellow]")
        return

    dataset_choice = questionary.select(
        "Select Dataset to Train On:",
        choices=datasets + ["Back"]
    ).ask()
    
    if dataset_choice == "Back":
        return

    # 2. Gather Parameters
    # Try to guess trigger word from folder name "trigger_name"
    default_trigger = dataset_choice.split("_")[0] if "_" in dataset_choice else "trigger"
    dataset_path = os.path.join(training_root, dataset_choice)
    
    # Check file count
    image_files = [f for f in os.listdir(dataset_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    file_count = len(image_files)
    
    console.print(Panel(
        f"[bold]Dataset Check:[/bold]\n"
        f"Found {file_count} images in '{dataset_choice}'.\n\n"
        f"[yellow]Important: The training will use ALL images in this folder.\n"
        f"Please manually delete any bad generations from '{dataset_path}' before continuing.[/yellow]",
        border_style="yellow"
    ))
    
    if not questionary.confirm("Are these images ready for training?").ask():
        console.print("[yellow]Aborted. Go curate your dataset![/yellow]")
        return

    console.print(f"[bold]Configuring LoRA for {dataset_choice}[/bold]")
    
    # Model Selection
    model_ids = config.get("model_ids", {})
    default_model_key = config.get("training", {}).get("default_base_model", "flux-schnell")
    
    model_choices = list(model_ids.keys())
    selected_model_key = questionary.select(
        "Select Base Model for Training:",
        choices=model_choices,
        default=default_model_key
    ).ask()
    
    selected_model_id = model_ids[selected_model_key]
    
    # Determine base model type (schnell vs dev vs z-image-turbo)
    # Heuristic: check string content or use a manual mapping if needed.
    if "schnell" in selected_model_key or "schnell" in selected_model_id:
        base_model_type = "schnell"
    elif "dev" in selected_model_key or "dev" in selected_model_id:
        base_model_type = "dev"
    elif "z-image-turbo" in selected_model_key:
        base_model_type = "z-image-turbo"
    else:
        # Fallback or ask user? Let's default to schnell for safety if unsure, or ask.
        base_model_type = "schnell" 

    lora_name = questionary.text("LoRA Name (e.g. 'viking_gorilla_v1'):", default=dataset_choice).ask()
    trigger_word = questionary.text("Trigger Word:", default=default_trigger).ask()
    steps = int(questionary.text("Training Steps/Epochs:", default="1000").ask())
    rank = int(questionary.text("LoRA Rank (Complexity):", default="16").ask())

    # 3. Confirm
    console.print(f"\n[bold]Plan:[/bold] Train LoRA '{lora_name}' on '{dataset_choice}'")
    console.print(f"• Base Model: {selected_model_key} ({base_model_type})")
    console.print(f"• Trigger: {trigger_word}")
    console.print(f"• Steps: {steps}")
    console.print(f"• Rank: {rank}")
    
    if questionary.confirm("Start Training? (This will take time)").ask():
        manager = get_training_manager()
        success = manager.train_lora(
            dataset_path=dataset_path,
            output_name=lora_name,
            trigger_word=trigger_word,
            model_id=selected_model_id,
            base_model_type=base_model_type,
            steps=steps,
            rank=rank
        )
        
        if success:
            # Update config to register this new LoRA
            if "loras" not in config:
                config["loras"] = {}
            
            config["loras"][lora_name] = {
                "path": os.path.join("assets", "loras", f"{lora_name}.safetensors"),
                "trigger": trigger_word,
                "base_model": "z-image-turbo"
            }
            save_config(config)
            console.print("[green]LoRA registered in config.json[/green]")
            input("\nPress Enter to continue...")
        else:
            input("\nTraining failed. Press Enter to continue...")
