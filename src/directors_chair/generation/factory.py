from typing import Dict, Optional
import os
from directors_chair.config.loader import load_config
from .engine import BaseGenerator, ZImageTurboGenerator

class GeneratorFactory:
    _instances: Dict[str, BaseGenerator] = {}

    @classmethod
    def get_generator(cls, token: str) -> BaseGenerator:
        # Normalize token
        token = token.lower()
        
        # Check if already instantiated
        if token in cls._instances:
            return cls._instances[token]
            
        # Load config to find potential local paths
        config = load_config()
        model_path = None
        
        # Check if token matches a configured model key
        if token in config.get("model_ids", {}):
             candidate_path = os.path.join(config["directories"]["models"], token)
             if os.path.exists(candidate_path) and len(os.listdir(candidate_path)) > 0:
                 model_path = candidate_path

        # Instantiate based on token
        generator: Optional[BaseGenerator] = None
        
        if "z-image" in token or "zimage-turbo" in token or "flux" in token:
            generator = ZImageTurboGenerator(local_model_path=model_path)
        else:
            # Fallback or default
            generator = ZImageTurboGenerator(local_model_path=model_path)
            
        cls._instances[token] = generator
        return generator

def get_generator(token: str) -> BaseGenerator:
    return GeneratorFactory.get_generator(token)
