from typing import Dict, Optional
import os
from directors_chair.config.loader import load_config
from .engine import BaseGenerator, ZImageTurboGenerator, FluxSchnellGenerator
from .fal_engine import FalFluxGenerator

class GeneratorFactory:
    _instances: Dict[str, BaseGenerator] = {}

    @classmethod
    def get_generator(cls, token: str, lora_paths: list[str] = None) -> BaseGenerator:
        token = token.lower()

        cache_key = token
        if lora_paths:
            cache_key = f"{token}|{str(sorted(lora_paths))}"

        if cache_key in cls._instances:
            return cls._instances[cache_key]

        config = load_config()
        generator: Optional[BaseGenerator] = None

        if token.startswith("fal-"):
            # fal.ai cloud generators
            generator = FalFluxGenerator(lora_paths=lora_paths)
        elif "schnell" in token:
            model_path = cls._resolve_local_model(token, config)
            generator = FluxSchnellGenerator(local_model_path=model_path, lora_paths=lora_paths)
        elif "z-image" in token or "zimage" in token:
            model_path = cls._resolve_local_model(token, config)
            generator = ZImageTurboGenerator(local_model_path=model_path, lora_paths=lora_paths)
        else:
            model_path = cls._resolve_local_model(token, config)
            generator = ZImageTurboGenerator(local_model_path=model_path, lora_paths=lora_paths)

        cls._instances[cache_key] = generator
        return generator

    @classmethod
    def _resolve_local_model(cls, token: str, config: dict) -> Optional[str]:
        if token in config.get("model_ids", {}):
            candidate_path = os.path.join(config["directories"]["models"], token)
            if os.path.exists(candidate_path) and len(os.listdir(candidate_path)) > 0:
                return candidate_path
        return None

def get_generator(token: str, lora_paths: list[str] = None) -> BaseGenerator:
    return GeneratorFactory.get_generator(token, lora_paths)
