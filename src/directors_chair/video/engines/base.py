from abc import ABC, abstractmethod
from typing import Optional


class BaseVideoEngine(ABC):
    @abstractmethod
    def generate_clip(self,
                      prompt: str,
                      start_image_path: str,
                      end_image_path: str,
                      output_path: str,
                      resolution: str = "480p",
                      num_frames: int = 81,
                      fps: int = 16,
                      num_inference_steps: int = 30,
                      guide_scale: float = 5.0,
                      seed: Optional[int] = None,
                      negative_prompt: Optional[str] = None) -> bool:
        pass
