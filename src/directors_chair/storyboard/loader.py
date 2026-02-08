import json
import os
from typing import Dict, Any, List, Tuple


def _resolve_file_ref(base_dir: str, value: str) -> str:
    """Read a .txt file relative to the storyboard directory."""
    file_path = os.path.join(base_dir, value)
    with open(file_path, "r") as f:
        return f.read().strip()


def load_storyboard(path: str) -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.abspath(path))

    with open(path, "r") as f:
        storyboard = json.load(f)

    # Resolve file references in shots
    for shot in storyboard.get("shots", []):
        if "image_prompt_file" in shot:
            shot["image_prompt"] = _resolve_file_ref(base_dir, shot["image_prompt_file"])
        if "motion_file" in shot:
            shot["motion"] = _resolve_file_ref(base_dir, shot["motion_file"])

    return storyboard


def validate_storyboard(storyboard: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    if "name" not in storyboard:
        errors.append("Missing required field: 'name'")
    if "shots" not in storyboard:
        errors.append("Missing required field: 'shots'")
    elif not isinstance(storyboard["shots"], list) or len(storyboard["shots"]) < 1:
        errors.append("'shots' must be a list with at least 1 entry")

    if "shots" in storyboard and isinstance(storyboard["shots"], list):
        for i, shot in enumerate(storyboard["shots"]):
            if i == 0 and "image_prompt" not in shot:
                errors.append(f"Shot 1: missing 'image_prompt' (or 'image_prompt_file') — first shot must have a scene prompt")
            if "motion" not in shot:
                errors.append(f"Shot {i + 1}: missing 'motion' (or 'motion_file')")

    if "loras" in storyboard:
        for i, lora in enumerate(storyboard["loras"]):
            if "path" not in lora:
                errors.append(f"LoRA {i + 1}: missing 'path'")
            elif not os.path.exists(lora["path"]):
                errors.append(f"LoRA {i + 1}: file not found at '{lora['path']}'")

    if "video_loras" in storyboard:
        for i, lora in enumerate(storyboard["video_loras"]):
            if "path" not in lora:
                errors.append(f"video_loras[{i}]: missing 'path' (URL to LoRA weights)")
            if "scale" in lora:
                s = lora["scale"]
                if not isinstance(s, (int, float)) or s < 0 or s > 4:
                    errors.append(f"video_loras[{i}]: scale must be 0.0-4.0")

    if "video_params" in storyboard:
        vp = storyboard["video_params"]
        if "resolution" in vp and vp["resolution"] not in ("480p", "720p"):
            errors.append("video_params.resolution must be '480p' or '720p'")
        if "num_frames" in vp:
            nf = vp["num_frames"]
            if not isinstance(nf, int) or nf < 81 or nf > 100:
                errors.append("video_params.num_frames must be integer 81-100")
        if "fps" in vp:
            fps = vp["fps"]
            if not isinstance(fps, (int, float)) or fps < 5 or fps > 24:
                errors.append("video_params.fps must be 5-24")

    return (len(errors) == 0, errors)
