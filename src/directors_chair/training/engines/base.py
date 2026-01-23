from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTrainingEngine(ABC):
    @abstractmethod
    def train(self, 
              dataset_path: str, 
              output_name: str, 
              trigger_word: str, 
              steps: int, 
              rank: int) -> bool:
        """
        Executes the training process.
        
        Args:
            dataset_path: Path to directory containing images and .txt captions.
            output_name: Name of the resulting LoRA (e.g., "viking_gorilla").
            trigger_word: The unique token to learn.
            steps: Number of training steps.
            rank: LoRA rank (size/complexity).
            
        Returns:
            True if successful, False otherwise.
        """
        pass
