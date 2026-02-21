import os
import re
import requests
from typing import Dict, Any, List, Optional, Tuple

import fal_client


def _resolve_voices(
    beats: List[Dict[str, str]],
    characters: Dict[str, Any],
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Scan beat prompts for <<<character_name>>> tags and resolve to voice_ids.

    Replaces <<<character_name>>> with <<<voice_N>>> in order of first appearance.
    Returns (updated_beats, voice_ids). voice_ids is empty if no tags found.
    """
    # Find all <<<name>>> tags across all beats in order of appearance
    seen = []
    pattern = re.compile(r"<<<(\w+)>>>")
    for beat in beats:
        for match in pattern.finditer(beat["prompt"]):
            name = match.group(1)
            if name not in seen and not name.startswith("voice_"):
                seen.append(name)

    if not seen:
        return beats, []

    # Strip @Element/@Image references — incompatible with voice mode (no elements)
    element_pattern = re.compile(r"@(?:Element|Image)\d+\s*")
    stripped_beats = []
    for beat in beats:
        stripped_beats.append({**beat, "prompt": element_pattern.sub("", beat["prompt"])})
    beats = stripped_beats

    # Map character names to voice_ids
    voice_ids = []
    name_to_slot = {}
    for name in seen:
        if name not in characters:
            raise ValueError(f"<<<{name}>>> in beat prompt but '{name}' not in characters")
        voice_id = characters[name].get("kling_voice_id")
        if not voice_id:
            raise ValueError(f"Character '{name}' has no kling_voice_id")
        slot = len(voice_ids) + 1
        name_to_slot[name] = f"<<<voice_{slot}>>>"
        voice_ids.append(voice_id)

    if len(voice_ids) > 2:
        raise ValueError(
            f"Kling supports max 2 voices per clip but found {len(voice_ids)}: {seen}"
        )

    # Replace <<<name>>> with <<<voice_N>>> in all beat prompts
    updated = []
    for beat in beats:
        prompt = beat["prompt"]
        for name, slot in name_to_slot.items():
            prompt = prompt.replace(f"<<<{name}>>>", slot)
        updated.append({**beat, "prompt": prompt})

    return updated, voice_ids


class FalKlingEngine:
    """Kling image-to-video engine with multi-prompt beats and character elements.

    Supports two modes:
    - **Elements mode** (O3): Character reference images for visual consistency, no audio.
    - **Voice mode** (V3 Pro): Custom voice_ids with native audio, no elements.
      Activated when beat prompts contain <<<character_name>>> tags.
    """

    def __init__(self, kling_params: Optional[Dict[str, Any]] = None):
        self.kling_params = kling_params or {}

    def generate_video(
        self,
        start_image_path: str,
        beats: List[Dict[str, str]],
        characters: Dict[str, Any],
        output_path: str,
        kling_params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Generate video via Kling i2v with multi-prompt beats.

        Args:
            start_image_path: Path to start keyframe PNG
            beats: List of {"prompt": str, "duration": str} dicts
            characters: Dict of character definitions with reference_image
            output_path: Where to save the generated MP4
            kling_params: Optional override for aspect_ratio etc.

        Returns:
            True if video was generated successfully
        """
        from directors_chair.cli.utils import console

        params = {**self.kling_params, **(kling_params or {})}
        aspect_ratio = params.get("aspect_ratio", "16:9")

        # Resolve voice tags in beat prompts
        resolved_beats, voice_ids = _resolve_voices(beats, characters)
        use_voices = len(voice_ids) > 0

        # Upload start keyframe
        with console.status("[cyan]Uploading start keyframe...[/cyan]"):
            start_url = fal_client.upload_file(start_image_path)

        # Build multi_prompt — ensure duration is string
        multi_prompt = []
        for beat in resolved_beats:
            multi_prompt.append({
                "prompt": beat["prompt"],
                "duration": str(beat["duration"]),
            })

        total_duration = sum(int(b["duration"]) for b in beats)
        console.print(f"  [dim]Beats: {len(beats)} ({'+'.join(b['duration'] + 's' for b in beats)} = {total_duration}s)[/dim]")

        if use_voices:
            # Voice mode — V3 Pro with native audio, no elements
            console.print(f"  [dim]Voice mode: {len(voice_ids)} voice(s) detected[/dim]")
            endpoint = "fal-ai/kling-video/v3/pro/image-to-video"
            arguments = {
                "start_image_url": start_url,
                "aspect_ratio": aspect_ratio,
                "generate_audio": True,
                "voice_ids": voice_ids,
            }
            # Use single prompt for 1 beat (avoids 512-char multi_prompt limit)
            if len(multi_prompt) == 1:
                arguments["prompt"] = multi_prompt[0]["prompt"]
                arguments["duration"] = multi_prompt[0]["duration"]
            else:
                arguments["multi_prompt"] = multi_prompt
        else:
            # Elements mode — O3 with character references, no audio
            elements = []
            for char_name, char_def in characters.items():
                ref_path = char_def["reference_image"]
                with console.status(f"[cyan]Uploading {char_name} reference...[/cyan]"):
                    ref_url = fal_client.upload_file(ref_path)
                elements.append({
                    "frontal_image_url": ref_url,
                    "reference_image_urls": [ref_url],
                })
            endpoint = "fal-ai/kling-video/o3/standard/image-to-video"
            arguments = {
                "image_url": start_url,
                "aspect_ratio": aspect_ratio,
                "elements": elements,
            }
            if len(multi_prompt) == 1:
                arguments["prompt"] = multi_prompt[0]["prompt"]
                arguments["duration"] = multi_prompt[0]["duration"]
            else:
                arguments["multi_prompt"] = multi_prompt

        # Submit to Kling
        label = "V3 Pro (voice)" if use_voices else "O3 (elements)"
        with console.status(f"[cyan]Generating video via Kling {label}...[/cyan]") as status:
            handler = fal_client.submit(endpoint, arguments=arguments)
            for event in handler.iter_events(with_logs=True):
                if isinstance(event, fal_client.InProgress) and event.logs:
                    for log in event.logs:
                        status.update(f"[cyan]{log.get('message', '')}[/cyan]")
            result = handler.get()

        # Extract video URL
        result_url = result.get("video", {}).get("url")
        if not result_url:
            result_url = result.get("url")
        if not result_url:
            console.print("[red]Video generation failed — no video URL in response[/red]")
            console.print(f"[red]Response: {result}[/red]")
            return False

        # Download video
        console.print("  [dim]Downloading video...[/dim]")
        response = requests.get(result_url, stream=True)
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

        console.print(f"  [green]Video saved: {os.path.basename(output_path)} ({downloaded // 1024}KB)[/green]")
        return True
