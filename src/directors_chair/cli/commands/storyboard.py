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
    "scene": "Scene — fresh keyframe per shot via Kontext, crossfade transitions",
    "chain": "Chain — continuous long take, last frame feeds next clip",
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


def _generate_keyframe_multipass(characters: dict, passes: list, keyframes_dir: str, shot_index: int) -> bool:
    """Generate a keyframe via multi-pass Kontext editing.

    Pass 0: Uses the character's reference_image as Kontext input.
    Pass N>0: Uses the output of pass N-1 as Kontext input.
    """
    num_passes = len(passes)
    current_image_path = None

    for pass_idx, kp in enumerate(passes):
        char_name = kp["character"]
        prompt = kp["prompt"]
        is_final = (pass_idx == num_passes - 1)

        if pass_idx == 0:
            input_image = characters[char_name]["reference_image"]
        else:
            input_image = current_image_path

        if is_final:
            output_path = os.path.join(keyframes_dir, f"keyframe_{shot_index:03d}.png")
        else:
            output_path = os.path.join(keyframes_dir, f"keyframe_{shot_index:03d}_pass{pass_idx}.png")

        console.print(f"    [dim]Pass {pass_idx + 1}/{num_passes} ({char_name}): {prompt[:60]}...[/dim]")

        ok = _generate_keyframe_kontext(prompt, input_image, output_path)
        if not ok:
            return False

        current_image_path = output_path

    return True


