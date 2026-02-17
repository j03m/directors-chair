import os
import json
import subprocess
import questionary
from rich.panel import Panel
from rich.table import Table
from directors_chair.config.loader import load_config
from directors_chair.storyboard import load_storyboard, validate_storyboard
from directors_chair.cli.utils import console


def storyboard_to_video(storyboard_file=None, auto_mode=False):
    """Main storyboard pipeline: Layout → Keyframe → Video.

    Args:
        storyboard_file: Path to storyboard JSON (skips file selection if provided).
        auto_mode: If True, skip all interactive prompts and review loops.
    """
    config = load_config()

    # --- Select Storyboard File ---
    if storyboard_file:
        storyboard_path = storyboard_file
        if not os.path.exists(storyboard_path):
            console.print(f"[red]Storyboard file not found: {storyboard_path}[/red]")
            return
    else:
        storyboard_dir = config.get("directories", {}).get("storyboards", "storyboards")
        if not os.path.exists(storyboard_dir):
            console.print(f"[red]Storyboard directory not found: {storyboard_dir}/[/red]")
            console.print("[yellow]Create a 'storyboards/' directory and add JSON files.[/yellow]")
            if not auto_mode:
                input("\nPress Enter to continue...")
            return

        json_files = []
        for root, dirs, files in os.walk(storyboard_dir):
            for f in files:
                if f.endswith(".json"):
                    rel = os.path.relpath(os.path.join(root, f), storyboard_dir)
                    json_files.append(rel)
        if not json_files:
            console.print("[yellow]No storyboard JSON files found in storyboards/[/yellow]")
            if not auto_mode:
                input("\nPress Enter to continue...")
            return

        file_choice = questionary.select(
            "Select Storyboard:",
            choices=sorted(json_files) + ["Back"]
        ).ask()

        if not file_choice or file_choice == "Back":
            return

        storyboard_path = os.path.join(storyboard_dir, file_choice)
    storyboard_base_dir = os.path.dirname(os.path.abspath(storyboard_path))
    storyboard = load_storyboard(storyboard_path)

    # --- Validate ---
    is_valid, errors = validate_storyboard(storyboard)
    if not is_valid:
        console.print("[red]Storyboard validation failed:[/red]")
        for err in errors:
            console.print(f"  [red]- {err}[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    # --- Display Summary ---
    name = storyboard["name"]
    shots = storyboard["shots"]
    characters = storyboard["characters"]
    kling_params = storyboard.get("kling_params", {})
    keyframe_engine = storyboard.get("keyframe_engine", "gemini")

    table = Table(title=f"Storyboard: {name}")
    table.add_column("Shot", style="cyan", width=6)
    table.add_column("Name", style="white", width=20)
    table.add_column("Beats", style="magenta", width=8)
    table.add_column("Duration", style="yellow", width=10)
    table.add_column("Layout", style="green")

    for i, shot in enumerate(shots):
        shot_name = shot.get("name", f"shot_{i+1}")
        beats = shot.get("beats", [])
        total_dur = sum(int(b.get("duration", "5")) for b in beats)
        layout = shot.get("layout_prompt", "")
        table.add_row(
            str(i + 1),
            shot_name,
            str(len(beats)),
            f"{total_dur}s",
            layout[:50] + "..." if len(layout) > 50 else layout,
        )

    console.print(table)
    console.print(f"\n[bold]Characters:[/bold]")
    for cname, cdef in characters.items():
        body = cdef.get("body_type", "regular_male")
        console.print(f"  {cname}: {cdef['reference_image']} ({body})")
    console.print(f"[bold]Keyframe engine:[/bold] {keyframe_engine}")
    console.print(f"[bold]Kling params:[/bold] {kling_params}")

    # Cost estimate
    num_shots = len(shots)
    total_beats = sum(len(s.get("beats", [])) for s in shots)
    total_duration = sum(
        sum(int(b.get("duration", "5")) for b in s.get("beats", []))
        for s in shots
    )
    layout_cost = num_shots * 0.02
    keyframe_cost = num_shots * 0.10
    video_cost = num_shots * 0.60
    total_cost = layout_cost + keyframe_cost + video_cost
    console.print(f"[bold]Estimated cost:[/bold] ~${total_cost:.2f} ({num_shots} shots, {total_beats} beats, {total_duration}s total)")

    if not auto_mode:
        if not questionary.confirm("Proceed?").ask():
            return

    # --- Setup Output Directories ---
    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    output_base = os.path.join(videos_dir, name)
    layouts_dir = os.path.join(output_base, "layouts")
    keyframes_dir = os.path.join(output_base, "keyframes")
    clips_dir = os.path.join(output_base, "clips")
    os.makedirs(layouts_dir, exist_ok=True)
    os.makedirs(keyframes_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    # --- Phase 1: Layout Generation ---
    console.print(Panel("[bold]Phase 1: Layout Generation[/bold]", border_style="cyan"))

    from directors_chair.layout import generate_layout

    layout_paths = []
    for i, shot in enumerate(shots):
        layout_path = os.path.join(layouts_dir, f"layout_{i:03d}.png")
        layout_paths.append(layout_path)

        if os.path.exists(layout_path):
            console.print(f"  [dim]Layout {i + 1}/{num_shots} already exists, skipping.[/dim]")
            continue

        console.print(f"\n[bold]Layout {i + 1}/{num_shots}: {shot.get('name', '')}[/bold]")
        ok = generate_layout(shot["layout_prompt"], characters, layout_path)
        if not ok:
            console.print(f"[red]Layout generation failed for shot {i + 1}.[/red]")
            if not auto_mode:
                input("\nPress Enter to continue...")
            return

    # Layout review
    if not auto_mode:
        console.print(Panel(
            f"[bold]Review layouts before keyframe generation.[/bold]\n\n"
            f"Layouts: {layouts_dir}/\n"
            f"Open this folder and inspect each image.",
            title="Layout Review",
            border_style="yellow"
        ))

        while True:
            review = questionary.select(
                "Layout Review:",
                choices=[
                    "Accept all layouts - proceed to keyframes",
                    "Re-generate a layout",
                    "Abort storyboard"
                ]
            ).ask()

            if not review or review == "Abort storyboard":
                console.print("[yellow]Aborted.[/yellow]")
                input("\nPress Enter to continue...")
                return

            if review == "Accept all layouts - proceed to keyframes":
                break

            if review == "Re-generate a layout":
                regen_choices = [f"Shot {i + 1}: {shots[i].get('name', '')}" for i in range(num_shots)]
                pick = questionary.select("Which layout?", choices=regen_choices + ["Cancel"]).ask()
                if pick and pick != "Cancel":
                    idx = int(pick.split(":")[0].split(" ")[1]) - 1
                    layout_path = layout_paths[idx]

                    # Show current prompt and offer to edit
                    current_prompt = shots[idx].get("layout_prompt", "")
                    if current_prompt:
                        console.print(f"\n[dim]Current prompt:[/dim]")
                        console.print(f"  {current_prompt}")
                        edited = questionary.text(
                            "Edit prompt (Enter to keep, or type new):",
                            default=current_prompt,
                        ).ask()
                        if edited and edited != current_prompt:
                            shots[idx]["layout_prompt"] = edited
                            # Save back to file
                            prompt_file = shots[idx].get("layout_prompt_file")
                            if prompt_file:
                                save_path = os.path.join(storyboard_base_dir, prompt_file)
                                with open(save_path, "w") as f:
                                    f.write(edited)
                                console.print(f"  [yellow]Prompt saved to {prompt_file}[/yellow]")

                    if os.path.exists(layout_path):
                        os.remove(layout_path)
                    # Also remove the generated script
                    script_path = layout_path.replace(".png", "_layout.py")
                    if os.path.exists(script_path):
                        os.remove(script_path)

                    console.print(f"Re-generating layout {idx + 1}...")
                    ok = generate_layout(shots[idx]["layout_prompt"], characters, layout_path)
                    if ok:
                        console.print(f"  [green]Layout {idx + 1} re-generated.[/green]")
    else:
        console.print("[dim]Auto mode: accepting all layouts.[/dim]")

    # --- Phase 2: Keyframe Generation ---
    engine_label = "Kling O3 i2i" if keyframe_engine == "kling" else "Nano Banana Pro (Gemini)"
    console.print(Panel(f"[bold]Phase 2: Keyframe Generation ({engine_label})[/bold]", border_style="cyan"))

    from directors_chair.keyframe import generate_keyframe_kling, generate_keyframe_nano_banana

    keyframe_paths = []
    for i, shot in enumerate(shots):
        kf_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.png")
        keyframe_paths.append(kf_path)

        if os.path.exists(kf_path):
            console.print(f"  [dim]Keyframe {i + 1}/{num_shots} already exists, skipping.[/dim]")
            continue

        console.print(f"\n[bold]Keyframe {i + 1}/{num_shots}: {shot.get('name', '')}[/bold]")
        # Per-shot character scoping: if shot has "characters" list, only use those
        shot_characters = characters
        if "characters" in shot and isinstance(shot["characters"], list):
            shot_characters = {k: v for k, v in characters.items() if k in shot["characters"]}
            console.print(f"  [dim]Shot characters: {list(shot_characters.keys())}[/dim]")

        if keyframe_engine == "gemini":
            ok = generate_keyframe_nano_banana(
                prompt=shot.get("keyframe_prompt", ""),
                comp_image_path=layout_paths[i],
                characters=shot_characters,
                output_path=kf_path,
                kling_params=kling_params,
            )
        else:
            ok = generate_keyframe_kling(
                prompt=shot.get("keyframe_prompt"),
                comp_image_path=layout_paths[i],
                characters=shot_characters,
                output_path=kf_path,
                kling_params=kling_params,
                keyframe_passes=shot.get("keyframe_passes"),
            )
        if not ok:
            console.print(f"[red]Keyframe generation failed for shot {i + 1}.[/red]")
            if not auto_mode:
                input("\nPress Enter to continue...")
            return

    # Keyframe review
    if not auto_mode:
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
                regen_choices = [f"Shot {i + 1}: {shots[i].get('name', '')}" for i in range(num_shots)]
                pick = questionary.select("Which keyframe?", choices=regen_choices + ["Cancel"]).ask()
                if pick and pick != "Cancel":
                    idx = int(pick.split(":")[0].split(" ")[1]) - 1
                    kf = keyframe_paths[idx]

                    # Show current prompt and offer to edit
                    current_prompt = shots[idx].get("keyframe_prompt", "")
                    if current_prompt:
                        console.print(f"\n[dim]Current prompt:[/dim]")
                        console.print(f"  {current_prompt}")
                        edited = questionary.text(
                            "Edit prompt (Enter to keep, or type new):",
                            default=current_prompt,
                        ).ask()
                        if edited and edited != current_prompt:
                            shots[idx]["keyframe_prompt"] = edited
                            # Save back to file
                            prompt_file = shots[idx].get("keyframe_prompt_file")
                            if prompt_file:
                                save_path = os.path.join(storyboard_base_dir, prompt_file)
                                with open(save_path, "w") as f:
                                    f.write(edited)
                                console.print(f"  [yellow]Prompt saved to {prompt_file}[/yellow]")

                    # How many variants?
                    num_variants = 1
                    if keyframe_engine == "gemini":
                        variant_pick = questionary.select(
                            "How many variants?",
                            choices=["1 (default)", "2", "3", "4"]
                        ).ask()
                        if variant_pick:
                            num_variants = int(variant_pick[0])

                    if os.path.exists(kf):
                        os.remove(kf)

                    console.print(f"Re-generating keyframe {idx + 1} ({num_variants} variant(s))...")
                    if keyframe_engine == "gemini":
                        ok = generate_keyframe_nano_banana(
                            prompt=shots[idx].get("keyframe_prompt", ""),
                            comp_image_path=layout_paths[idx],
                            characters=characters,
                            output_path=kf,
                            kling_params=kling_params,
                            num_images=num_variants,
                        )
                    else:
                        ok = generate_keyframe_kling(
                            prompt=shots[idx].get("keyframe_prompt"),
                            comp_image_path=layout_paths[idx],
                            characters=characters,
                            output_path=kf,
                            kling_params=kling_params,
                            keyframe_passes=shots[idx].get("keyframe_passes"),
                        )
                    if ok:
                        console.print(f"  [green]Keyframe {idx + 1} re-generated.[/green]")
    else:
        console.print("[dim]Auto mode: accepting all keyframes.[/dim]")

    # --- Phase 3: Video Generation ---
    console.print(Panel("[bold]Phase 3: Video Generation (Kling O3 i2v)[/bold]", border_style="cyan"))

    from directors_chair.video.engines.fal_kling_engine import FalKlingEngine

    engine = FalKlingEngine(kling_params=kling_params)
    clip_paths = []

    for i, shot in enumerate(shots):
        clip_path = os.path.join(clips_dir, f"clip_{i:03d}.mp4")
        clip_paths.append(clip_path)

        if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
            console.print(f"  [dim]Clip {i + 1}/{num_shots} already exists, skipping.[/dim]")
            continue

        console.print(f"\n[bold]Clip {i + 1}/{num_shots}: {shot.get('name', '')}[/bold]")
        ok = engine.generate_video(
            start_image_path=keyframe_paths[i],
            beats=shot["beats"],
            characters=characters,
            output_path=clip_path,
            kling_params=kling_params,
        )
        if not ok:
            console.print(f"[red]Video generation failed for shot {i + 1}.[/red]")
            if not auto_mode:
                input("\nPress Enter to continue...")
            return

    # --- Phase 4: Stitch (if multiple shots) ---
    if len(clip_paths) == 1:
        final_path = os.path.join(output_base, f"{name}.mp4")
        # Just copy the single clip
        if not os.path.exists(final_path):
            subprocess.check_call([
                "ffmpeg", "-y", "-i", clip_paths[0], "-c", "copy", final_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"\n[bold green]Final video: {final_path}[/bold green]")
    elif len(clip_paths) > 1:
        console.print(Panel("[bold]Phase 4: Stitching Clips[/bold]", border_style="cyan"))
        final_path = os.path.join(output_base, f"{name}.mp4")
        _stitch_clips(clip_paths, final_path)

    console.print(f"\n[bold green]Done! All outputs in: {output_base}/[/bold green]")
    console.print(f"[yellow]  Layouts: {layouts_dir}/[/yellow]")
    console.print(f"[yellow]  Keyframes: {keyframes_dir}/[/yellow]")
    console.print(f"[yellow]  Clips: {clips_dir}/[/yellow]")
    if not auto_mode:
        input("\nPress Enter to continue...")


def _stitch_clips(clip_paths, final_path):
    """Stitch multiple clips into final video, re-encoding to common resolution."""
    # Build ffmpeg filter to scale all inputs to 1280x720 and concatenate
    inputs = []
    filter_parts = []
    for i, cp in enumerate(clip_paths):
        inputs.extend(["-i", os.path.abspath(cp)])
        filter_parts.append(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")

    stream_labels = "".join(f"[v{i}]" for i in range(len(clip_paths)))
    filter_parts.append(f"{stream_labels}concat=n={len(clip_paths)}:v=1:a=0[out]")
    filter_graph = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        final_path
    ]

    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    console.print(f"\n[bold green]Final video: {final_path}[/bold green]")
