from abc import ABC, abstractmethod
from mflux.models.z_image import ZImageTurbo
from mflux.models.flux.variants.txt2img.flux import Flux1
from mflux.models.common.resolution.path_resolution import PathResolution
from mflux.models.z_image.weights.z_image_weight_definition import ZImageWeightDefinition
from mflux.models.common.config.model_config import ModelConfig

class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, steps: int, seed: int):
        pass

class ZImageTurboGenerator(BaseGenerator):
    def __init__(self, local_model_path: str = None, lora_paths: list[str] = None):
        if local_model_path:
             model_path = local_model_path
        else:
            model_name = ModelConfig.z_image_turbo().model_name
            resolved_path = PathResolution.resolve(
                path=model_name,
                patterns=ZImageWeightDefinition.get_download_patterns()
            )
            model_path = str(resolved_path) if resolved_path else None

        self.model = ZImageTurbo(
            quantize=8,
            model_path=model_path,
            lora_paths=lora_paths
        )

    def generate(self, prompt: str, steps: int, seed: int):
        return self.model.generate_image(prompt=prompt, num_inference_steps=steps, seed=seed)

class FluxSchnellGenerator(BaseGenerator):
    def __init__(self, local_model_path: str = None, lora_paths: list[str] = None):
        model_path = local_model_path or ModelConfig.schnell().model_name
        self.model = Flux1(
            quantize=4,
            model_path=model_path,
            lora_paths=lora_paths,
            model_config=ModelConfig.schnell(),
        )

    def generate(self, prompt: str, steps: int, seed: int):
        return self.model.generate_image(prompt=prompt, num_inference_steps=steps, seed=seed)