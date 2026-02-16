import os
import subprocess
import questionary
from rich.table import Table
from directors_chair.config.loader import load_config
from directors_chair.cli.utils import console


def assemble_movie(clip_names=None, movie_name=None, auto_mode=False):
    """Assemble multiple storyboard final videos into a movie.

    Args:
        clip_names: List of storyboard names in order (skips selection if provided).
        movie_name: Output movie name (skips naming prompt if provided).
        auto_mode: If True, skip all interactive prompts.
    """
    config = load_config()
    videos_dir = config.get("directories", {}).get("videos", "assets/generated/videos")
    movies_dir = config.get("directories", {}).get("movies", "assets/generated/movies")

    if not os.path.exists(videos_dir):
        console.print(f"[red]Videos directory not found: {videos_dir}/[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    # Find all final storyboard videos (name/name.mp4)
    available = []
    for entry in sorted(os.listdir(videos_dir)):
        entry_dir = os.path.join(videos_dir, entry)
        if not os.path.isdir(entry_dir):
            continue
        final_video = os.path.join(entry_dir, f"{entry}.mp4")
        if os.path.exists(final_video):
            size_mb = os.path.getsize(final_video) / (1024 * 1024)
            available.append((entry, final_video, size_mb))

    if not available:
        console.print("[yellow]No completed storyboard videos found.[/yellow]")
        console.print(f"[dim]Looking in: {videos_dir}/*/[/dim]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    # Display available clips
    table = Table(title="Available Storyboard Videos")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Storyboard", style="white")
    table.add_column("Size", style="yellow", width=10)
    table.add_column("Path", style="dim")

    for i, (name, path, size) in enumerate(available):
        table.add_row(str(i + 1), name, f"{size:.1f}MB", path)

    console.print(table)

    if auto_mode and clip_names and movie_name:
        # Autonomous mode: resolve clip names to paths
        available_dict = {name: (path, size) for name, path, size in available}
        selected = []
        for cn in clip_names:
            if cn not in available_dict:
                console.print(f"[red]Clip '{cn}' not found. Available: {', '.join(available_dict.keys())}[/red]")
                return
            path, size = available_dict[cn]
            selected.append((cn, path, size))

        console.print(f"\n[bold]Auto mode: assembling {len(selected)} clips as '{movie_name}'[/bold]")
        for i, (name, _, _) in enumerate(selected):
            console.print(f"  {i + 1}. {name}")
    else:
        # Interactive mode
        choices = [f"{name} ({size:.1f}MB)" for name, _, size in available]

        console.print("\n[bold]Select clips in the order they should appear in the movie.[/bold]")
        console.print("[dim]You'll pick them one at a time. Same clip can be used multiple times.[/dim]\n")

        selected = []
        while True:
            pick = questionary.select(
                f"Clip {len(selected) + 1}:",
                choices=choices + ["--- Done (assemble) ---", "--- Cancel ---"]
            ).ask()

            if not pick or pick == "--- Cancel ---":
                if not selected:
                    return
                confirm = questionary.confirm("Discard selection?").ask()
                if confirm:
                    return
                continue

            if pick == "--- Done (assemble) ---":
                if len(selected) < 2:
                    console.print("[yellow]Need at least 2 clips to assemble.[/yellow]")
                    continue
                break

            # Find which clip was selected
            idx = choices.index(pick)
            selected.append(available[idx])
            console.print(f"  [green]Added: {available[idx][0]}[/green]")

        # Show assembly order
        console.print("\n[bold]Assembly order:[/bold]")
        for i, (name, _, _) in enumerate(selected):
            console.print(f"  {i + 1}. {name}")

        # Name the movie
        movie_name = questionary.text(
            "Movie name:",
            default="movie"
        ).ask()

        if not movie_name:
            return

    os.makedirs(movies_dir, exist_ok=True)
    output_path = os.path.join(movies_dir, f"{movie_name}.mp4")

    if os.path.exists(output_path):
        if auto_mode:
            console.print(f"[yellow]Overwriting existing {movie_name}.mp4[/yellow]")
        else:
            overwrite = questionary.confirm(f"{movie_name}.mp4 already exists. Overwrite?").ask()
            if not overwrite:
                return

    # Stitch with re-encoding to common resolution
    console.print(f"\n[bold]Assembling {len(selected)} clips...[/bold]")

    clip_paths = [path for _, path, _ in selected]
    inputs = []
    filter_parts = []
    for i, cp in enumerate(clip_paths):
        inputs.extend(["-i", os.path.abspath(cp)])
        filter_parts.append(
            f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
        )

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
        output_path
    ]

    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]ffmpeg failed (exit {e.returncode})[/red]")
        if not auto_mode:
            input("\nPress Enter to continue...")
        return

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    console.print(f"\n[bold green]Movie assembled: {output_path} ({size_mb:.1f}MB)[/bold green]")
    if not auto_mode:
        input("\nPress Enter to continue...")
