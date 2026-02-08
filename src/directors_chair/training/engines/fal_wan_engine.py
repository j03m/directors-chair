import os
import zipfile
import requests
import fal_client
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from .base import BaseTrainingEngine


class FalWanTrainingEngine(BaseTrainingEngine):
    def __init__(self):
        self._last_lora_url: Optional[str] = None

    def train(self,
              dataset_path: str,
              output_name: str,
              trigger_word: str,
              steps: int,
              rank: int = 16,
              model_id: str = "",
              base_model_type: str = "",
              learning_rate: float = 0.0002,
              auto_scale_input: bool = True) -> bool:
        from directors_chair.cli.utils import console

        dataset_path = os.path.abspath(dataset_path)
        output_dir = os.path.join(os.path.abspath(os.getcwd()), "assets", "loras")
        os.makedirs(output_dir, exist_ok=True)

        # 1. Zip the dataset
        zip_path = Path(f"/tmp/{output_name}_wan_training.zip")
        console.print(f"[cyan]Zipping training data from {dataset_path}...[/cyan]")

        file_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(dataset_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.txt', '.mp4')):
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(dataset_path)
                        zipf.write(file_path, arcname)
                        if not file.lower().endswith('.txt'):
                            file_count += 1

        console.print(f"  Zipped {file_count} media files")

        # 2. Upload zip to fal storage
        console.print("[cyan]Uploading training data to fal.ai...[/cyan]")
        training_data_url = fal_client.upload_file(str(zip_path))
        console.print(f"  [green]Uploaded[/green]")

        # 3. Submit WAN training job
        console.print("[cyan]Submitting WAN LoRA training job...[/cyan]")
        console.print(f"  Trigger phrase: {trigger_word}")
        console.print(f"  Steps: {steps}")
        console.print(f"  Learning rate: {learning_rate}")

        handler = fal_client.submit(
            "fal-ai/wan-trainer",
            arguments={
                "training_data_url": training_data_url,
                "trigger_phrase": trigger_word,
                "number_of_steps": steps,
                "learning_rate": learning_rate,
                "auto_scale_input": auto_scale_input,
            },
        )

        # 4. Stream logs
        for event in handler.iter_events(with_logs=True):
            if isinstance(event, fal_client.InProgress):
                if event.logs:
                    for log in event.logs:
                        console.print(f"    [dim]{log['message']}[/dim]")

        result = handler.get()

        # 5. Download the trained LoRA
        lora_url = result.get("lora_file", {}).get("url")
        if not lora_url:
            console.print("[red]Error: No LoRA URL in training result[/red]")
            console.print(f"[dim]Full result: {result}[/dim]")
            return False

        self._last_lora_url = lora_url

        output_path = os.path.join(output_dir, f"{output_name}.safetensors")
        console.print(f"[cyan]Downloading trained LoRA to {output_path}...[/cyan]")

        response = requests.get(lora_url, stream=True)
        total_size = int(response.headers.get("content-length", 0))
        with open(output_path, "wb") as f, tqdm(
            desc=output_name,
            total=total_size, unit="iB", unit_scale=True, unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)

        # 6. Cleanup
        zip_path.unlink(missing_ok=True)

        console.print(f"\n[bold green]WAN LoRA training complete![/bold green]")
        console.print(f"  Local: {output_path}")
        console.print(f"  Remote URL: {lora_url}")
        return True

    @property
    def last_lora_url(self) -> Optional[str]:
        return self._last_lora_url
