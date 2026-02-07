import json
import os
from typing import Dict, Any, List, Tuple


def load_storyboard(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def validate_storyboard(storyboard: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    if "name" not in storyboard:
        errors.append("Missing required field: 'name'")
    if "shots" not in storyboard:
        errors.append("Missing required field: 'shots'")
    elif not isinstance(storyboard["shots"], list) or len(storyboard["shots"]) < 2:
        errors.append("'shots' must be a list with at least 2 entries")

    if "shots" in storyboard and isinstance(storyboard["shots"], list):
        for i, shot in enumerate(storyboard["shots"]):
            if "image_prompt" not in shot:
                errors.append(f"Shot {i + 1}: missing required field 'image_prompt'")
            if i < len(storyboard["shots"]) - 1 and "motion" not in shot:
                errors.append(f"Shot {i + 1}: missing 'motion' (required on all shots except the last)")

    if "loras" in storyboard:
        for i, lora in enumerate(storyboard["loras"]):
            if "path" not in lora:
                errors.append(f"LoRA {i + 1}: missing 'path'")
            elif not os.path.exists(lora["path"]):
                errors.append(f"LoRA {i + 1}: file not found at '{lora['path']}'")

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
