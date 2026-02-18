import io
import os
import re
import time
import requests
from typing import Dict, Any, Optional

import fal_client
from PIL import Image


def _translate_prompt(prompt: str, characters: Dict[str, Any]) -> str:
    """Translate @Image1/@ElementN syntax to positional image references for Gemini.

    Image ordering: image 1 = composition layout, image 2+ = character references
    in the order they appear in the characters dict.
    """
    # Replace @Image1 with positional reference
    prompt = prompt.replace("@Image1", "image 1 (the composition layout)")

    # Replace @ElementN with positional references
    char_names = list(characters.keys())
    for i, char_name in enumerate(char_names):
        element_ref = f"@Element{i + 1}"
        image_num = i + 2  # image 1 is the comp, chars start at image 2
        prompt = prompt.replace(element_ref, f"the character from image {image_num}")

    return prompt


def generate_keyframe_nano_banana(
    prompt: str,
    comp_image_path: str,
    characters: Dict[str, Any],
    output_path: str,
    kling_params: Optional[Dict[str, Any]] = None,
    num_images: int = 1,
) -> bool:
    """Generate a keyframe via Nano Banana Pro (Gemini) image editing.

    Passes the Blender composition + all character reference images as
    image_urls, with a prompt that references them by position.

    Args:
        prompt: Keyframe prompt (can use @Image1/@ElementN syntax, will be translated)
        comp_image_path: Path to Blender layout composition PNG
        characters: Dict of character definitions with reference_image
        output_path: Where to save the generated keyframe PNG
        kling_params: Optional dict with aspect_ratio, resolution (reused for consistency)
        num_images: Number of keyframe variants to generate (1-4). If > 1,
                    saves as keyframe_001_v1.png, _v2.png, etc. for review.
    """
    from directors_chair.cli.utils import console

    params = kling_params or {}
    aspect_ratio = params.get("aspect_ratio", "16:9")
    resolution = params.get("resolution", "2K")

    # Upload composition reference
    with console.status("[cyan]Uploading composition reference...[/cyan]"):
        comp_url = fal_client.upload_file(comp_image_path)
    console.print(f"  [dim]composition: uploaded[/dim]")

    # Upload character references
    image_urls = [comp_url]
    char_names = list(characters.keys())
    for char_name in char_names:
        char_def = characters[char_name]
        ref_path = char_def["reference_image"]
        with console.status(f"[cyan]Uploading {char_name} reference...[/cyan]"):
            ref_url = fal_client.upload_file(ref_path)
        image_urls.append(ref_url)
        console.print(f"  [dim]{char_name}: uploaded[/dim]")

    # Build preamble explaining each image
    preamble_parts = ["You are given multiple reference images."]
    preamble_parts.append("Image 1 is a composition layout showing character positions and camera angle.")
    for i, char_name in enumerate(char_names):
        desc = characters[char_name].get("description", char_name)
        preamble_parts.append(f"Image {i + 2} is a reference photo of {char_name}: {desc}.")
    preamble_parts.append(
        "Generate a single photorealistic cinematic image that matches the composition "
        "layout from image 1, featuring the characters from the reference images in their "
        "correct positions. Each character must closely match their reference photo."
    )
    preamble = " ".join(preamble_parts)

    # Translate @Image/@Element references
    translated_prompt = _translate_prompt(prompt, characters)
    full_prompt = f"{preamble}\n\n{translated_prompt}"

    console.print(f"  [dim]Images: {len(image_urls)} (1 comp + {len(char_names)} characters)[/dim]")
    console.print(f"  [dim]Prompt: {translated_prompt[:80]}...[/dim]")

    # Submit to Nano Banana Pro edit (with retry on 500 errors)
    console.print(f"  [dim]Requesting {num_images} variant(s)[/dim]")
    max_retries = 3
    result = None
    for attempt in range(max_retries):
        try:
            with console.status("[cyan]Generating keyframe via Nano Banana Pro (Gemini)...[/cyan]") as status:
                handler = fal_client.submit(
                    "fal-ai/nano-banana-pro/edit",
                    arguments={
                        "prompt": full_prompt,
                        "image_urls": image_urls,
                        "aspect_ratio": aspect_ratio,
                        "resolution": resolution,
                        "output_format": "png",
                        "num_images": num_images,
                    },
                )
                for event in handler.iter_events(with_logs=True):
                    if isinstance(event, fal_client.InProgress):
                        if event.logs:
                            for log in event.logs:
                                msg = log.get('message', '') if isinstance(log, dict) else str(log)
                                console.print(f"  [dim]  gemini: {msg}[/dim]")
                                status.update(f"[cyan]{msg}[/cyan]")
                result = handler.get()
                break  # Success
        except Exception as e:
            if "500" in str(e) or "downstream_service_error" in str(e):
                if attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)
                    console.print(f"  [yellow]Server error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...[/yellow]")
                    time.sleep(wait)
                else:
                    console.print(f"  [red]Server error after {max_retries} attempts, giving up.[/red]")
                    raise
            else:
                raise

    # Log response metadata
    for key in result:
        if key != "images":
            console.print(f"  [dim]  response.{key}: {str(result[key])[:200]}[/dim]")

    images = result.get("images", [])
    if not images or not images[0].get("url"):
        console.print(f"[red]Keyframe generation failed — no image in response. {str(result)[:500]}[/red]")
        return False

    if num_images == 1:
        # Single image — save directly to output_path
        image_url = images[0]["url"]
        resp = requests.get(image_url)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        img.save(output_path)
        size_kb = os.path.getsize(output_path) // 1024
        console.print(f"  [green]Keyframe saved: {os.path.basename(output_path)} ({size_kb}KB)[/green]")
    else:
        # Multiple variants — save each with _v1, _v2, etc.
        base, ext = os.path.splitext(output_path)
        variant_paths = []
        for vi, img_data in enumerate(images):
            url = img_data.get("url")
            if not url:
                continue
            vpath = f"{base}_v{vi + 1}{ext}"
            resp = requests.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            img.save(vpath)
            size_kb = os.path.getsize(vpath) // 1024
            console.print(f"  [green]Variant {vi + 1}: {os.path.basename(vpath)} ({size_kb}KB)[/green]")
            variant_paths.append(vpath)

        console.print(f"  [yellow]Review variants and rename your pick to {os.path.basename(output_path)}[/yellow]")

    return True
