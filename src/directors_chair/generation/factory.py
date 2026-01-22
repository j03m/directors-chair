from typing import Dict, Optional
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
        
        # Instantiate based on token
        generator: Optional[BaseGenerator] = None
        
        if "z-image" in token or "zimage-turbo" in token or "flux" in token:
            generator = ZImageTurboGenerator()
        else:
            # Fallback or default
            generator = ZImageTurboGenerator()
            
        cls._instances[token] = generator
        return generator

def get_generator(token: str) -> BaseGenerator:
    return GeneratorFactory.get_generator(token)
