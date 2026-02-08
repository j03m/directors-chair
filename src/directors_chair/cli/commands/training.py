import os
import questionary
from rich.panel import Panel
from directors_chair.config.loader import load_config, save_config
from directors_chair.training.manager import get_training_manager, TRAINING_ENGINES
from directors_chair.cli.utils import console


def train_lora_command():
    config = load_config()
    training_root = config["directories"]["training_data"]

    # 0. Select Training Engine
    engine_choices = [f"{label} [{key}]" for key, (label, _) in TRAINING_ENGINES.items()]
    engine_choice = questionary.select(
        "Select Training Engine:",
        choices=engine_choices + ["Back"]
    ).ask()

    if not engine_choice or engine_choice == "Back":
        return

    engine_key = engine_choice.split("[")[-1].rstrip("]")
    is_fal = engine_key.startswith("fal-")
    is_wan = (engine_key == "fal-wan")
    is_fal_flux = (engine_key == "fal-flux")

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

    if not dataset_choice or dataset_choice == "Back":
        return

    default_trigger = dataset_choice.split("_")[0] if "_" in dataset_choice else "trigger"
    dataset_path = os.path.join(training_root, dataset_choice)

    # Check file count
    image_files = [f for f in os.listdir(dataset_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    file_count = len(image_files)

    recommended_images = 10 if is_wan else 4 if is_fal_flux else 1
    if file_count < recommended_images:
        console.print(f"[yellow]Warning: {recommended_images}+ images recommended for best results. Found {file_count}.[/yellow]")
        if not questionary.confirm(f"Continue with {file_count} images anyway?").ask():
            return

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

    # 2. Gather Parameters
    console.print(f"[bold]Configuring LoRA for {dataset_choice}[/bold]")

    if is_wan:
        default_name = f"{dataset_choice}_wan"
    elif is_fal_flux:
        default_name = dataset_choice
    else:
        default_name = dataset_choice

    lora_name = questionary.text("LoRA Name:", default=default_name).ask()
    trigger_word = questionary.text("Trigger Word:", default=default_trigger).ask()

    # Engine-specific params
    selected_model_id = ""
    selected_model_key = ""
    base_model_type = ""
    rank = 4
    learning_rate = 0.0002

    if is_wan:
        steps = int(questionary.text("Training Steps:", default="400").ask())
        learning_rate = float(questionary.text("Learning Rate:", default="0.0002").ask())

        console.print(f"\n[bold]Plan:[/bold] Train WAN video LoRA '{lora_name}'")
        console.print(f"  Trigger: {trigger_word}")
        console.print(f"  Steps: {steps}, LR: {learning_rate}")
        console.print(f"  Engine: fal-ai/wan-trainer")

    elif is_fal_flux:
        steps = int(questionary.text("Training Steps:", default="1000").ask())

        console.print(f"\n[bold]Plan:[/bold] Train Flux image LoRA '{lora_name}'")
        console.print(f"  Trigger: {trigger_word}")
        console.print(f"  Steps: {steps}")
        console.print(f"  Estimated cost: ~${steps * 0.002:.2f}")
        console.print(f"  Engine: fal-ai/flux-lora-fast-training")

    else:
        # mflux local
        model_ids = config.get("model_ids", {})
        default_model_key = config.get("training", {}).get("default_base_model", "flux-schnell")

        selected_model_key = questionary.select(
            "Select Base Model for Training:",
            choices=list(model_ids.keys()),
            default=default_model_key
        ).ask()

        selected_model_id = model_ids[selected_model_key]

        if "schnell" in selected_model_key or "schnell" in selected_model_id:
            base_model_type = "schnell"
        elif "dev" in selected_model_key or "dev" in selected_model_id:
            base_model_type = "dev"
        elif "z-image-turbo" in selected_model_key:
            base_model_type = "z-image-turbo"
        else:
            base_model_type = "schnell"

        steps = int(questionary.text("Training Steps/Epochs:", default="1000").ask())
        rank = int(questionary.text("LoRA Rank (Complexity):", default="4").ask())

        console.print(f"\n[bold]Plan:[/bold] Train LoRA '{lora_name}' locally")
        console.print(f"  Base Model: {selected_model_key} ({base_model_type})")
        console.print(f"  Trigger: {trigger_word}")
        console.print(f"  Steps: {steps}, Rank: {rank}")

    # 3. Train
    if questionary.confirm("Start Training?").ask():
        manager = get_training_manager(engine_name=engine_key)

        train_kwargs = {
            "dataset_path": dataset_path,
            "output_name": lora_name,
            "trigger_word": trigger_word,
            "steps": steps,
        }

        if is_wan:
            train_kwargs["learning_rate"] = learning_rate
        elif not is_fal:
            # mflux local
            train_kwargs["model_id"] = selected_model_id
            train_kwargs["base_model_type"] = base_model_type
            train_kwargs["rank"] = rank

        success = manager.train_lora(**train_kwargs)

        if success:
            if "loras" not in config:
                config["loras"] = {}

            if is_wan:
                lora_type = "wan"
                base_model = "wan-2.1"
            elif is_fal_flux:
                lora_type = "flux"
                base_model = "fal-flux"
            else:
                lora_type = "flux"
                base_model = selected_model_key

            lora_entry = {
                "path": os.path.join("assets", "loras", f"{lora_name}.safetensors"),
                "trigger": trigger_word,
                "type": lora_type,
                "base_model": base_model,
            }

            # For fal.ai engines, store the remote URL for inference
            if is_fal and hasattr(manager.engine, 'last_lora_url') and manager.engine.last_lora_url:
                lora_entry["fal_url"] = manager.engine.last_lora_url

            config["loras"][lora_name] = lora_entry
            save_config(config)
            console.print("[green]LoRA registered in config.json[/green]")
            input("\nPress Enter to continue...")
        else:
            input("\nTraining failed. Press Enter to continue...")
