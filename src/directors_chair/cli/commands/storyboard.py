import os
import json
import random
import subprocess
import questionary
from rich.panel import Panel
from rich.table import Table
from directors_chair.config.loader import load_config
from directors_chair.generation import get_generator
from directors_chair.video import get_video_manager
from directors_chair.storyboard import load_storyboard, validate_storyboard
from directors_chair.cli.utils import console


def storyboard_to_video():
    config = load_config()

    # --- Select Storyboard File ---
    storyboard_dir = config.get("directories", {}).get("storyboards", "storyboards")
    if not os.path.exists(storyboard_dir):
        console.print(f"[red]Storyboard directory not found: {storyboard_dir}/[/red]")
        console.print("[yellow]Create a 'storyboards/' directory and add JSON files.[/yellow]")
        input("\nPress Enter to continue...")
        return

    json_files = [f for f in os.listdir(storyboard_dir) if f.endswith(".json")]
    if not json_files:
        console.print("[yellow]No storyboard JSON files found in storyboards/[/yellow]")
        input("\nPress Enter to continue...")
        return

    file_choice = questionary.select(
        "Select Storyboard:",
        choices=sorted(json_files) + ["Back"]
    ).ask()

    if not file_choice or file_choice == "Back":
        return

    storyboard_path = os.path.join(storyboard_dir, file_choice)
    storyboard = load_storyboard(storyboard_path)

    # --- Validate ---
    is_valid, errors = validate_storyboard(storyboard)
    if not is_valid:
        console.print("[red]Storyboard validation failed:[/red]")
        for err in errors:
            console.print(f"  [red]- {err}[/red]")
        input("\nPress Enter to continue...")
        return

    # --- Display Summary ---
    name = storyboard["name"]
    shots = storyboard["shots"]
    generator_name = storyboard.get("generator", config["system"].get("default_generator", "zimage-turbo"))
    loras = storyboard.get("loras", [])
    image_params = storyboard.get("image_params", {})
    video_params = storyboard.get("video_params", {})

    steps = image_params.get("steps", 25)
    resolution = video_params.get("resolution", "480p")
    num_frames = video_params.get("num_frames", 81)
    fps = video_params.get("fps", 16)

    table = Table(title=f"Storyboard: {name}")
    table.add_column("Shot", style="cyan", width=6)
    table.add_column("Image Prompt", style="white")
    table.add_column("Motion", style="green")

    for i, shot in enumerate(shots):
        motion = shot.get("motion", "(end keyframe)")
        table.add_row(str(i + 1), shot["image_prompt"], motion)

    console.print(table)
    console.print(f"\n[bold]Generator:[/bold] {generator_name}")
    console.print(f"[bold]LoRAs:[/bold] {[l['path'] for l in loras] if loras else 'None'}")
    console.print(f"[bold]Image:[/bold] steps={steps}")
    console.print(f"[bold]Video:[/bold] {resolution}, {num_frames} frames, {fps} fps")
    console.print(f"[bold]Clips to generate:[/bold] {len(shots) - 1}")
    cost = (len(shots) - 1) * (0.20 if resolution == "480p" else 0.40)
    console.print(f"[bold]Estimated cost:[/bold] ~${cost:.2f}")

    if not questionary.confirm("Proceed with keyframe generation?").ask():
        return

    # --- Setup Output Directories ---
    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    output_base = os.path.join(videos_dir, name)
    keyframes_dir = os.path.join(output_base, "keyframes")
    clips_dir = os.path.join(output_base, "clips")
    os.makedirs(keyframes_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    # --- Generate Keyframe Images ---
    lora_paths = [l["path"] for l in loras] if loras else None
    generator = get_generator(generator_name, lora_paths=lora_paths)

    keyframe_paths = []
    for i, shot in enumerate(shots):
        seed = random.randint(0, 2**32 - 1)
        console.print(f"\n[bold]Generating keyframe {i + 1}/{len(shots)}:[/bold] {shot['image_prompt']}")

        image = generator.generate(prompt=shot["image_prompt"], steps=steps, seed=seed)

        keyframe_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.png")
        image.save(keyframe_path)
        keyframe_paths.append(keyframe_path)

        metadata = {
            "prompt": shot["image_prompt"],
            "seed": seed,
            "steps": steps,
            "generator": generator_name,
            "shot_index": i,
        }
        meta_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)

        console.print(f"  Saved: {keyframe_path} (seed: {seed})")

    console.print(f"\n[bold green]All {len(shots)} keyframes generated![/bold green]")

    # --- Interactive Keyframe Review ---
    console.print(Panel(
        f"[bold]Review your keyframes before video generation.[/bold]\n\n"
        f"Keyframes saved to: {keyframes_dir}/\n"
        f"Open this folder and inspect each image.",
        title="Keyframe Review",
        border_style="yellow"
    ))

    while True:
        review_choice = questionary.select(
            "Keyframe Review:",
            choices=[
                "Accept all keyframes - proceed to video",
                "Re-generate a keyframe",
                "Abort storyboard"
            ]
        ).ask()

        if not review_choice or review_choice == "Abort storyboard":
            console.print("[yellow]Storyboard aborted. Keyframes remain on disk.[/yellow]")
            input("\nPress Enter to continue...")
            return

        if review_choice == "Accept all keyframes - proceed to video":
            break

        if review_choice == "Re-generate a keyframe":
            regen_choices = [f"Shot {i + 1}: {shots[i]['image_prompt'][:60]}" for i in range(len(shots))]
            regen_choice = questionary.select(
                "Which keyframe to re-generate?",
                choices=regen_choices + ["Cancel"]
            ).ask()

            if regen_choice and regen_choice != "Cancel":
                idx = regen_choices.index(regen_choice)
                new_seed = random.randint(0, 2**32 - 1)
                console.print(f"Re-generating keyframe {idx + 1} with seed {new_seed}...")
                image = generator.generate(prompt=shots[idx]["image_prompt"], steps=steps, seed=new_seed)
                image.save(keyframe_paths[idx])

                metadata = {
                    "prompt": shots[idx]["image_prompt"],
                    "seed": new_seed,
                    "steps": steps,
                    "generator": generator_name,
                    "shot_index": idx,
                }
                meta_path = os.path.join(keyframes_dir, f"keyframe_{idx:03d}.json")
                with open(meta_path, "w") as f:
                    json.dump(metadata, f, indent=4)

                console.print(f"  [green]Keyframe {idx + 1} re-generated.[/green]")

    # --- Generate Video Clips ---
    console.print(f"\n[bold]Starting video clip generation ({len(shots) - 1} clips)...[/bold]")

    video_manager = get_video_manager()
    clip_paths = []

    for i in range(len(shots) - 1):
        clip_path = os.path.join(clips_dir, f"clip_{i:03d}.mp4")
        clip_paths.append(clip_path)

        motion_prompt = shots[i]["motion"]
        console.print(f"\n[bold cyan]Clip {i + 1}/{len(shots) - 1}:[/bold cyan] {motion_prompt}")

        success = video_manager.generate_clip(
            prompt=motion_prompt,
            start_image_path=keyframe_paths[i],
            end_image_path=keyframe_paths[i + 1],
            output_path=clip_path,
            resolution=resolution,
            num_frames=num_frames,
            fps=fps,
        )

        if not success:
            console.print(f"  [red]Clip {i + 1} generation failed. Aborting.[/red]")
            input("\nPress Enter to continue...")
            return

        console.print(f"  [green]Clip {i + 1} saved.[/green]")

    console.print(f"\n[bold green]All {len(shots) - 1} clips generated![/bold green]")

    # --- Stitch with ffmpeg ---
    console.print("\n[bold]Stitching clips into final video...[/bold]")

    concat_list_path = os.path.join(output_base, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for clip_path in clip_paths:
            f.write(f"file '{os.path.abspath(clip_path)}'\n")

    final_video_path = os.path.join(output_base, f"{name}.mp4")

    try:
        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            final_video_path
        ])
        console.print(f"\n[bold green]Final video saved: {final_video_path}[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]ffmpeg stitching failed (exit code {e.returncode})[/red]")
        console.print(f"[yellow]Individual clips are available in: {clips_dir}/[/yellow]")
    except FileNotFoundError:
        console.print("[red]ffmpeg not found. Please install ffmpeg (brew install ffmpeg).[/red]")
        console.print(f"[yellow]Individual clips are available in: {clips_dir}/[/yellow]")

    # Cleanup concat list
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    input("\nPress Enter to continue...")
