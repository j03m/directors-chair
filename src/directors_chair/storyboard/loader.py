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
        # Multi-character: resolve keyframe_passes prompt files
        if "keyframe_passes" in shot:
            for kp in shot["keyframe_passes"]:
                if "prompt_file" in kp:
                    kp["prompt"] = _resolve_file_ref(base_dir, kp["prompt_file"])

    return storyboard


def validate_storyboard(storyboard: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    if "name" not in storyboard:
        errors.append("Missing required field: 'name'")
    if "shots" not in storyboard:
        errors.append("Missing required field: 'shots'")
    elif not isinstance(storyboard["shots"], list) or len(storyboard["shots"]) < 1:
        errors.append("'shots' must be a list with at least 1 entry")

    characters = storyboard.get("characters", {})
    is_multichar = len(characters) > 0

    if is_multichar:
        for char_name, char_def in characters.items():
            if "reference_image" not in char_def:
                errors.append(f"Character '{char_name}': missing 'reference_image'")
            elif not os.path.exists(char_def["reference_image"]):
                errors.append(f"Character '{char_name}': reference_image not found: {char_def['reference_image']}")

    if "shots" in storyboard and isinstance(storyboard["shots"], list):
        for i, shot in enumerate(storyboard["shots"]):
            if is_multichar:
                if "image_prompt" not in shot and "keyframe_passes" not in shot:
                    errors.append(f"Shot {i + 1}: needs 'image_prompt' (composite) or 'keyframe_passes' (multi-pass)")
                elif "keyframe_passes" in shot:
                    passes = shot["keyframe_passes"]
                    if not isinstance(passes, list) or len(passes) < 1:
                        errors.append(f"Shot {i + 1}: 'keyframe_passes' must be a non-empty list")
                    else:
                        for j, kp in enumerate(passes):
                            if "character" not in kp:
                                errors.append(f"Shot {i + 1}, pass {j + 1}: missing 'character'")
                            elif kp["character"] not in characters:
                                errors.append(f"Shot {i + 1}, pass {j + 1}: character '{kp['character']}' not in 'characters'")
                            if "prompt" not in kp:
                                errors.append(f"Shot {i + 1}, pass {j + 1}: missing 'prompt' (or 'prompt_file')")
            else:
                if i == 0 and "image_prompt" not in shot:
                    errors.append(f"Shot 1: missing 'image_prompt' (or 'image_prompt_file') — first shot must have a scene prompt")
            if "motion" not in shot:
                errors.append(f"Shot {i + 1}: missing 'motion' (or 'motion_file')")
            if "video_params" in shot:
                svp = shot["video_params"]
                if "num_frames" in svp:
                    nf = svp["num_frames"]
                    if not isinstance(nf, int) or nf < 81 or nf > 129:
                        errors.append(f"Shot {i + 1}: video_params.num_frames must be integer 17-129")
                if "resolution" in svp and svp["resolution"] not in ("480p", "720p"):
                    errors.append(f"Shot {i + 1}: video_params.resolution must be '480p' or '720p'")
                if "fps" in svp:
                    sfps = svp["fps"]
                    if not isinstance(sfps, (int, float)) or sfps < 5 or sfps > 24:
                        errors.append(f"Shot {i + 1}: video_params.fps must be 5-24")

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
            if not isinstance(nf, int) or nf < 81 or nf > 129:
                errors.append("video_params.num_frames must be integer 17-129")
        if "fps" in vp:
            fps = vp["fps"]
            if not isinstance(fps, (int, float)) or fps < 5 or fps > 24:
                errors.append("video_params.fps must be 5-24")

    return (len(errors) == 0, errors)
