import os
import subprocess
import tempfile
import time
import requests
from typing import Dict, Any, List, Optional

import fal_client


def _ensure_min_720p(video_path: str) -> str:
    """Scale video to 1280x720 if dimensions are below 720px height.

    Kling i2v returns slightly varying resolutions per clip (e.g. 716px instead
    of 720px). The O1 v2v edit API requires minimum 720px height. This rescales
    undersized clips to exactly 1280x720 using the same approach as the stitch
    pipeline.

    Returns the path to use for upload (original if already >=720p, or a temp file).
    """
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    if probe.returncode != 0:
        return video_path

    parts = probe.stdout.strip().split(",")
    if len(parts) != 2:
        return video_path

    width, height = int(parts[0]), int(parts[1])
    if height >= 720:
        return video_path

    # Scale to 1280x720, pad if needed
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
         "-c:v", "libx264", "-crf", "18", "-preset", "fast",
         "-c:a", "copy", tmp.name],
        capture_output=True
    )
    return tmp.name


def edit_clip(
    prompt: str,
    video_path: str,
    output_path: str,
    characters: Optional[Dict[str, Any]] = None,
    keep_audio: bool = True,
) -> bool:
    """Edit an existing video clip via Kling O3 Video-to-Video Edit.

    Preserves original motion and camera while applying pixel-level edits
    based on the prompt. Use @Element1/@Element2 to reference character elements.

    Args:
        prompt: Edit instruction describing desired changes.
        video_path: Path to existing .mp4 clip (3-10s, 720-2160px, max 200MB).
        output_path: Where to save the edited .mp4.
        characters: Optional dict of character definitions with reference_image.
        keep_audio: Whether to preserve original audio (default True).

    Returns:
        True if edit succeeded and file was saved.
    """
    from directors_chair.cli.utils import console

    # Ensure clip meets 720px minimum height requirement
    upload_path = _ensure_min_720p(video_path)
    scaled = upload_path != video_path
    if scaled:
        console.print("  [dim]Scaled clip to 720p for API compatibility[/dim]")

    # Upload video
    try:
        with console.status("[cyan]Uploading video clip...[/cyan]"):
            video_url = fal_client.upload_file(upload_path)
        console.print(f"  [dim]Video uploaded ({os.path.getsize(upload_path) // 1024}KB)[/dim]")
    finally:
        # Clean up temp file if we created one
        if scaled and os.path.exists(upload_path):
            os.unlink(upload_path)

    # Build elements from characters
    elements = []
    if characters:
        for char_name, char_def in characters.items():
            ref_path = char_def["reference_image"]
            with console.status(f"[cyan]Uploading {char_name} reference...[/cyan]"):
                ref_url = fal_client.upload_file(ref_path)
            elements.append({
                "frontal_image_url": ref_url,
                "reference_image_urls": [ref_url],
            })
            console.print(f"  [dim]{char_name}: uploaded[/dim]")

    # Enforce API constraint: max 4 elements
    if len(elements) > 4:
        console.print(f"[red]Too many character elements ({len(elements)}). API max is 4.[/red]")
        return False

    # Build arguments
    arguments = {
        "prompt": prompt,
        "video_url": video_url,
        "keep_audio": keep_audio,
    }
    if elements:
        arguments["elements"] = elements

    console.print(f"  [dim]Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}[/dim]")
    console.print(f"  [dim]Elements: {len(elements)}[/dim]")

    # Submit with retry
    max_retries = 3
    result = None
    for attempt in range(max_retries):
        try:
            with console.status("[cyan]Editing video via Kling O3 v2v...[/cyan]") as status:
                handler = fal_client.submit(
                    "fal-ai/kling-video/o3/standard/video-to-video/edit",
                    arguments=arguments,
                )
                for event in handler.iter_events(with_logs=True):
                    if isinstance(event, fal_client.InProgress) and event.logs:
                        for log in event.logs:
                            msg = log.get("message", "") if isinstance(log, dict) else str(log)
                            status.update(f"[cyan]{msg}[/cyan]")
                result = handler.get()
                break
        except Exception as e:
            err_str = str(e)
            if "422" in err_str:
                console.print(f"  [red]Content filter rejected edit (422).[/red]")
                return False
            elif "500" in err_str or "downstream_service_error" in err_str:
                if attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)
                    console.print(f"  [yellow]Server error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...[/yellow]")
                    time.sleep(wait)
                else:
                    console.print(f"  [red]Server error after {max_retries} attempts.[/red]")
                    raise
            else:
                raise

    if result is None:
        console.print("[red]Video edit failed — no result[/red]")
        return False

    # Extract video URL
    result_url = result.get("video", {}).get("url")
    if not result_url:
        result_url = result.get("url")
    if not result_url:
        console.print("[red]Video edit failed — no video URL in response[/red]")
        console.print(f"[red]Response: {result}[/red]")
        return False

    # Download
    console.print("  [dim]Downloading edited video...[/dim]")
    response = requests.get(result_url, stream=True)
    downloaded = 0
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)

    console.print(f"  [green]Edited clip saved: {os.path.basename(output_path)} ({downloaded // 1024}KB)[/green]")
    return True
