import json
import os
from typing import Dict, Any

def load_config(config_path: str = "config/config.json") -> Dict[str, Any]:
    with open(config_path, "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any], config_path: str = "config/config.json"):
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

def get_prompt(prompt_input: str) -> str:
    if prompt_input.endswith(".txt") and os.path.exists(prompt_input):
        with open(prompt_input, "r") as f:
            return f.read().strip()
    return prompt_input
