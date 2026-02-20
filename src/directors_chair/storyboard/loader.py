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

    for shot in storyboard.get("shots", []):
        # Layout prompt (Blender layout description)
        if "layout_prompt_file" in shot:
            shot["layout_prompt"] = _resolve_file_ref(base_dir, shot["layout_prompt_file"])
        # Keyframe prompt (Kling i2i) — single prompt for <= 2 characters
        if "keyframe_prompt_file" in shot:
            shot["keyframe_prompt"] = _resolve_file_ref(base_dir, shot["keyframe_prompt_file"])
        # Optional keyframe edit prompt (post-generation touch-up)
        if "keyframe_edit_prompt_file" in shot:
            shot["keyframe_edit_prompt"] = _resolve_file_ref(base_dir, shot["keyframe_edit_prompt_file"])
        # Keyframe passes (multi-pass for > 2 characters)
        if "keyframe_passes" in shot:
            for kp in shot["keyframe_passes"]:
                if "prompt_file" in kp:
                    kp["prompt"] = _resolve_file_ref(base_dir, kp["prompt_file"])
        # Beats (Kling i2v multi-prompt)
        if "beats" in shot:
            for beat in shot["beats"]:
                if "prompt_file" in beat:
                    beat["prompt"] = _resolve_file_ref(base_dir, beat["prompt_file"])

    return storyboard


VALID_BODY_TYPES = {"large", "regular_male", "regular_female"}
VALID_DURATIONS = {"3", "4", "5", "6", "7", "8", "9", "10"}
VALID_KEYFRAME_ENGINES = {"kling", "gemini"}


def validate_storyboard(storyboard: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    if "name" not in storyboard:
        errors.append("Missing required field: 'name'")
    if "shots" not in storyboard:
        errors.append("Missing required field: 'shots'")
    elif not isinstance(storyboard["shots"], list) or len(storyboard["shots"]) < 1:
        errors.append("'shots' must be a list with at least 1 entry")

    # Keyframe engine (optional, defaults to kling)
    kf_engine = storyboard.get("keyframe_engine", "gemini")
    if kf_engine not in VALID_KEYFRAME_ENGINES:
        errors.append(f"'keyframe_engine' must be one of {VALID_KEYFRAME_ENGINES}, got '{kf_engine}'")

    # Characters are required
    characters = storyboard.get("characters", {})
    if not characters:
        errors.append("Missing required field: 'characters' (dict of character definitions)")
    else:
        for char_name, char_def in characters.items():
            if "reference_image" not in char_def:
                errors.append(f"Character '{char_name}': missing 'reference_image'")
            elif not os.path.exists(char_def["reference_image"]):
                errors.append(f"Character '{char_name}': reference_image not found: {char_def['reference_image']}")
            if "body_type" in char_def and char_def["body_type"] not in VALID_BODY_TYPES:
                errors.append(f"Character '{char_name}': body_type must be one of {VALID_BODY_TYPES}")

    # Validate shots
    if "shots" in storyboard and isinstance(storyboard["shots"], list):
        for i, shot in enumerate(storyboard["shots"]):
            # Layout prompt required for Blender layout generation
            if "layout_prompt" not in shot:
                errors.append(f"Shot {i + 1}: missing 'layout_prompt' (or 'layout_prompt_file')")
            # Keyframe: either single prompt or multi-pass
            has_keyframe = "keyframe_prompt" in shot
            has_passes = "keyframe_passes" in shot
            if not has_keyframe and not has_passes:
                errors.append(f"Shot {i + 1}: missing 'keyframe_prompt' or 'keyframe_passes'")
            if has_passes:
                passes = shot["keyframe_passes"]
                if not isinstance(passes, list) or len(passes) < 2:
                    errors.append(f"Shot {i + 1}: 'keyframe_passes' must have at least 2 entries")
                else:
                    for pi, kp in enumerate(passes):
                        if "prompt" not in kp:
                            errors.append(f"Shot {i + 1}, pass {pi + 1}: missing 'prompt' (or 'prompt_file')")
                        if "characters" not in kp or not isinstance(kp.get("characters"), list):
                            errors.append(f"Shot {i + 1}, pass {pi + 1}: missing 'characters' list")
            # Anchor keyframe (optional — must reference an earlier shot)
            if "anchor_keyframe" in shot:
                anchor = shot["anchor_keyframe"]
                if not isinstance(anchor, int) or anchor < 0:
                    errors.append(f"Shot {i + 1}: 'anchor_keyframe' must be a non-negative integer")
                elif anchor >= i:
                    errors.append(f"Shot {i + 1}: 'anchor_keyframe' ({anchor}) must reference an earlier shot (< {i})")

            # Beats required for Kling i2v
            if "beats" not in shot:
                errors.append(f"Shot {i + 1}: missing 'beats' (multi-prompt narrative beats)")
            elif not isinstance(shot["beats"], list) or len(shot["beats"]) < 1:
                errors.append(f"Shot {i + 1}: 'beats' must be a non-empty list")
            else:
                for j, beat in enumerate(shot["beats"]):
                    if "prompt" not in beat:
                        errors.append(f"Shot {i + 1}, beat {j + 1}: missing 'prompt' (or 'prompt_file')")
                    if "duration" not in beat:
                        errors.append(f"Shot {i + 1}, beat {j + 1}: missing 'duration'")
                    elif str(beat["duration"]) not in VALID_DURATIONS:
                        errors.append(f"Shot {i + 1}, beat {j + 1}: duration must be one of {VALID_DURATIONS}")

    return (len(errors) == 0, errors)
