import os
import requests
from typing import Dict, Any, List, Optional

import fal_client


class FalKlingEngine:
    """Kling O3 image-to-video engine with multi-prompt beats and character elements.

    This engine does NOT inherit BaseVideoEngine — the interface is fundamentally
    different (beats instead of frames, elements for character consistency).
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
        """Generate video via Kling O3 i2v with multi-prompt beats.

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

        # Upload start keyframe
        with console.status("[cyan]Uploading start keyframe...[/cyan]"):
            start_url = fal_client.upload_file(start_image_path)

        # Upload character references and build elements
        elements = []
        for char_name, char_def in characters.items():
            ref_path = char_def["reference_image"]
            with console.status(f"[cyan]Uploading {char_name} reference...[/cyan]"):
                ref_url = fal_client.upload_file(ref_path)
            elements.append({
                "frontal_image_url": ref_url,
                "reference_image_urls": [ref_url],
            })

        # Build multi_prompt — ensure duration is string
        multi_prompt = []
        for beat in beats:
            multi_prompt.append({
                "prompt": beat["prompt"],
                "duration": str(beat["duration"]),
            })

        total_duration = sum(int(b["duration"]) for b in beats)
        console.print(f"  [dim]Beats: {len(beats)} ({'+'.join(b['duration'] + 's' for b in beats)} = {total_duration}s)[/dim]")

        # Submit to Kling O3 i2v
        with console.status("[cyan]Generating video via Kling O3 i2v...[/cyan]") as status:
            handler = fal_client.submit(
                "fal-ai/kling-video/o3/standard/image-to-video",
                arguments={
                    "image_url": start_url,
                    "multi_prompt": multi_prompt,
                    "aspect_ratio": aspect_ratio,
                    "elements": elements,
                },
            )
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
