from .engines.base import BaseTrainingEngine
from .engines.mflux_engine import MFluxEngine
from .engines.fal_flux_engine import FalFluxTrainingEngine
from .engines.fal_wan_engine import FalWanTrainingEngine

TRAINING_ENGINES = {
    "mflux": ("MFlux Local (Apple Silicon)", MFluxEngine),
    "fal-flux": ("Flux LoRA (fal.ai Cloud)", FalFluxTrainingEngine),
    "fal-wan": ("WAN 2.1 LoRA (fal.ai Cloud)", FalWanTrainingEngine),
}

DEFAULT_TRAINING_ENGINE = "mflux"


class TrainingManager:
    def __init__(self, engine_name: str = DEFAULT_TRAINING_ENGINE):
        if engine_name not in TRAINING_ENGINES:
            raise ValueError(f"Unknown training engine: {engine_name}. Available: {list(TRAINING_ENGINES.keys())}")
        _, engine_cls = TRAINING_ENGINES[engine_name]
        self.engine_name = engine_name
        self.engine: BaseTrainingEngine = engine_cls()

    def train_lora(self,
                   dataset_path: str,
                   output_name: str,
                   trigger_word: str,
                   steps: int = 1000,
                   rank: int = 16,
                   model_id: str = "",
                   base_model_type: str = "",
                   learning_rate: float = 0.0002,
                   auto_scale_input: bool = True) -> bool:

        return self.engine.train(
            dataset_path=dataset_path,
            output_name=output_name,
            trigger_word=trigger_word,
            steps=steps,
            rank=rank,
            model_id=model_id,
            base_model_type=base_model_type,
            learning_rate=learning_rate,
            auto_scale_input=auto_scale_input,
        )


_manager = None

def get_training_manager(engine_name: str = DEFAULT_TRAINING_ENGINE):
    global _manager
    if _manager is None or _manager.engine_name != engine_name:
        _manager = TrainingManager(engine_name=engine_name)
    return _manager
