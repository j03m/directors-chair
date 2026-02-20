"""Clip & Keyframe Tools — edit clips, edit keyframes, regenerate single clips."""

import os
import shutil
import questionary
from rich.table import Table
from rich.panel import Panel
from directors_chair.config.loader import load_config
from directors_chair.storyboard import load_storyboard, validate_storyboard
from directors_chair.cli.utils import console


def _select_storyboard(config, storyboard_file=None):
    """Shared storyboard selection logic. Returns (storyboard, storyboard_path) or (None, None)."""
    if storyboard_file:
        storyboard_path = storyboard_file
        if not os.path.exists(storyboard_path):
            console.print(f"[red]Storyboard file not found: {storyboard_path}[/red]")
            return None, None
    else:
        storyboard_dir = config.get("directories", {}).get("storyboards", "storyboards")
        if not os.path.exists(storyboard_dir):
            console.print(f"[red]Storyboard directory not found: {storyboard_dir}/[/red]")
            input("\nPress Enter to continue...")
            return None, None

        json_files = []
        for root, dirs, files in os.walk(storyboard_dir):
            for f in files:
                if f.endswith(".json"):
                    rel = os.path.relpath(os.path.join(root, f), storyboard_dir)
                    json_files.append(rel)
        if not json_files:
            console.print("[yellow]No storyboard JSON files found.[/yellow]")
            input("\nPress Enter to continue...")
            return None, None

        file_choice = questionary.select(
            "Select Storyboard:",
            choices=sorted(json_files) + ["Back"]
        ).ask()
        if not file_choice or file_choice == "Back":
            return None, None

        storyboard_path = os.path.join(storyboard_dir, file_choice)

    storyboard = load_storyboard(storyboard_path)
    is_valid, errors = validate_storyboard(storyboard)
    if not is_valid:
        console.print("[red]Storyboard validation failed:[/red]")
        for err in errors:
            console.print(f"  [red]- {err}[/red]")
        return None, None

    return storyboard, storyboard_path


def _list_clips(clips_dir, shots):
    """List available clips and return sorted clip files."""
    clip_files = sorted([
        f for f in os.listdir(clips_dir)
        if f.startswith("clip_") and f.endswith(".mp4")
        and "_edited" not in f and "_original" not in f
    ])
    if not clip_files:
        console.print("[yellow]No clips found. Run the storyboard pipeline first.[/yellow]")
        return []

    table = Table(title="Available Clips")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Shot Name", style="yellow")
    table.add_column("Size", style="dim", width=8)
    for clip_file in clip_files:
        idx = int(clip_file.replace("clip_", "").replace(".mp4", ""))
        shot_name = shots[idx].get("name", "?") if idx < len(shots) else "?"
        size_kb = os.path.getsize(os.path.join(clips_dir, clip_file)) // 1024
        table.add_row(str(idx), shot_name, f"{size_kb}KB")
    console.print(table)
    return clip_files


def _select_clip(clip_files, shots):
    """Let user pick a clip. Returns index or None."""
    choices = []
    for f in clip_files:
        idx = int(f.replace("clip_", "").replace(".mp4", ""))
        shot_name = shots[idx].get("name", "?") if idx < len(shots) else "?"
        choices.append(f"{idx:03d} — {shot_name}")
    choices.append("Back")

    pick = questionary.select("Select clip:", choices=choices).ask()
    if not pick or pick == "Back":
        return None
    return int(pick.split(" ")[0])


def _list_keyframes(keyframes_dir, shots):
    """List available keyframes."""
    table = Table(title="Keyframes")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Shot Name", style="yellow")
    table.add_column("Status", style="dim", width=10)
    for i, shot in enumerate(shots):
        kf_path = os.path.join(keyframes_dir, f"keyframe_{i:03d}.png")
        exists = os.path.exists(kf_path)
        size_kb = os.path.getsize(kf_path) // 1024 if exists else 0
        status = f"{size_kb}KB" if exists else "[red]missing[/red]"
        table.add_row(str(i), shot.get("name", "?"), status)
    console.print(table)


