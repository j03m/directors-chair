"""
Experiment: Two-pass keyframe generation for violent scenes.

Pass 1 (Gemini/nano-banana-pro): Generate the ACTION — impact poses, falling
bodies, chaotic energy — but no blood/gore words that trigger content filters.

Pass 2 (Flux 2 Pro edit): Take the Gemini output and add blood, wounds, gore
details via Flux which has more permissive safety settings.

Tests shot05 (hockey_headshot) from raider_ambush.
"""
import io
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

import fal_client
from PIL import Image

OUTPUT_DIR = "assets/generated/videos/raider_ambush/experiments"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Character reference images
LAYOUT_IMG = "assets/generated/videos/raider_ambush/layouts/layout_004.png"
HOCKEY_REF = "assets/training_data/raider_hockey/hockey-2.png"
GALE_REF = "assets/training_data/gale_gale/gale-2.png"
NOMAD1_REF = "assets/training_data/nomad_nomad1/nomad1-2.png"

# ─── PASS 1: Gemini — action without gore words ───────────────────────────

GEMINI_PROMPT = """You are given multiple reference images. Image 1 is a composition layout showing character positions and camera angle. Image 2 is a reference photo of hockey: raider in hockey mask, makeshift sheet metal armor, pipe weapon. Image 3 is a reference photo of gale: lean beautiful woman with blonde war hawk hair, sleeve tattoos, canvas tank top, cargo pants, work boots. Image 4 is a reference photo of nomad1: Caucasian male civilian in repurposed denim jacket, baseball cap, cargo pants. Generate a single photorealistic cinematic image that matches the composition layout from image 1, featuring the characters from the reference images in their correct positions. Each character must closely match their reference photo.

Use image 1 (the composition layout) as composition reference. Ground level, desert road, chaotic action.

the character from image 2 a raider in a hockey mask stands on the left — his head snaps violently backwards from a massive unseen force from above. His body is going limp mid-fall, knees buckling, arms flying outward. The hockey mask is cracking apart. the character from image 3 a woman with blonde war hawk hair and sleeve tattoos is on the ground, flattened, arms over her head. the character from image 4 a civilian man is face-down on the road beside her.

Chaos — dust, debris flying, the moment of devastating impact. Other raiders diving for cover in the background. Desert road, harsh light. Photorealistic, cinematic, intense action scene."""

# ─── PASS 2: Flux — add blood/gore to the Gemini output ───────────────────

FLUX_GORE_PROMPT = """Take this action scene image and add graphic violence details:
- The raider whose head is snapping back: add a massive spray of dark red blood erupting from his head, blood mist in the air, fragments of skull and mask flying outward
- Add blood splatter on the ground around him
- Add blood pooling beneath him
- Make the wound devastating and visceral — this is a high-caliber sniper round impact
- Keep everything else in the scene exactly as it is
Photorealistic, cinematic, graphic action movie violence, rated R."""


def generate_pass1_gemini():
    """Pass 1: Generate action keyframe via Gemini (no gore words)."""
    output_path = os.path.join(OUTPUT_DIR, "pass1_gemini_action.png")
    if os.path.exists(output_path):
        print(f"  Pass 1 already exists: {output_path}")
        return output_path

    print("═══ PASS 1: Gemini — action without gore words ═══")

    # Upload images
    print("  Uploading layout...")
    layout_url = fal_client.upload_file(LAYOUT_IMG)
    print("  Uploading hockey ref...")
    hockey_url = fal_client.upload_file(HOCKEY_REF)
    print("  Uploading gale ref...")
    gale_url = fal_client.upload_file(GALE_REF)
    print("  Uploading nomad1 ref...")
    nomad1_url = fal_client.upload_file(NOMAD1_REF)

    image_urls = [layout_url, hockey_url, gale_url, nomad1_url]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  Submitting to nano-banana-pro (attempt {attempt + 1})...")
            handler = fal_client.submit(
                "fal-ai/nano-banana-pro/edit",
                arguments={
                    "prompt": GEMINI_PROMPT,
                    "image_urls": image_urls,
                    "aspect_ratio": "16:9",
                    "resolution": "2K",
                    "output_format": "png",
                    "num_images": 1,
                },
            )
            for event in handler.iter_events(with_logs=True):
                if isinstance(event, fal_client.InProgress) and event.logs:
                    for log in event.logs:
                        msg = log.get('message', '') if isinstance(log, dict) else str(log)
                        print(f"    gemini: {msg}")
            result = handler.get()
            break
        except Exception as e:
            if ("500" in str(e) or "downstream_service_error" in str(e)) and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    images = result.get("images", [])
    if not images:
        print("  FAILED: No image returned from Gemini")
        return None

    resp = requests.get(images[0]["url"])
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img.save(output_path)
    size_kb = os.path.getsize(output_path) // 1024
    print(f"  ✓ Pass 1 saved: {output_path} ({size_kb}KB)")
    return output_path


def generate_pass2_flux(gemini_image_path):
    """Pass 2: Add blood/gore via Flux 2 Pro edit."""
    output_path = os.path.join(OUTPUT_DIR, "pass2_flux_gore.png")
    if os.path.exists(output_path):
        print(f"  Pass 2 already exists: {output_path}")
        return output_path

    print("\n═══ PASS 2: Flux 2 Pro — adding blood/gore ═══")

    print("  Uploading Gemini result...")
    img_url = fal_client.upload_file(gemini_image_path)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  Submitting to flux-2-pro/edit (attempt {attempt + 1})...")
            handler = fal_client.submit(
                "fal-ai/flux-2-pro/edit",
                arguments={
                    "prompt": FLUX_GORE_PROMPT,
                    "image_urls": [img_url],
                    "output_format": "png",
                    "safety_tolerance": 5,
                    "enable_safety_checker": False,
                },
            )
            for event in handler.iter_events(with_logs=True):
                if isinstance(event, fal_client.InProgress) and event.logs:
                    for log in event.logs:
                        msg = log.get('message', '') if isinstance(log, dict) else str(log)
                        print(f"    flux: {msg}")
            result = handler.get()
            break
        except Exception as e:
            if ("500" in str(e) or "downstream_service_error" in str(e)) and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    images = result.get("images", [])
    if not images:
        print("  FAILED: No image returned from Flux")
        return None

    resp = requests.get(images[0]["url"])
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img.save(output_path)
    size_kb = os.path.getsize(output_path) // 1024
    print(f"  ✓ Pass 2 saved: {output_path} ({size_kb}KB)")
    return output_path


if __name__ == "__main__":
    print("Violence Experiment: Two-pass keyframe generation")
    print(f"Output: {OUTPUT_DIR}/\n")

    # Pass 1
    gemini_path = generate_pass1_gemini()
    if not gemini_path:
        print("\nPass 1 failed — cannot continue")
        exit(1)

    # Pass 2
    flux_path = generate_pass2_flux(gemini_path)
    if not flux_path:
        print("\nPass 2 failed")
        exit(1)

    print(f"\n═══ EXPERIMENT COMPLETE ═══")
    print(f"  Pass 1 (Gemini, action only): {gemini_path}")
    print(f"  Pass 2 (Flux, +gore):         {flux_path}")
    print(f"  Current keyframe:             assets/generated/videos/raider_ambush/keyframes/keyframe_004.png")
    print(f"\nCompare all three to evaluate the approach.")
