from typing import Optional
from .engines.base import BaseTrainingEngine
from .engines.mflux_engine import MFluxEngine

class TrainingManager:
    def __init__(self):
        # In the future, we can load this from config to support Nvidia/DGX
        self.engine: BaseTrainingEngine = MFluxEngine()

    def train_lora(self, 
                   dataset_path: str, 
                   output_name: str, 
                   trigger_word: str, 
                   model_id: str,
                   base_model_type: str,
                   steps: int = 1000, 
                   rank: int = 16) -> bool:
        
        return self.engine.train(
            dataset_path=dataset_path,
            output_name=output_name,
            trigger_word=trigger_word,
            steps=steps,
            rank=rank,
            model_id=model_id,
            base_model_type=base_model_type
        )

# Singleton helper
_manager = None
def get_training_manager():
    global _manager
    if _manager is None:
        _manager = TrainingManager()
    return _manager
