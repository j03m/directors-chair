from abc import ABC, abstractmethod
from mflux.models.z_image import ZImageTurbo
from mflux.models.common.resolution.path_resolution import PathResolution
from mflux.models.z_image.weights.z_image_weight_definition import ZImageWeightDefinition
from mflux.models.common.config.model_config import ModelConfig

class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, steps: int, seed: int):
        pass

class ZImageTurboGenerator(BaseGenerator):
    def __init__(self):
        # Resolve the model path to a local path to prevent repeated downloads/checks
        # by TokenizerLoader which happens if we pass a repo ID directly.
        model_name = ModelConfig.z_image_turbo().model_name
        resolved_path = PathResolution.resolve(
            path=model_name,
            patterns=ZImageWeightDefinition.get_download_patterns()
        )
        
        # Pass the resolved local path as string
        model_path = str(resolved_path) if resolved_path else None
        
        self.model = ZImageTurbo(
            quantize=8,
            model_path=model_path
        )

    def generate(self, prompt: str, steps: int, seed: int):
        # returns the image
        return self.model.generate_image(prompt=prompt, num_inference_steps=steps, seed=seed)