import os
import torch
import random
import argparse
from diffusers import FluxPipeline
from dotenv import load_dotenv
from directors_chair.config import load_config, get_prompt


def generate_data(prompt_input: str, name: str, num_images: int = 1):
    load_dotenv()
    config = load_config()

    models_dir = config['directories']['models']

    # 1. Construct the explicit path to the flat folder created by setup.py
    # This matches the key in config.json ('flux_schnell')
    model_path = os.path.join(models_dir, "flux_schnell")

    # 2. Output directory logic
    output_dir = os.path.join(config['directories']['training_data'], name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading Flux Schnell from local path: {model_path}...")

    # Check if the model actually exists to avoid cryptic HF errors
    if not os.path.exists(model_path):
        print(f"❌ CRITICAL ERROR: Path not found: {model_path}")
        print("   Run 'python scripts/setup.py' first.")
        return

    # 3. Load from the PATH, not the Repo ID
    pipe = FluxPipeline.from_pretrained(
        model_path,  # <--- Pointing to the folder, not the web ID
        local_files_only=True,  # Safe now, because we know the files are flat
        torch_dtype=torch.bfloat16
    )

    print("Enabling model CPU offload...")
    pipe.enable_model_cpu_offload()

    prompt = get_prompt(prompt_input)
    print(f"Generating {num_images} images for '{name}'...")

    for i in range(num_images):
        seed = random.randint(0, 2 ** 32 - 1)
        print(f"[{i + 1}/{num_images}] Generating (Seed: {seed})...")

        image = pipe(
            prompt,
            guidance_scale=0.0,
            num_inference_steps=4,
            max_sequence_length=256,
            generator=