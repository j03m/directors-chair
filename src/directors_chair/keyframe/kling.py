import io
import os
import requests
from typing import Dict, Any, Optional, List

import fal_client
from PIL import Image


MAX_ELEMENTS_PER_PASS = 2


def _run_kling_i2i(prompt, image_url, elements, aspect_ratio, resolution):
    """Run a single Kling O3 i2i pass. Returns result image URL or None."""
    from directors_chair.cli.utils import console

    with console.status("[cyan]Generating via Kling O3 i2i...[/cyan]") as status:
        handler = fal_client.submit(
            "fal-ai/kling-image/o3/image-to-image",
            arguments={
                "prompt": prompt,
                "image_urls": [image_url],
                "elements": elements,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            },
        )
        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress):
                if event.logs:
                    for log in event.logs:
                        msg = log.get('message', '') if isinstance(log, dict) else str(log)
                        console.print(f"  [dim]  kling: {msg}[/dim]")
                        status.update(f"[cyan]{msg}[/cyan]")
        result = handler.get()

    # Log full response keys for debugging
    for key in result:
        if key != "images":
            console.print(f"  [dim]  response.{key}: {str(result[key])[:200]}[/dim]")

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        console.print(f"  [red]No image in response. Full result: {str(result)[:500]}[/red]")
        return None

    # Log image metadata if present
    img_data = images[0]
    for key in img_data:
        if key != "url":
            console.print(f"  [dim]  image.{key}: {str(img_data[key])[:200]}[/dim]")

    return img_data["url"]


def _upload_and_build_elements(char_names, characters):
    """Upload character references and build Kling elements list."""
    from directors_chair.cli.utils import console

    elements = []
    for char_name in char_names:
        char_def = characters[char_name]
        ref_path = char_def["reference_image"]
        with console.status(f"[cyan]Uploading {char_name} reference...[/cyan]"):
            ref_url = fal_client.upload_file(ref_path)
        elements.append({
            "frontal_image_url": ref_url,
            "reference_image_urls": [ref_url],
        })
        console.print(f"  [dim]{char_name}: uploaded[/dim]")
    return elements


def generate_keyframe_kling(
    prompt: Optional[str],
    comp_image_path: str,
    characters: Dict[str, Any],
    output_path: str,
    kling_params: Optional[Dict[str, Any]] = None,
    keyframe_passes: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Generate a keyframe via Kling O3 image-to-image.

    Two modes:
    - Single pass: provide `prompt` — all characters used as elements (max 2).
    - Multi-pass: provide `keyframe_passes` — each pass specifies which
      characters to use and its own prompt. Pass 1 uses the Blender comp
      as @Image1, subsequent passes use the previous result.

    keyframe_passes format:
        [
            {"characters": ["cranial", "robot"], "prompt": "...@Element1...@Element2..."},
            {"characters": ["gorilla"], "prompt": "...@Element1...add gorilla..."},
        ]
    """
    from directors_chair.cli.utils import console

    params = kling_params or {}
    aspect_ratio = params.get("aspect_ratio", "16:9")
    resolution = params.get("resolution", "2K")

    # Upload composition reference
    with console.status("[cyan]Uploading composition reference...[/cyan]"):
        comp_url = fal_client.upload_file(comp_image_path)

    if keyframe_passes:
        # Multi-pass mode
        console.print(f"  [bold]Multi-pass keyframe: {len(keyframe_passes)} passes[/bold]")
        result_url = comp_url

        for i, kp in enumerate(keyframe_passes):
            pass_chars = kp["characters"]
            pass_prompt = kp["prompt"]

            if len(pass_chars) > MAX_ELEMENTS_PER_PASS:
                console.print(f"[red]Pass {i + 1}: max {MAX_ELEMENTS_PER_PASS} characters per pass, got {len(pass_chars)}[/red]")
                return False

            console.print(f"  [cyan]Pass {i + 1}: {', '.join(pass_chars)}[/cyan]")
            elements = _upload_and_build_elements(pass_chars, characters)

            console.print(f"  [dim]Prompt: {pass_prompt[:80]}...[/dim]")
            result_url = _run_kling_i2i(
                pass_prompt, result_url, elements, aspect_ratio, resolution
            )

            if not result_url:
                console.print(f"[red]Pass {i + 1} failed — no image in response[/red]")
                return False

            console.print(f"  [green]Pass {i + 1} complete[/green]")
    else:
        # Single pass mode
        char_names = list(characters.keys())
        console.print(f"  [dim]Single pass ({len(char_names)} characters)[/dim]")
        elements = _upload_and_build_elements(char_names, characters)
        console.print(f"  [dim]Prompt: {prompt[:80]}...[/dim]")
        result_url = _run_kling_i2i(prompt, comp_url, elements, aspect_ratio, resolution)

    if not result_url:
        console.print("[red]Keyframe generation failed — no image in response[/red]")
        return False

    # Download final result
    response = requests.get(result_url)
    response.raise_for_status()
    img = Image.open(io.BytesIO(response.content))
    img.save(output_path)

    size_kb = os.path.getsize(output_path) // 1024
    console.print(f"  [green]Keyframe saved: {os.path.basename(output_path)} ({size_kb}KB)[/green]")
    return True
