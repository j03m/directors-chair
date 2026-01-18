import os
import sys
import zipfile
import requests
import fal_client
from dotenv import load_dotenv
from tqdm import tqdm
from pathlib import Path

def train_lora(folder_name: str, trigger_word: str) -> None:
    load_dotenv()
    
    base_path = Path("assets/training_data") / folder_name
    if not base_path.exists():
        print(f"Error: {base_path} does not exist.")
        sys.exit(1)

    zip_path = Path(f"{folder_name}.zip")
    print(f"Zipping {base_path} to {zip_path}...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(base_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(base_path)
                zipf.write(file_path, arcname)

    print("Uploading zip file...")
    url = fal_client.upload_file(str(zip_path))
    print(f"Uploaded to {url}")

    print("Submitting training job...")
    handler = fal_client.submit(
        "fal-ai/flux-lora-fast-training",
        arguments={
            "images_data_url": url,
            "trigger_word": trigger_word,
            "steps": 1000
        },
    )

    print("Training started. Streaming logs...")
    for event in handler.iter_events(with_logs=True):
        if isinstance(event, fal_client.InProgress):
            if event.logs:
                for log in event.logs:
                    print(log["message"])

    result = handler.get()
    print("Training complete.")

    lora_url = result.get("diffusers_lora_file", {}).get("url")
    if not lora_url:
        print("Error: No LoRA URL found in result.")
        print(result)
        sys.exit(1)

    output_dir = Path("assets/loras")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{folder_name}.safetensors"

    print(f"Downloading LoRA to {output_path}...")
    response = requests.get(lora_url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    
    with open(output_path, "wb") as f, tqdm(
        desc=output_path.name,
        total=total_size,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)

    print("Cleaning up...")
    zip_path.unlink()
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/train_lora.py <folder_name> <trigger_word>")
        sys.exit(1)
    
    train_lora(sys.argv[1], sys.argv[2])
