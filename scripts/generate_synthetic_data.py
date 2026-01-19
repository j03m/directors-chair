import sys
import os
import torch
import random
import argparse
from diffusers import FluxPipeline
from dotenv import load_dotenv

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from directors_chair.config import load_config, get_prompt


def generate_data(prompt_input: str, name: str, model_key: str, num_images: int = 1):
    load_dotenv()
    config = load_config()

    # Validate model key against config
    if model_key not in config['model_ids']:
        print(f"❌ Error: Model '{model_key}' not found in config.json")
        print(f"   Available models: {list(config['model_ids'].keys())}")
        sys.exit(1)

    # Construct path using config directory + model key (folder name)
    models_dir = config['directories']['models']
    local_model_path = os.path.join(models_dir, model_key)

    output_dir = os.path.join(config['directories']['training_data'], name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"DEBUG: Looking for model at: {local_model_path}")

    if not os.path.exists(local_model_path):
        print(f"❌ CRITICAL ERROR: Folder not found: {local_model_path}")
        sys.exit(1)

    print(f"✅ Found model '{model_key}'. Loading...")

    pipe = FluxPipeline.from_pretrained(
        local_model_path,
        local_files_only=True,
        torch_dtype=torch.bfloat16
    )

    print("Enabling model CPU offload...")
    pipe.enable_model_cpu_offload()

    prompt = get_prompt(prompt_input)
    print(f"Generating {num_images} images for '{name}' using {model_key}...")

    for i in range(num_images):
        seed = random.randint(0, 2 ** 32 - 1)
        print(f"[{i + 1}/{num_images}] Generating (Seed: {seed})...")

        image = pipe(
            prompt,
            guidance_scale=0.0,  # Note: Flux Dev might prefer 3.5, Schnell needs 0.0
            num_inference_steps=4,  # Note: Dev needs ~20-30, Schnell needs ~4
            max_sequence_length=512,
            generator=torch.Generator("cpu").manual_seed(seed)
        ).images[0]

        output_path = os.path.join(output_dir, f"{name}_{i}_{seed}.png")
        image.save(output_path)
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic training data using Flux.")
    parser.add_argument("prompt", type=str, help="Prompt string or path to .txt file.")
    parser.add_argument("--name", type=str, required=True, help="Character name (creates subfolder).")
    parser.add_argument("--num-images", type=int, default=1, help="Count.")

    # NEW: Allow selecting the model key from config
    parser.add_argument("--model", type=str, default="flux-schnell",
                        help="Key from config.json (default: flux-schnell)")

    args = parser.parse_args()

    generate_data(args.prompt, args.name, args.model, args.num_images)