def _select_keyframe(shots):
    """Let user pick a keyframe. Returns index or None."""
    choices = []
    for i, shot in enumerate(shots):
        choices.append(f"{i:03d} — {shot.get('name', '?')}")
    choices.append("Back")

    pick = questionary.select("Select keyframe:", choices=choices).ask()
    if not pick or pick == "Back":
        return None
    return int(pick.split(" ")[0])


# ============================================================
# Edit Clip (Kling O1 v2v)
# ============================================================

def edit_clip_command(storyboard_file=None, clip_index=None, edit_prompt=None, auto_mode=False, save_as_new=False):
    """Edit an existing video clip via Kling O1 v2v edit."""
    config = load_config()
    storyboard, storyboard_path = _select_storyboard(config, storyboard_file)
    if storyboard is None:
        return

    name = storyboard["name"]
    shots = storyboard["shots"]
    characters = storyboard["characters"]

    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    clips_dir = os.path.join(videos_dir, name, "clips")
    if not os.path.exists(clips_dir):
        console.print(f"[red]No clips directory for '{name}'. Run storyboard pipeline first.[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    # Select clip
    if clip_index is None:
        clip_files = _list_clips(clips_dir, shots)
        if not clip_files:
            if not auto_mode:
                input("\nPress Enter to continue...")
            return
        clip_index = _select_clip(clip_files, shots)
        if clip_index is None:
            return

    clip_path = os.path.join(clips_dir, f"clip_{clip_index:03d}.mp4")
    if not os.path.exists(clip_path):
        console.print(f"[red]Clip not found: {clip_path}[/red]")
        return

    shot_name = shots[clip_index].get("name", "?") if clip_index < len(shots) else "?"
    console.print(f"\n[bold]Editing clip {clip_index:03d}: {shot_name}[/bold]")

    # Edit loop
    while True:
        # Get prompt
        if edit_prompt and auto_mode:
            prompt = edit_prompt
        else:
            prompt = questionary.text("Edit prompt (describe what to change):").ask()
            if not prompt:
                return

        # Character selection
        selected_characters = {}
        if not auto_mode:
            char_names = list(characters.keys())
            # Scope to shot characters if available
            if clip_index < len(shots):
                shot_chars = shots[clip_index].get("characters", [])
                if isinstance(shot_chars, list) and shot_chars:
                    char_names = [c for c in shot_chars if c in characters]

            if char_names:
                use_chars = questionary.confirm(
                    f"Include character elements? ({', '.join(char_names)})",
                    default=False
                ).ask()
                if use_chars:
                    selected_characters = {k: characters[k] for k in char_names if k in characters}
        else:
            # Auto mode: use shot-scoped characters
            if clip_index < len(shots):
                shot_chars = shots[clip_index].get("characters", [])
                if isinstance(shot_chars, list):
                    selected_characters = {k: characters[k] for k in shot_chars if k in characters}

        edited_path = os.path.join(clips_dir, f"clip_{clip_index:03d}_edited.mp4")

        from directors_chair.video.engines.fal_kling_v2v_edit import edit_clip
        ok = edit_clip(
            prompt=prompt,
            video_path=clip_path,
            output_path=edited_path,
            characters=selected_characters if selected_characters else None,
        )

        if not ok:
            console.print("[red]Edit failed.[/red]")
            if auto_mode:
                return
            retry = questionary.confirm("Try again with a different prompt?").ask()
            if retry:
                edit_prompt = None
                continue
            return

        # Accept/reject
        if auto_mode:
            if save_as_new:
                console.print(f"[green]Saved: {edited_path}[/green]")
            else:
                backup = os.path.join(clips_dir, f"clip_{clip_index:03d}_original.mp4")
                if not os.path.exists(backup):
                    shutil.copy2(clip_path, backup)
                shutil.move(edited_path, clip_path)
                console.print(f"[green]Edit applied to clip_{clip_index:03d}.mp4[/green]")
            return

        action = questionary.select("Result:", choices=[
            "Accept (overwrite original)",
            "Accept (save as new)",
            "Retry with different prompt",
            "Discard",
        ]).ask()

        if not action or action == "Discard":
            if os.path.exists(edited_path):
                os.remove(edited_path)
            return

        if action == "Accept (overwrite original)":
            backup = os.path.join(clips_dir, f"clip_{clip_index:03d}_original.mp4")
            if not os.path.exists(backup):
                shutil.copy2(clip_path, backup)
                console.print(f"  [dim]Original backed up to {os.path.basename(backup)}[/dim]")
            shutil.move(edited_path, clip_path)
            console.print(f"[green]Edit applied to clip_{clip_index:03d}.mp4[/green]")
            input("\nPress Enter to continue...")
            return

        if action == "Accept (save as new)":
            console.print(f"[green]Saved: {os.path.basename(edited_path)}[/green]")
            input("\nPress Enter to continue...")
            return

        if action == "Retry with different prompt":
            if os.path.exists(edited_path):
                os.remove(edited_path)
            edit_prompt = None
            continue


# ============================================================
# Edit Keyframe (Nano Banana Pro)
# ============================================================

def edit_keyframe_command(storyboard_file=None, keyframe_index=None, edit_prompt=None, auto_mode=False):
    """Edit an existing keyframe via Nano Banana Pro (Gemini)."""
    config = load_config()
    storyboard, storyboard_path = _select_storyboard(config, storyboard_file)
    if storyboard is None:
        return

    name = storyboard["name"]
    shots = storyboard["shots"]
    characters = storyboard["characters"]
    kling_params = storyboard.get("kling_params", {})

    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    keyframes_dir = os.path.join(videos_dir, name, "keyframes")
    if not os.path.exists(keyframes_dir):
        console.print(f"[red]No keyframes directory for '{name}'. Run storyboard pipeline first.[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    # Select keyframe
    if keyframe_index is None:
        _list_keyframes(keyframes_dir, shots)
        keyframe_index = _select_keyframe(shots)
        if keyframe_index is None:
            return

    kf_path = os.path.join(keyframes_dir, f"keyframe_{keyframe_index:03d}.png")
    if not os.path.exists(kf_path):
        console.print(f"[red]Keyframe not found: {kf_path}[/red]")
        return

    shot_name = shots[keyframe_index].get("name", "?") if keyframe_index < len(shots) else "?"
    console.print(f"\n[bold]Editing keyframe {keyframe_index:03d}: {shot_name}[/bold]")

    # Scope characters to shot
    shot_characters = characters
    if keyframe_index < len(shots):
        shot_chars = shots[keyframe_index].get("characters", [])
        if isinstance(shot_chars, list) and shot_chars:
            shot_characters = {k: characters[k] for k in shot_chars if k in characters}

    # Edit loop
    while True:
        if edit_prompt and auto_mode:
            prompt = edit_prompt
        else:
            prompt = questionary.text("Edit prompt (describe what to change):").ask()
            if not prompt:
                return

        from directors_chair.keyframe import edit_keyframe
        ok = edit_keyframe(
            prompt=prompt,
            keyframe_path=kf_path,
            output_path=kf_path,
            kling_params=kling_params,
            characters=shot_characters,
        )

        if not ok:
            console.print("[red]Keyframe edit failed.[/red]")
            if auto_mode:
                return
            retry = questionary.confirm("Try again?").ask()
            if retry:
                edit_prompt = None
                continue
            return

        console.print(f"[green]Keyframe {keyframe_index:03d} updated.[/green]")

        if auto_mode:
            return

        action = questionary.select("Result:", choices=[
            "Accept",
            "Edit again",
            "Back",
        ]).ask()

        if not action or action == "Accept" or action == "Back":
            input("\nPress Enter to continue...")
            return

        if action == "Edit again":
            edit_prompt = None
            continue


# ============================================================
# Regenerate Single Clip
# ============================================================

def regen_clip_command(storyboard_file=None, clip_index=None, auto_mode=False):
    """Regenerate a single video clip from its keyframe and beats."""
    config = load_config()
    storyboard, storyboard_path = _select_storyboard(config, storyboard_file)
    if storyboard is None:
        return

    name = storyboard["name"]
    shots = storyboard["shots"]
    characters = storyboard["characters"]
    kling_params = storyboard.get("kling_params", {})

    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    output_base = os.path.join(videos_dir, name)
    keyframes_dir = os.path.join(output_base, "keyframes")
    clips_dir = os.path.join(output_base, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    # Select clip
    if clip_index is None:
        if os.path.exists(clips_dir):
            clip_files = _list_clips(clips_dir, shots)
        else:
            # No clips yet — show shot list instead
            for i, shot in enumerate(shots):
                console.print(f"  {i:03d} — {shot.get('name', '?')}")
            clip_files = []

        choices = []
        for i, shot in enumerate(shots):
            choices.append(f"{i:03d} — {shot.get('name', '?')}")
        choices.append("Back")

        pick = questionary.select("Select clip to regenerate:", choices=choices).ask()
        if not pick or pick == "Back":
            return
        clip_index = int(pick.split(" ")[0])

    if clip_index >= len(shots):
        console.print(f"[red]Clip index {clip_index} out of range (0-{len(shots) - 1}).[/red]")
        return

    shot = shots[clip_index]
    shot_name = shot.get("name", "?")
    kf_path = os.path.join(keyframes_dir, f"keyframe_{clip_index:03d}.png")
    clip_path = os.path.join(clips_dir, f"clip_{clip_index:03d}.mp4")

    if not os.path.exists(kf_path):
        console.print(f"[red]Keyframe not found: {kf_path}. Generate keyframes first.[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    console.print(f"\n[bold]Regenerating clip {clip_index:03d}: {shot_name}[/bold]")

    # Delete existing clip
    if os.path.exists(clip_path):
        os.remove(clip_path)
        console.print(f"  [dim]Deleted existing clip.[/dim]")

    # Scope characters to shot
    shot_characters = characters
    if "characters" in shot and isinstance(shot["characters"], list):
        shot_characters = {k: characters[k] for k in shot["characters"] if k in characters}

    # Generate via Kling engine
    from directors_chair.video.engines.fal_kling_engine import FalKlingEngine
    engine = FalKlingEngine(kling_params=kling_params)
    ok = engine.generate_video(
        start_image_path=kf_path,
        beats=shot["beats"],
        characters=shot_characters,
        output_path=clip_path,
        kling_params=kling_params,
    )

    if ok:
        console.print(f"[green]Clip {clip_index:03d} regenerated successfully.[/green]")
    else:
        console.print(f"[red]Clip {clip_index:03d} generation failed.[/red]")

    if not auto_mode:
        input("\nPress Enter to continue...")


# ============================================================
# Submenu
# ============================================================

def clip_tools_menu():
    """Clip & Keyframe Tools submenu."""
    while True:
        console.print(Panel("[bold]Clip & Keyframe Tools[/bold]", border_style="cyan"))

        choice = questionary.select(
            "Select tool:",
            choices=[
                "a. Edit Clip (v2v)",
                "b. Edit Keyframe",
                "c. Regenerate Single Clip",
                "d. Back",
            ]
        ).ask()

        if not choice or "d." in choice:
            return

        if "a." in choice:
            edit_clip_command()
        elif "b." in choice:
            edit_keyframe_command()
        elif "c." in choice:
            regen_clip_command()
