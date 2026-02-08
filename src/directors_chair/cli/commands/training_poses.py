import os
import io
import random
import json
import questionary
import requests
import fal_client
from PIL import Image
from rich.table import Table
from directors_chair.config.loader import load_config
from directors_chair.cli.utils import console


def _expand_poses(poses: list[str], gear: list[str]) -> list[str]:
    """Expand {gear} tokens in poses into one prompt per gear item."""
    expanded = []
    for pose in poses:
        if "{gear}" in pose:
            for item in gear:
                expanded.append(pose.replace("{gear}", item))
        else:
            expanded.append(pose)
    return expanded


def generate_training_poses():
    config = load_config()
    characters_dir = "characters"

    console.print("[bold]Generate Training Poses from Character Config[/bold]")
    console.print("[dim]Uses reference image for character consistency + varied pose prompts.[/dim]\n")

    # 1. Select character
    if not os.path.exists(characters_dir):
        console.print(f"[red]No characters/ directory found. Create one with prompt.txt and variations.json.[/red]")
        input("\nPress Enter to continue...")
        return

    characters = [d for d in os.listdir(characters_dir)
                  if os.path.isdir(os.path.join(characters_dir, d))]

    if not characters:
        console.print("[yellow]No characters found in characters/[/yellow]")
        input("\nPress Enter to continue...")
        return

    char_choice = questionary.select(
        "Select Character:",
        choices=sorted(characters) + ["Back"]
    ).ask()

    if not char_choice or char_choice == "Back":
        return

    char_dir = os.path.join(characters_dir, char_choice)

    # 2. Load character config
    prompt_path = os.path.join(char_dir, "prompt.txt")
    variations_path = os.path.join(char_dir, "variations.json")

    if not os.path.exists(prompt_path):
        console.print(f"[red]Missing {prompt_path}[/red]")
        input("\nPress Enter to continue...")
        return

    if not os.path.exists(variations_path):
        console.print(f"[red]Missing {variations_path}[/red]")
        input("\nPress Enter to continue...")
        return

    with open(prompt_path) as f:
        character_description = f.read().strip()

    with open(variations_path) as f:
        variations = json.load(f)

    hero_image = variations.get("hero_image", "")
    training_prompt = variations.get("training_prompt", "")
    gear = variations.get("gear", [])
    poses = variations.get("poses", [])

    if not hero_image or not os.path.exists(hero_image):
        console.print(f"[red]Hero image not found: {hero_image}[/red]")
        console.print("[yellow]Generate a hero image first (menu option 3), then update variations.json.[/yellow]")
        input("\nPress Enter to continue...")
        return

    # 3. Expand poses with gear
    expanded_poses = _expand_poses(poses, gear)

    # 4. Display plan
    table = Table(title=f"Training Poses for {char_choice}")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Pose Prompt", style="white")

    for i, pose in enumerate(expanded_poses):
        table.add_row(str(i + 1), pose)

    console.print(table)
    # Use training_prompt (short, CLIP-safe) if available, else fall back to full description
    if not training_prompt:
        console.print("[yellow]No training_prompt in variations.json — using full prompt.txt (may be truncated by CLIP 77-token limit)[/yellow]")
        prompt_base = character_description
    else:
        prompt_base = training_prompt

    console.print(f"\n[bold]Character:[/bold] {char_choice}")
    console.print(f"[bold]Hero image:[/bold] {hero_image}")
    console.print(f"[bold]Prompt base:[/bold] {prompt_base}")
    console.print(f"[bold]Total images:[/bold] {len(expanded_poses)}")
    console.print(f"[bold]Estimated cost:[/bold] ~${len(expanded_poses) * 0.07:.2f} (pose + photorealism pass)")

    # 5. Configuration
    identity_scale = float(questionary.text(
        "Identity scale (character preservation vs pose freedom, 0.0-2.0):",
        default="0.9"
    ).ask())

    # Check all composed prompts fit within CLIP's 77-token limit
    # CLIP tokenizes roughly by word with some subword splits; 65 words is a safe ceiling
    CLIP_WORD_LIMIT = 65
    too_long = []
    for i, pose in enumerate(expanded_poses):
        composed = f"{pose}, {prompt_base}"
        word_count = len(composed.split())
        if word_count > CLIP_WORD_LIMIT:
            too_long.append((i + 1, pose, word_count))

    if too_long:
        console.print(f"\n[red bold]Prompt too long — will be truncated by CLIP (77 token limit):[/red bold]")
        for num, pose, wc in too_long:
            console.print(f"  [red]#{num} ({wc} words): {pose}[/red]")
        console.print(f"\n[yellow]Shorten training_prompt or pose text in variations.json, then retry.[/yellow]")
        input("\nPress Enter to continue...")
        return

    if not questionary.confirm("Start generating training poses?").ask():
        return

    # 6. Setup output directory
    training_root = config["directories"]["training_data"]
    output_dir = os.path.join(training_root, char_choice)
    os.makedirs(output_dir, exist_ok=True)
    existing_count = len([f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    # 7. Upload hero image as reference
    console.print("\n[cyan]Uploading hero image to fal.ai...[/cyan]")
    hero_url = fal_client.upload_file(hero_image)

    # 8. Generate each pose
    for i, pose in enumerate(expanded_poses):
        idx = existing_count + i
        seed = random.randint(0, 2**32 - 1)
        # Pose FIRST so CLIP (77 token limit) sees the action; reference image handles appearance
        full_prompt = f"{pose}, {prompt_base}"

        console.print(f"\n[bold]Pose {i + 1}/{len(expanded_poses)}:[/bold] {pose}")

        with console.status("[cyan]Generating...[/cyan]") as status:
            handler = fal_client.submit(
                "fal-ai/instant-character",
                arguments={
                    "prompt": full_prompt,
                    "image_url": hero_url,
                    "scale": identity_scale,
                    "num_inference_steps": 40,
                    "guidance_scale": 5.0,
                    "negative_prompt": "cartoon, 3d render, CGI, animation, illustration, drawing, painting, anime, plastic, smooth skin, toy, clay, pixar, dreamworks, low quality, blurry",
                    "seed": seed,
                    "enable_safety_checker": False,
                    "output_format": "png",
                    "image_size": "square_hd",
                },
            )

            for event in handler.iter_events(with_logs=True):
                if isinstance(event, fal_client.InProgress):
                    if event.logs:
                        for log in event.logs:
                            status.update(f"[cyan]{log['message']}[/cyan]")

            result = handler.get()

        images = result.get("images", [])
        if not images or not images[0].get("url"):
            console.print(f"  [red]Failed - no image in response[/red]")
            continue

        pose_image_url = images[0]["url"]

        # Pass 2: Photorealism refinement via Kontext
        with console.status("[cyan]Refining for photorealism...[/cyan]") as status:
            refine_handler = fal_client.submit(
                "fal-ai/flux-pro/kontext",
                arguments={
                    "prompt": (
                        "Make this image photorealistic. Render as a practical VFX creature "
                        "photographed on 35mm film with harsh natural sunlight, highly detailed "
                        "wet skin textures, subsurface scattering, film grain, and cinematic "
                        "color grading. Keep the exact same pose, character, clothing, "
                        "composition, and framing unchanged."
                    ),
                    "image_url": pose_image_url,
                    "guidance_scale": 4.0,
                    "output_format": "png",
                    "safety_tolerance": "5",
                },
            )

            for event in refine_handler.iter_events(with_logs=True):
                if isinstance(event, fal_client.InProgress):
                    if event.logs:
                        for log in event.logs:
                            status.update(f"[cyan]{log['message']}[/cyan]")

            refine_result = refine_handler.get()

        refined_images = refine_result.get("images", [])
        if not refined_images or not refined_images[0].get("url"):
            console.print(f"  [yellow]Refinement failed — saving unrefined pose[/yellow]")
            final_url = pose_image_url
        else:
            final_url = refined_images[0]["url"]

        # Download
        response = requests.get(final_url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))

        # Save image
        img_path = os.path.join(output_dir, f"{char_choice}-{idx}.png")
        img.save(img_path)

        # Save caption (used by LoRA trainers)
        with open(os.path.join(output_dir, f"{char_choice}-{idx}.txt"), "w") as f:
            f.write(full_prompt)

        # Save metadata
        meta = {
            "prompt": full_prompt,
            "pose": pose,
            "seed": seed,
            "identity_scale": identity_scale,
            "hero_image": hero_image,
            "generator": "fal-ai/instant-character + fal-ai/flux-pro/kontext",
        }
        with open(os.path.join(output_dir, f"{char_choice}-{idx}.json"), "w") as f:
            json.dump(meta, f, indent=4)

        console.print(f"  [green]Saved: {char_choice}-{idx}.png[/green]")

    console.print(f"\n[bold green]Generated {len(expanded_poses)} training poses![/bold green]")
    console.print(f"Output: {output_dir}/")
    console.print(f"[yellow]Review and delete bad ones before training.[/yellow]")
    input("\nPress Enter to continue...")
