import io
import requests
import fal_client
from typing import Optional, List, Dict
from PIL import Image
from .engine import BaseGenerator


class FalFluxGenerator(BaseGenerator):
    def __init__(self, local_model_path: str = None, lora_paths: list[str] = None,
                 lora_urls: Optional[List[Dict]] = None):
        """
        Args:
            local_model_path: Unused (fal.ai is cloud-based).
            lora_paths: Local LoRA paths — resolved to fal URLs via config at generation time.
            lora_urls: Direct fal.ai LoRA URLs [{path: url, scale: float}].
        """
        self.lora_urls = lora_urls or []
        self._lora_paths = lora_paths or []

    def _resolve_lora_urls(self) -> List[Dict]:
        """Resolve local LoRA paths to fal URLs via config, or use direct URLs."""
        if self.lora_urls:
            return self.lora_urls

        if not self._lora_paths:
            return []

        from directors_chair.config.loader import load_config
        config = load_config()
        config_loras = config.get("loras", {})

        resolved = []
        for path in self._lora_paths:
            # Find matching config entry by path
            for name, entry in config_loras.items():
                if entry.get("path") == path and entry.get("fal_url"):
                    resolved.append({"path": entry["fal_url"], "scale": 1.0})
                    break
            else:
                # If no fal_url found, try uploading the local file
                from directors_chair.cli.utils import console
                console.print(f"  [yellow]No fal URL for {path}, uploading...[/yellow]")
                url = fal_client.upload_file(path)
                resolved.append({"path": url, "scale": 1.0})

        return resolved

    def generate(self, prompt: str, steps: int, seed: int):
        from directors_chair.cli.utils import console

        loras = self._resolve_lora_urls()

        # flux-lora endpoint is the dev model (high quality, up to 50 steps)
        # flux/dev is the same without LoRA support
        endpoint = "fal-ai/flux-lora" if loras else "fal-ai/flux/dev"

        # Clamp steps to endpoint limits
        if steps > 50:
            steps = 28

        arguments = {
            "prompt": prompt,
            "num_inference_steps": steps,
            "guidance_scale": 3.5,
            "seed": seed,
            "enable_safety_checker": False,
            "output_format": "png",
            "image_size": "square_hd",
        }

        if loras:
            arguments["loras"] = loras

        console.print(f"  [dim]Submitting to {endpoint}...[/dim]")
        handler = fal_client.submit(endpoint, arguments=arguments)

        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress):
                if event.logs:
                    for log in event.logs:
                        console.print(f"    [dim]{log['message']}[/dim]")

        result = handler.get()

        images = result.get("images", [])
        if not images:
            raise RuntimeError(f"No images in fal.ai response: {result}")

        image_url = images[0].get("url")
        if not image_url:
            raise RuntimeError(f"No image URL in response: {images[0]}")

        result_seed = result.get("seed")
        console.print(f"  [dim]Generated (seed: {result_seed})[/dim]")

        # Download and return as PIL Image
        response = requests.get(image_url)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
