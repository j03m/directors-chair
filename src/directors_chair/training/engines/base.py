from abc import ABC, abstractmethod
from typing import Optional

class BaseTrainingEngine(ABC):
    @abstractmethod
    def train(self,
              dataset_path: str,
              output_name: str,
              trigger_word: str,
              steps: int,
              rank: int = 16,
              model_id: str = "",
              base_model_type: str = "",
              learning_rate: float = 0.0002,
              auto_scale_input: bool = True) -> bool:
        """
        Executes the training process.

        Args:
            dataset_path: Path to directory containing images and .txt captions.
            output_name: Name of the resulting LoRA (e.g., "viking_gorilla").
            trigger_word: The unique token to learn.
            steps: Number of training steps.
            rank: LoRA rank (mflux only).
            model_id: Hugging Face Repo ID (mflux only).
            base_model_type: mflux base model type (mflux only).
            learning_rate: Learning rate (fal-wan only).
            auto_scale_input: Auto-scale videos to 81 frames (fal-wan only).

        Returns:
            True if successful, False otherwise.
        """
        pass