def _create_composite_reference(characters: dict, output_path: str) -> str:
    """Stitch character reference images side-by-side into a composite.

    First character gets ~60% width (primary subject should be larger
    per Kontext best practices).
    """
    char_list = list(characters.items())
    images = []
    for cname, cdef in char_list:
        img = Image.open(cdef["reference_image"])
        images.append((cname, img))

    # Normalize to same height
    target_height = max(img.height for _, img in images)
    resized = []
    for cname, img in images:
        if img.height != target_height:
            ratio = target_height / img.height
            img = img.resize((int(img.width * ratio), target_height), Image.LANCZOS)
        resized.append((cname, img))

    # First character gets 60% width for 2 chars, equal for 3+
    if len(resized) == 2:
        primary_name, primary_img = resized[0]
        secondary_name, secondary_img = resized[1]
        # Scale primary to 60%, secondary to 40% of total
        total_w = primary_img.width + secondary_img.width
        target_primary_w = int(total_w * 0.6)
        target_secondary_w = total_w - target_primary_w
        primary_img = primary_img.resize((target_primary_w, target_height), Image.LANCZOS)
        secondary_img = secondary_img.resize((target_secondary_w, target_height), Image.LANCZOS)
        resized = [(primary_name, primary_img), (secondary_name, secondary_img)]

    total_width = sum(img.width for _, img in resized)
    composite = Image.new("RGB", (total_width, target_height))
    x_offset = 0
    for cname, img in resized:
        composite.paste(img, (x_offset, 0))
        console.print(f"  [dim]Composite: {cname} at x={x_offset}, {img.width}x{img.height}[/dim]")
        x_offset += img.width

    composite.save(output_path)
    console.print(f"  [green]Composite reference saved: {output_path}[/green]")
    return output_path


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
    characters = storyboard.get("characters", {})
    is_multichar = len(characters) > 0

    steps = image_params.get("steps", 25)
    resolution = video_params.get("resolution", "480p")
    num_frames = video_params.get("num_frames", 81)
    fps = video_params.get("fps", 16)

    table = Table(title=f"Storyboard: {name}")
    table.add_column("Shot", style="cyan", width=6)
    if is_multichar:
        table.add_column("Passes", style="magenta")
    else:
        table.add_column("Scene", style="white")
    table.add_column("Motion", style="green")
    table.add_column("Frames", style="yellow", width=8)

    for i, shot in enumerate(shots):
        motion = shot.get("motion", "")
        shot_vp = shot.get("video_params", {})
        shot_frames = shot_vp.get("num_frames", num_frames)
        frames_str = str(shot_frames) if shot_vp.get("num_frames") else f"{num_frames}"

        if is_multichar:
            passes = shot.get("keyframe_passes", [])
            pass_summary = " → ".join(kp["character"] for kp in passes)
            table.add_row(
                str(i + 1),
                pass_summary,
                motion[:60] + "..." if len(motion) > 60 else motion,
                frames_str,
            )
        else:
            scene = shot.get("image_prompt", "")
            table.add_row(
                str(i + 1),
                scene[:80] + "..." if len(scene) > 80 else scene,
                motion[:80] + "..." if len(motion) > 80 else motion,
                frames_str,
            )

    console.print(table)
    if is_multichar:
        console.print(f"\n[bold]Characters:[/bold]")
        for cname, cdef in characters.items():
            console.print(f"  {cname}: {cdef['reference_image']}")
    else:
        console.print(f"\n[bold]Reference image:[/bold] {reference_image or 'None'}")
    console.print(f"[bold]Video defaults:[/bold] {resolution}, {num_frames} frames, {fps} fps")

    num_clips = sum(1 for s in shots if s.get("motion"))
    clip_cost = num_clips * (0.20 if resolution == "480p" else 0.40)
    # Kontext keyframe costs: ~$0.04 per call
    if is_multichar:
        num_kontext = sum(len(s.get("keyframe_passes", [])) for s in shots)
    else:
        num_kontext = len(shots) if reference_image else 0
    keyframe_cost = num_kontext * 0.04
    total_cost = clip_cost + keyframe_cost
    console.print(f"[bold]Clips:[/bold] {num_clips}")
    console.print(f"[bold]Kontext keyframe calls:[/bold] {num_kontext}")
    console.print(f"[bold]Estimated cost:[/bold] ~${total_cost:.2f} (clips ${clip_cost:.2f} + keyframes ${keyframe_cost:.2f})")

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
        # Create composite reference for multi-character storyboards
        composite_ref = None
        if is_multichar:
            composite_ref = os.path.join(keyframes_dir, "composite_reference.png")
            if not os.path.exists(composite_ref):
                console.print("\n[bold]Creating composite reference image...[/bold]")
                _create_composite_reference(characters, composite_ref)
            else:
                console.print(f"  [dim]Composite reference already exists.[/dim]")

        # Generate keyframes for all shots
        keyframe_paths = []
        for i, shot in enumerate(shots):
            kf_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.png")
            keyframe_paths.append(kf_path)

            if os.path.exists(kf_path):
                console.print(f"  [dim]Keyframe {i + 1}/{len(shots)} already exists, skipping.[/dim]")
                continue

            console.print(f"\n[bold]Keyframe {i + 1}/{len(shots)}:[/bold]")

            if is_multichar:
                # Composite approach: single Kontext call with stitched reference
                if shot.get("image_prompt"):
                    ok = _generate_keyframe_kontext(shot["image_prompt"], composite_ref, kf_path)
                    if not ok:
                        input("\nPress Enter to continue...")
                        return
                # Multi-pass fallback: keyframe_passes with per-character prompts
                elif shot.get("keyframe_passes"):
                    passes = shot["keyframe_passes"]
                    ok = _generate_keyframe_multipass(characters, passes, keyframes_dir, i)
                    if not ok:
                        input("\nPress Enter to continue...")
                        return
                else:
                    console.print(f"  [red]Shot {i + 1} needs image_prompt or keyframe_passes.[/red]")
                    input("\nPress Enter to continue...")
                    return
            else:
                scene_prompt = shot.get("image_prompt", "")
                if not scene_prompt:
                    console.print(f"  [red]Shot {i + 1} has no scene prompt — required for scene mode.[/red]")
                    input("\nPress Enter to continue...")
                    return
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

                    # Show current prompt and offer to edit
                    current_prompt = shots[idx].get("image_prompt", "")
                    if current_prompt:
                        console.print(f"\n[dim]Current prompt:[/dim]")
                        console.print(f"  {current_prompt[:120]}...")
                        edited = questionary.text(
                            "Edit prompt (Enter to keep, or type new):",
                            default=current_prompt,
                        ).ask()
                        if edited and edited != current_prompt:
                            shots[idx]["image_prompt"] = edited
                            console.print(f"  [yellow]Prompt updated for this run.[/yellow]")

                    if os.path.exists(kf):
                        os.remove(kf)
                    # Clean intermediate pass files
                    for p in range(10):
                        intermediate = os.path.join(keyframes_dir, f"keyframe_{idx:03d}_pass{p}.png")
                        if os.path.exists(intermediate):
                            os.remove(intermediate)
                        else:
                            break

                    regen_prompt = shots[idx].get("image_prompt", "")
                    console.print(f"Re-generating keyframe {idx + 1}...")
                    console.print(f"  [dim]Reference: {composite_ref if is_multichar else reference_image}[/dim]")
                    console.print(f"  [dim]Prompt: {regen_prompt[:100]}...[/dim]")
                    if is_multichar and regen_prompt:
                        _generate_keyframe_kontext(regen_prompt, composite_ref, kf)
                    elif is_multichar and shots[idx].get("keyframe_passes"):
                        passes = shots[idx]["keyframe_passes"]
                        _generate_keyframe_multipass(characters, passes, keyframes_dir, idx)
                    elif reference_image and os.path.exists(reference_image):
                        scene_prompt = shots[idx].get("image_prompt", "")
                        _generate_keyframe_kontext(scene_prompt, reference_image, kf)
                    else:
                        scene_prompt = shots[idx].get("image_prompt", "")
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

            # Per-shot video_params override storyboard defaults
            shot_vp = shot.get("video_params", {})
            shot_frames = shot_vp.get("num_frames", num_frames)
            shot_res = shot_vp.get("resolution", resolution)
            shot_fps = shot_vp.get("fps", fps)

            console.print(f"\n[bold cyan]Clip {len(clip_paths)}/{num_clips}:[/bold cyan] {shot['motion'][:80]}")
            console.print(f"  [dim]Start image: keyframe_{i:03d}.png | {shot_frames} frames @ {shot_fps}fps[/dim]")

            success = video_manager.generate_clip(
                prompt=shot["motion"],
                start_image_path=keyframe_paths[i],
                output_path=clip_path,
                resolution=shot_res,
                num_frames=shot_frames,
                fps=shot_fps,
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
        # Create composite reference for multi-character storyboards
        composite_ref = None
        if is_multichar:
            composite_ref = os.path.join(keyframes_dir, "composite_reference.png")
            if not os.path.exists(composite_ref):
                console.print("\n[bold]Creating composite reference image...[/bold]")
                _create_composite_reference(characters, composite_ref)
            else:
                console.print(f"  [dim]Composite reference already exists.[/dim]")

        # Generate initial keyframe only
        keyframe_path = os.path.join(keyframes_dir, "keyframe_000.png")
        first_shot = shots[0]

        if os.path.exists(keyframe_path):
            console.print(f"  [dim]Initial keyframe already exists, skipping.[/dim]")
        else:
            console.print(f"\n[bold]Generating initial keyframe...[/bold]")

            if is_multichar and first_shot.get("image_prompt"):
                ok = _generate_keyframe_kontext(first_shot["image_prompt"], composite_ref, keyframe_path)
                if not ok:
                    input("\nPress Enter to continue...")
                    return
            elif is_multichar and first_shot.get("keyframe_passes"):
                passes = first_shot["keyframe_passes"]
                ok = _generate_keyframe_multipass(characters, passes, keyframes_dir, 0)
                if not ok:
                    input("\nPress Enter to continue...")
                    return
            else:
                scene_prompt = first_shot.get("image_prompt", "")
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
                    console.print("[red]Shot 1 needs an image_prompt or keyframe_passes.[/red]")
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
                for p in range(10):
                    intermediate = os.path.join(keyframes_dir, f"keyframe_000_pass{p}.png")
                    if os.path.exists(intermediate):
                        os.remove(intermediate)
                    else:
                        break
                console.print("Re-generating keyframe...")
                if is_multichar and first_shot.get("image_prompt"):
                    _generate_keyframe_kontext(first_shot["image_prompt"], composite_ref, keyframe_path)
                elif is_multichar and first_shot.get("keyframe_passes"):
                    passes = first_shot["keyframe_passes"]
                    _generate_keyframe_multipass(characters, passes, keyframes_dir, 0)
                elif reference_image and os.path.exists(reference_image):
                    scene_prompt = first_shot.get("image_prompt", "")
                    _generate_keyframe_kontext(scene_prompt, reference_image, keyframe_path)
                else:
                    scene_prompt = first_shot.get("image_prompt", "")
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

            # Per-shot video_params override storyboard defaults
            shot_vp = shot.get("video_params", {})
            shot_frames = shot_vp.get("num_frames", num_frames)
            shot_res = shot_vp.get("resolution", resolution)
            shot_fps = shot_vp.get("fps", fps)

            console.print(f"\n[bold cyan]Clip {len(clip_paths)}/{num_clips}:[/bold cyan] {shot['motion'][:80]}")
            console.print(f"  [dim]Start image: {os.path.basename(current_start_image)} | {shot_frames} frames @ {shot_fps}fps[/dim]")

            success = video_manager.generate_clip(
                prompt=shot["motion"],
                start_image_path=current_start_image,
                output_path=clip_path,
                resolution=shot_res,
                num_frames=shot_frames,
                fps=shot_fps,
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


def _detect_trailing_freeze(clip_path: str, threshold=0.03, min_duration=0.5) -> float:
    """Detect if a clip has a trailing freeze and return the trim point.

    Returns the timestamp where content ends (before the trailing freeze),
    or 0 if no trailing freeze detected.
    """
    result = subprocess.run(
        ["ffmpeg", "-i", clip_path, "-vf",
         f"freezedetect=n={threshold}:d={min_duration}",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    # Parse freeze events — collect all (start, end) pairs
    freezes = []
    current_start = None
    for line in result.stderr.split("\n"):
        if "freeze_start:" in line:
            current_start = float(line.split("freeze_start:")[1].strip())
        if "freeze_end:" in line and current_start is not None:
            freeze_end = float(line.split("freeze_end:")[1].strip())
            freezes.append((current_start, freeze_end))
            current_start = None

    if not freezes:
        return 0

    # Get clip duration
    dur_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", clip_path],
        capture_output=True, text=True
    )
    clip_dur = float(dur_result.stdout.strip())

    # Check if the last freeze extends to (or near) the end of the clip
    last_start, last_end = freezes[-1]
    if clip_dur - last_end < 0.2:
        return last_start
    return 0


def _stitch_clips(clip_paths, output_base, name, engine_key, fps, crossfade=0):
    """Stitch clips into final video. crossfade=0 for hard cut, >0 for crossfade seconds."""
    console.print("\n[bold]Stitching clips into final video...[/bold]")

    final_video_path = os.path.join(output_base, f"{name}_{engine_key}.mp4")

    if crossfade > 0 and len(clip_paths) > 1:
        # Probe each clip for duration, fps, and trailing freezes
        clip_info = []
        for cp in clip_paths:
            probe_result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=r_frame_rate",
                 "-show_entries", "format=duration",
                 "-of", "json", cp],
                capture_output=True, text=True
            )
            probe = json.loads(probe_result.stdout)
            dur = float(probe["format"]["duration"])
            fps_str = probe["streams"][0]["r_frame_rate"]
            fps_num, fps_den = fps_str.split("/")
            clip_fps = float(fps_num) / float(fps_den)

            # Detect trailing freeze and trim to content
            freeze_at = _detect_trailing_freeze(cp)
            if freeze_at > 0:
                content_dur = freeze_at
                needs_trim = True
            else:
                content_dur = dur
                needs_trim = False

            clip_info.append({
                "path": cp, "file_duration": dur, "content_duration": content_dur,
                "fps": clip_fps, "needs_trim": needs_trim,
            })
            trim_note = f" [TRIM {dur:.2f}s → {content_dur:.2f}s, trailing freeze]" if needs_trim else ""
            console.print(f"  [dim]{os.path.basename(cp)}: {clip_fps:.0f}fps, {dur:.2f}s{trim_note}[/dim]")

        # Use the max fps across clips for output
        output_fps = max(ci["fps"] for ci in clip_info)

        # Build inputs and per-clip filters (trim + fps normalize)
        # Always apply fps filter to all clips to ensure matching timebases for xfade
        has_mixed_fps = len(set(ci["fps"] for ci in clip_info)) > 1
        inputs = []
        prep_filters = []
        for i, ci in enumerate(clip_info):
            inputs.extend(["-i", ci["path"]])
            parts = []
            # Trim to content duration to remove trailing still frames
            if ci["needs_trim"]:
                parts.append(f"trim=duration={ci['content_duration']:.4f},setpts=PTS-STARTPTS")
            # Normalize fps — always apply when mixed fps to ensure matching timebases
            if has_mixed_fps or ci["needs_trim"]:
                parts.append(f"fps={output_fps:.0f}")

            if parts:
                prep_filters.append(f"[{i}:v]{','.join(parts)}[p{i}]")
            else:
                prep_filters.append(None)

        # Calculate xfade offsets from content durations
        offsets = []
        accumulated = 0
        for i, ci in enumerate(clip_info[:-1]):
            accumulated += ci["content_duration"] if i == 0 else ci["content_duration"] - crossfade
            offsets.append(accumulated - crossfade)

        # Build xfade filter chain
        xfade_parts = []
        current = f"[p0]" if prep_filters[0] else "[0:v]"
        for i in range(1, len(clip_paths)):
            next_label = f"[p{i}]" if prep_filters[i] else f"[{i}:v]"
            out_label = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
            xfade_parts.append(
                f"{current}{next_label}xfade=transition=fade:duration={crossfade}:offset={offsets[i-1]:.3f}{out_label}"
            )
            current = out_label

        # Combine prep + xfade filters
        all_filters = [f for f in prep_filters if f is not None] + xfade_parts
        filter_str = ";".join(all_filters)

        try:
            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[vout]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
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
        # Hard cut concat — detect trailing freezes and trim if needed
        any_trim = False
        trimmed_paths = []
        for cp in clip_paths:
            freeze_at = _detect_trailing_freeze(cp)
            if freeze_at > 0:
                any_trim = True
                trimmed_path = cp.replace(".mp4", "_trimmed.mp4")
                console.print(f"  [dim]{os.path.basename(cp)}: trimming trailing freeze at {freeze_at:.2f}s[/dim]")
                subprocess.check_call([
                    "ffmpeg", "-y", "-i", cp,
                    "-t", f"{freeze_at:.4f}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    trimmed_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                trimmed_paths.append(trimmed_path)
            else:
                trimmed_paths.append(cp)

        concat_list_path = os.path.join(output_base, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for tp in trimmed_paths:
                f.write(f"file '{os.path.abspath(tp)}'\n")

        try:
            # If we trimmed anything, must re-encode; otherwise stream copy is fine
            encode_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p"] if any_trim else ["-c", "copy"]
            subprocess.check_call([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_list_path,
            ] + encode_args + [final_video_path])
            console.print(f"\n[bold green]Final video saved: {final_video_path}[/bold green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]ffmpeg stitching failed (exit {e.returncode})[/red]")
        except FileNotFoundError:
            console.print("[red]ffmpeg not found. Install: brew install ffmpeg[/red]")

        # Cleanup
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
        for tp in trimmed_paths:
            if "_trimmed.mp4" in tp and os.path.exists(tp):
                os.remove(tp)

    console.print(f"[yellow]Individual clips: {os.path.dirname(clip_paths[0])}/[/yellow]")
