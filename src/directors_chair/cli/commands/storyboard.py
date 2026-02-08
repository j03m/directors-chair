import os
import io
import json
import random
import subprocess
import questionary
import requests
import fal_client
from PIL import Image
from rich.panel import Panel
from rich.table import Table
from directors_chair.config.loader import load_config
from directors_chair.generation import get_generator
from directors_chair.video.manager import get_video_manager, VIDEO_ENGINES, DEFAULT_ENGINE
from directors_chair.storyboard import load_storyboard, validate_storyboard
from directors_chair.cli.utils import console


# --- Technique Registry ---
STITCH_MODES = {
    "chain": "Chain — continuous long take, last frame feeds next clip",
    "scene": "Scene — fresh keyframe per shot via Kontext, crossfade transitions",
}


def _extract_last_frame(clip_path: str, output_path: str):
    """Extract the last frame of an mp4 as a PNG using ffmpeg."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", clip_path],
        capture_output=True, text=True
    )
    total_frames = int(result.stdout.strip())

    subprocess.check_call([
        "ffmpeg", "-y",
        "-i", clip_path,
        "-vf", f"select=eq(n\\,{total_frames - 1})",
        "-vframes", "1",
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _generate_keyframe_kontext(scene_prompt: str, reference_image: str, output_path: str):
    """Generate a keyframe by editing the hero image via Kontext."""
    console.print(f"  [dim]Hero: {reference_image}[/dim]")

    with console.status("[cyan]Uploading hero image...[/cyan]"):
        ref_url = fal_client.upload_file(reference_image)

    with console.status("[cyan]Generating keyframe via Kontext...[/cyan]") as status:
        handler = fal_client.submit(
            "fal-ai/flux-pro/kontext",
            arguments={
                "prompt": scene_prompt,
                "image_url": ref_url,
                "guidance_scale": 4.0,
                "output_format": "png",
                "safety_tolerance": "5",
            },
        )
        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress) and event.logs:
                for log in event.logs:
                    status.update(f"[cyan]{log['message']}[/cyan]")
        result = handler.get()

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        console.print("[red]Keyframe generation failed — no image in response[/red]")
        return False

    response = requests.get(images[0]["url"])
    response.raise_for_status()
    img = Image.open(io.BytesIO(response.content))
    img.save(output_path)
    return True


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
    reference_image = storyboard.get("reference_image", "")

    steps = image_params.get("steps", 25)
    resolution = video_params.get("resolution", "480p")
    num_frames = video_params.get("num_frames", 81)
    fps = video_params.get("fps", 16)

    table = Table(title=f"Storyboard: {name}")
    table.add_column("Shot", style="cyan", width=6)
    table.add_column("Scene", style="white")
    table.add_column("Motion", style="green")

    for i, shot in enumerate(shots):
        scene = shot.get("image_prompt", "")
        motion = shot.get("motion", "")
        table.add_row(
            str(i + 1),
            scene[:80] + "..." if len(scene) > 80 else scene,
            motion[:80] + "..." if len(motion) > 80 else motion,
        )

    console.print(table)
    console.print(f"\n[bold]Reference image:[/bold] {reference_image or 'None'}")
    console.print(f"[bold]Video:[/bold] {resolution}, {num_frames} frames, {fps} fps")

    num_clips = sum(1 for s in shots if s.get("motion"))
    cost = num_clips * (0.20 if resolution == "480p" else 0.40)
    console.print(f"[bold]Clips:[/bold] {num_clips}")
    console.print(f"[bold]Estimated cost:[/bold] ~${cost:.2f}")

    if not questionary.confirm("Proceed?").ask():
        return

    # --- Select Stitch Mode ---
    mode_choices = [f"{k} — {v}" for k, v in STITCH_MODES.items()]
    mode_choice = questionary.select(
        "Select stitch mode:",
        choices=mode_choices,
    ).ask()

    if not mode_choice:
        return

    stitch_mode = mode_choice.split(" — ")[0]
    console.print(f"[bold]Stitch mode:[/bold] {stitch_mode}")

    # --- Select Video Engine ---
    engine_choices = [f"{label} [{key}]" for key, (label, _) in VIDEO_ENGINES.items()]
    default_label = next(f"{label} [{key}]" for key, (label, _) in VIDEO_ENGINES.items() if key == DEFAULT_ENGINE)
    engine_choice = questionary.select(
        "Select video engine:",
        choices=engine_choices,
        default=default_label,
    ).ask()

    if not engine_choice:
        return

    engine_key = engine_choice.split("[")[-1].rstrip("]")
    console.print(f"[bold]Engine:[/bold] {engine_key}")

    # --- Video LoRA Selection (for fal-wan-i2v-lora engine) ---
    engine_kwargs = {}

    if engine_key == "fal-wan-i2v-lora":
        video_loras = storyboard.get("video_loras", [])

        if not video_loras:
            config_loras = config.get("loras", {})
            wan_loras = {k: v for k, v in config_loras.items() if v.get("type") == "wan"}

            if wan_loras:
                lora_choices = [f"{k} (trigger: {v.get('trigger', '?')})" for k, v in wan_loras.items()]
                lora_pick = questionary.select(
                    "Select WAN LoRA for video generation:",
                    choices=lora_choices + ["None (no LoRA)"]
                ).ask()

                if lora_pick and lora_pick != "None (no LoRA)":
                    picked_name = lora_pick.split(" (trigger:")[0]
                    fal_url = wan_loras[picked_name].get("fal_url")
                    if fal_url:
                        scale = float(questionary.text("LoRA scale (0.0-4.0):", default="1.0").ask())
                        video_loras = [{"path": fal_url, "scale": scale}]
                        console.print(f"  [green]WAN LoRA: {picked_name} (scale={scale})[/green]")
                    else:
                        console.print("[red]No fal.ai URL found for this LoRA.[/red]")
                        input("\nPress Enter to continue...")
                        return
            else:
                console.print("[yellow]No WAN LoRAs found in config.[/yellow]")
                if not questionary.confirm("Continue without video LoRA?").ask():
                    return

        if video_loras:
            engine_kwargs["loras"] = video_loras

    # --- Setup Output Directories ---
    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    output_base = os.path.join(videos_dir, name)
    keyframes_dir = os.path.join(output_base, "keyframes")
    clips_dir = os.path.join(output_base, "clips", engine_key)
    os.makedirs(keyframes_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    # ===================================================================
    # SCENE MODE: fresh Kontext keyframe per shot, crossfade stitch
    # ===================================================================
    if stitch_mode == "scene":
        # Generate keyframes for all shots
        keyframe_paths = []
        for i, shot in enumerate(shots):
            kf_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.png")
            keyframe_paths.append(kf_path)

            if os.path.exists(kf_path):
                console.print(f"  [dim]Keyframe {i + 1}/{len(shots)} already exists, skipping.[/dim]")
                continue

            scene_prompt = shot.get("image_prompt", "")
            if not scene_prompt:
                console.print(f"  [red]Shot {i + 1} has no scene prompt — required for scene mode.[/red]")
                input("\nPress Enter to continue...")
                return

            console.print(f"\n[bold]Keyframe {i + 1}/{len(shots)}:[/bold]")

            if reference_image and os.path.exists(reference_image):
                ok = _generate_keyframe_kontext(scene_prompt, reference_image, kf_path)
                if not ok:
                    input("\nPress Enter to continue...")
                    return
            else:
                lora_paths = [l["path"] for l in loras] if loras else None
                generator = get_generator(generator_name, lora_paths=lora_paths)
                seed = random.randint(0, 2**32 - 1)
                img = generator.generate(prompt=scene_prompt, steps=steps, seed=seed)
                img.save(kf_path)

            console.print(f"  [green]Saved: {kf_path}[/green]")

        # Review keyframes
        console.print(Panel(
            f"[bold]Review keyframes before video generation.[/bold]\n\n"
            f"Keyframes: {keyframes_dir}/\n"
            f"Open this folder and inspect each image.",
            title="Keyframe Review",
            border_style="yellow"
        ))

        while True:
            review = questionary.select(
                "Keyframe Review:",
                choices=[
                    "Accept all keyframes - proceed to video",
                    "Re-generate a keyframe",
                    "Abort storyboard"
                ]
            ).ask()

            if not review or review == "Abort storyboard":
                console.print("[yellow]Aborted.[/yellow]")
                input("\nPress Enter to continue...")
                return

            if review == "Accept all keyframes - proceed to video":
                break

            if review == "Re-generate a keyframe":
                regen_choices = [f"Shot {i + 1}" for i in range(len(shots))]
                pick = questionary.select("Which keyframe?", choices=regen_choices + ["Cancel"]).ask()
                if pick and pick != "Cancel":
                    idx = int(pick.split(" ")[1]) - 1
                    kf = keyframe_paths[idx]
                    if os.path.exists(kf):
                        os.remove(kf)
                    scene_prompt = shots[idx].get("image_prompt", "")
                    console.print(f"Re-generating keyframe {idx + 1}...")
                    if reference_image and os.path.exists(reference_image):
                        _generate_keyframe_kontext(scene_prompt, reference_image, kf)
                    else:
                        lora_paths = [l["path"] for l in loras] if loras else None
                        generator = get_generator(generator_name, lora_paths=lora_paths)
                        seed = random.randint(0, 2**32 - 1)
                        img = generator.generate(prompt=scene_prompt, steps=steps, seed=seed)
                        img.save(kf)
                    console.print(f"  [green]Keyframe {idx + 1} re-generated.[/green]")

        # Generate clips — each from its own keyframe
        console.print(f"\n[bold]Generating {num_clips} clips (scene mode)...[/bold]")
        video_manager = get_video_manager(engine_name=engine_key, engine_kwargs=engine_kwargs)
        clip_paths = []

        for i, shot in enumerate(shots):
            if not shot.get("motion"):
                continue

            clip_path = os.path.join(clips_dir, f"clip_{i:03d}.mp4")
            clip_paths.append(clip_path)

            if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                console.print(f"  [dim]Clip {len(clip_paths)}/{num_clips} already exists, skipping.[/dim]")
                continue

            console.print(f"\n[bold cyan]Clip {len(clip_paths)}/{num_clips}:[/bold cyan] {shot['motion'][:80]}")
            console.print(f"  [dim]Start image: keyframe_{i:03d}.png[/dim]")

            success = video_manager.generate_clip(
                prompt=shot["motion"],
                start_image_path=keyframe_paths[i],
                output_path=clip_path,
                resolution=resolution,
                num_frames=num_frames,
                fps=fps,
            )

            if not success:
                console.print(f"  [red]Clip {len(clip_paths)} failed. Aborting.[/red]")
                input("\nPress Enter to continue...")
                return

            console.print(f"  [green]Clip {len(clip_paths)} saved.[/green]")

        # Stitch with crossfade
        console.print(f"\n[bold green]All {num_clips} clips generated![/bold green]")
        _stitch_clips(clip_paths, output_base, name, engine_key, fps, crossfade=0.5)

    # ===================================================================
    # CHAIN MODE: continuous chained clips, last frame feeds next
    # ===================================================================
    elif stitch_mode == "chain":
        # Generate initial keyframe only
        keyframe_path = os.path.join(keyframes_dir, "keyframe_000.png")
        first_shot = shots[0]

        if os.path.exists(keyframe_path):
            console.print(f"  [dim]Initial keyframe already exists, skipping.[/dim]")
        else:
            scene_prompt = first_shot.get("image_prompt", "")
            console.print(f"\n[bold]Generating initial keyframe...[/bold]")

            if reference_image and os.path.exists(reference_image) and scene_prompt:
                ok = _generate_keyframe_kontext(scene_prompt, reference_image, keyframe_path)
                if not ok:
                    input("\nPress Enter to continue...")
                    return
            elif scene_prompt:
                lora_paths = [l["path"] for l in loras] if loras else None
                generator = get_generator(generator_name, lora_paths=lora_paths)
                seed = random.randint(0, 2**32 - 1)
                img = generator.generate(prompt=scene_prompt, steps=steps, seed=seed)
                img.save(keyframe_path)
            else:
                console.print("[red]Shot 1 needs an image_prompt for chain mode.[/red]")
                input("\nPress Enter to continue...")
                return

            console.print(f"  [green]Saved: {keyframe_path}[/green]")

        # Review
        console.print(Panel(
            f"[bold]Review the initial keyframe.[/bold]\n\n"
            f"Keyframe: {keyframe_path}",
            title="Keyframe Review",
            border_style="yellow"
        ))

        while True:
            review = questionary.select(
                "Keyframe Review:",
                choices=["Accept - proceed to video", "Re-generate", "Abort"]
            ).ask()

            if not review or review == "Abort":
                console.print("[yellow]Aborted.[/yellow]")
                input("\nPress Enter to continue...")
                return
            if review == "Accept - proceed to video":
                break
            if review == "Re-generate":
                if os.path.exists(keyframe_path):
                    os.remove(keyframe_path)
                scene_prompt = first_shot.get("image_prompt", "")
                console.print("Re-generating keyframe...")
                if reference_image and os.path.exists(reference_image):
                    _generate_keyframe_kontext(scene_prompt, reference_image, keyframe_path)
                else:
                    lora_paths = [l["path"] for l in loras] if loras else None
                    generator = get_generator(generator_name, lora_paths=lora_paths)
                    seed = random.randint(0, 2**32 - 1)
                    img = generator.generate(prompt=scene_prompt, steps=steps, seed=seed)
                    img.save(keyframe_path)
                console.print(f"  [green]Keyframe re-generated.[/green]")

        # Generate clips — chained
        console.print(f"\n[bold]Generating {num_clips} clips (chain mode)...[/bold]")
        video_manager = get_video_manager(engine_name=engine_key, engine_kwargs=engine_kwargs)
        clip_paths = []
        current_start_image = keyframe_path

        for i, shot in enumerate(shots):
            if not shot.get("motion"):
                continue

            clip_path = os.path.join(clips_dir, f"clip_{i:03d}.mp4")
            clip_paths.append(clip_path)

            if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                console.print(f"  [dim]Clip {len(clip_paths)}/{num_clips} already exists, skipping.[/dim]")
                last_frame_path = os.path.join(keyframes_dir, f"chain_frame_{i:03d}.png")
                if not os.path.exists(last_frame_path):
                    _extract_last_frame(clip_path, last_frame_path)
                current_start_image = last_frame_path
                continue

            console.print(f"\n[bold cyan]Clip {len(clip_paths)}/{num_clips}:[/bold cyan] {shot['motion'][:80]}")
            console.print(f"  [dim]Start image: {os.path.basename(current_start_image)}[/dim]")

            success = video_manager.generate_clip(
                prompt=shot["motion"],
                start_image_path=current_start_image,
                output_path=clip_path,
                resolution=resolution,
                num_frames=num_frames,
                fps=fps,
            )

            if not success:
                console.print(f"  [red]Clip {len(clip_paths)} failed. Aborting.[/red]")
                input("\nPress Enter to continue...")
                return

            console.print(f"  [green]Clip {len(clip_paths)} saved.[/green]")

            last_frame_path = os.path.join(keyframes_dir, f"chain_frame_{i:03d}.png")
            _extract_last_frame(clip_path, last_frame_path)
            current_start_image = last_frame_path
            console.print(f"  [dim]Extracted last frame → {os.path.basename(last_frame_path)}[/dim]")

        console.print(f"\n[bold green]All {num_clips} clips generated![/bold green]")
        _stitch_clips(clip_paths, output_base, name, engine_key, fps, crossfade=0)

    input("\nPress Enter to continue...")


def _stitch_clips(clip_paths, output_base, name, engine_key, fps, crossfade=0):
    """Stitch clips into final video. crossfade=0 for hard cut, >0 for crossfade seconds."""
    console.print("\n[bold]Stitching clips into final video...[/bold]")

    final_video_path = os.path.join(output_base, f"{name}_{engine_key}.mp4")

    if crossfade > 0 and len(clip_paths) > 1:
        # Build ffmpeg crossfade filter chain
        inputs = []
        for cp in clip_paths:
            inputs.extend(["-i", cp])

        # Build xfade filter chain
        filter_parts = []
        current = "[0:v]"
        for i in range(1, len(clip_paths)):
            next_label = f"[{i}:v]"
            out_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
            # offset = duration of accumulated clips minus crossfade overlap
            # Each clip's duration approximated from file
            filter_parts.append(
                f"{current}{next_label}xfade=transition=fade:duration={crossfade}:offset={{offset_{i}}}{out_label}"
            )
            current = out_label

        # Get clip durations to calculate offsets
        offsets = []
        accumulated = 0
        for i, cp in enumerate(clip_paths[:-1]):
            dur_result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", cp],
                capture_output=True, text=True
            )
            dur = float(dur_result.stdout.strip())
            accumulated += dur if i == 0 else dur - crossfade
            offsets.append(accumulated - crossfade)

        # Rebuild filter with actual offsets
        filter_parts = []
        current = "[0:v]"
        for i in range(1, len(clip_paths)):
            next_label = f"[{i}:v]"
            out_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
            filter_parts.append(
                f"{current}{next_label}xfade=transition=fade:duration={crossfade}:offset={offsets[i-1]:.3f}{out_label}"
            )
            current = out_label

        filter_str = ";".join(filter_parts)

        try:
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[vout]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                final_video_path
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print(f"\n[bold green]Final video saved: {final_video_path}[/bold green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]ffmpeg crossfade failed (exit {e.returncode}), falling back to hard cut...[/red]")
            _stitch_clips(clip_paths, output_base, name, engine_key, fps, crossfade=0)
        except FileNotFoundError:
            console.print("[red]ffmpeg not found. Install: brew install ffmpeg[/red]")
    else:
        # Hard cut concat
        concat_list_path = os.path.join(output_base, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for cp in clip_paths:
                f.write(f"file '{os.path.abspath(cp)}'\n")

        try:
            subprocess.check_call([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                final_video_path
            ])
            console.print(f"\n[bold green]Final video saved: {final_video_path}[/bold green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]ffmpeg stitching failed (exit {e.returncode})[/red]")
        except FileNotFoundError:
            console.print("[red]ffmpeg not found. Install: brew install ffmpeg[/red]")

        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)

    console.print(f"[yellow]Individual clips: {os.path.dirname(clip_paths[0])}/[/yellow]")
