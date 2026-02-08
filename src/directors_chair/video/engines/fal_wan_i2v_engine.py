import os
import requests
import fal_client
from typing import Optional
from tqdm import tqdm
from .base import BaseVideoEngine


class FalWanI2VEngine(BaseVideoEngine):
    def generate_clip(self,
                      prompt: str,
                      start_image_path: str,
                      output_path: str,
                      end_image_path: Optional[str] = None,
                      resolution: str = "480p",
                      num_frames: int = 81,
                      fps: int = 16,
                      num_inference_steps: int = 30,
                      guide_scale: float = 5.0,
                      seed: Optional[int] = None,
                      negative_prompt: Optional[str] = None) -> bool:
        from directors_chair.cli.utils import console

        console.print(f"  Uploading image: {os.path.basename(start_image_path)}")
        image_url = fal_client.upload_file(start_image_path)

        arguments = {
            "prompt": prompt,
            "image_url": image_url,
            "resolution": resolution,
            "num_frames": num_frames,
            "frames_per_second": fps,
            "num_inference_steps": num_inference_steps,
            "guide_scale": guide_scale,
            "enable_safety_checker": False,
        }
        if seed is not None:
            arguments["seed"] = seed
        if negative_prompt:
            arguments["negative_prompt"] = negative_prompt

        console.print(f"  Submitting video generation job (wan-i2v)...")
        handler = fal_client.submit("fal-ai/wan-i2v", arguments=arguments)

        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress):
                if event.logs:
                    for log in event.logs:
                        console.print(f"    [dim]{log['message']}[/dim]")

        result = handler.get()

        video_url = result.get("video", {}).get("url")
        if not video_url:
            console.print(f"  [red]Error: No video URL in response[/red]")
            return False

        result_seed = result.get("seed")
        console.print(f"  Video generated (seed: {result_seed})")

        console.print(f"  Downloading clip to {os.path.basename(output_path)}...")
        response = requests.get(video_url, stream=True)
        total_size = int(response.headers.get("content-length", 0))

        with open(output_path, "wb") as f, tqdm(
            desc=os.path.basename(output_path),
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)

        return True
