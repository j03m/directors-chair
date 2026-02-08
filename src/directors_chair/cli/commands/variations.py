import os
import io
import random
import json
import questionary
import requests
import fal_client
from PIL import Image
from directors_chair.config.loader import load_config
from directors_chair.cli.utils import console


def generate_variations():
    config = load_config()
    training_root = config["directories"]["training_data"]

    # 1. Select source image
    console.print("[bold]Generate character variations from a reference image[/bold]")
    console.print("[dim]Uses fal.ai img2img to create consistent character variations for LoRA training.[/dim]\n")

    # Find images across training_data and assets
    image_sources = []

    if os.path.exists(training_root):
        for dataset in sorted(os.listdir(training_root)):
            dataset_path = os.path.join(training_root, dataset)
            if os.path.isdir(dataset_path):
                for f in sorted(os.listdir(dataset_path)):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_sources.append(os.path.join(dataset_path, f))

    if not image_sources:
        console.print("[red]No images found in training data. Generate a hero image first![/red]")
        input("\nPress Enter to continue...")
        return

    # Show relative paths for readability
    display_choices = [os.path.relpath(p) for p in image_sources]
    source_choice = questionary.select(
        "Select reference image:",
        choices=display_choices + ["Back"]
    ).ask()

    if not source_choice or source_choice == "Back":
        return

    source_idx = display_choices.index(source_choice)
    source_path = image_sources[source_idx]
    console.print(f"[green]Reference: {source_choice}[/green]")

    # 2. Load the prompt from the companion .txt or .json file
    base_name = os.path.splitext(source_path)[0]
    source_prompt = ""

    if os.path.exists(f"{base_name}.txt"):
        with open(f"{base_name}.txt") as f:
            source_prompt = f.read().strip()
    elif os.path.exists(f"{base_name}.json"):
        with open(f"{base_name}.json") as f:
            meta = json.load(f)
            source_prompt = meta.get("prompt", "")

    if source_prompt:
        console.print(f"[dim]Prompt: {source_prompt[:100]}...[/dim]")
    else:
        source_prompt = questionary.text("No prompt found. Enter character description:").ask()
        if not source_prompt:
            return

    # 3. Configuration
    count = int(questionary.text("Number of variations:", default="12").ask())
    strength = float(questionary.text(
        "Variation strength (0.3=subtle, 0.6=moderate, 0.9=dramatic):",
        default="0.6"
    ).ask())

    # Output goes to same dataset directory as the source
    output_dir = os.path.dirname(source_path)
    existing_count = len([f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    console.print(f"\n[bold]Plan:[/bold]")
    console.print(f"  Reference: {source_choice}")
    console.print(f"  Variations: {count}")
    console.print(f"  Strength: {strength}")
    console.print(f"  Output: {output_dir}/ (starting at index {existing_count})")
    console.print(f"  Estimated cost: ~${count * 0.03:.2f}")

    if not questionary.confirm("Start generating variations?").ask():
        return

    # 4. Upload reference image
    console.print("\n[cyan]Uploading reference image to fal.ai...[/cyan]")
    image_url = fal_client.upload_file(source_path)

    # 5. Generate variations
    dataset_name = os.path.basename(output_dir)
    # Extract a base name from the first image file
    first_image_base = os.path.splitext(os.path.basename(source_path))[0]
    name_prefix = first_image_base.split("-")[0] if "-" in first_image_base else first_image_base

    for i in range(count):
        idx = existing_count + i
        seed = random.randint(0, 2**32 - 1)

        console.print(f"\n[bold]Variation {i + 1}/{count}[/bold] (seed: {seed})")

        handler = fal_client.submit(
            "fal-ai/flux/dev/image-to-image",
            arguments={
                "image_url": image_url,
                "prompt": source_prompt,
                "strength": strength,
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "seed": seed,
                "enable_safety_checker": False,
                "output_format": "png",
            },
        )

        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress):
                if event.logs:
                    for log in event.logs:
                        console.print(f"    [dim]{log['message']}[/dim]")

        result = handler.get()

        images = result.get("images", [])
        if not images or not images[0].get("url"):
            console.print(f"  [red]Failed - no image in response[/red]")
            continue

        # Download
        response = requests.get(images[0]["url"])
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))

        # Save image
        img_path = os.path.join(output_dir, f"{name_prefix}-{idx}.png")
        img.save(img_path)

        # Save caption
        with open(os.path.join(output_dir, f"{name_prefix}-{idx}.txt"), "w") as f:
            f.write(source_prompt)

        # Save metadata
        meta = {
            "prompt": source_prompt,
            "seed": seed,
            "strength": strength,
            "reference_image": source_choice,
            "generator": "fal-ai/flux/dev/image-to-image",
        }
        with open(os.path.join(output_dir, f"{name_prefix}-{idx}.json"), "w") as f:
            json.dump(meta, f, indent=4)

        console.print(f"  [green]Saved: {name_prefix}-{idx}.png[/green]")

    console.print(f"\n[bold green]Generated {count} variations![/bold green]")
    console.print(f"Output: {output_dir}/")
    console.print(f"[yellow]Review and delete bad ones before training.[/yellow]")
    input("\nPress Enter to continue...")
