from abc import ABC, abstractmethod
from mflux.models.z_image import ZImageTurbo

class BaseGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, steps: int, seed: int):
        pass

class ZImageTurboGenerator(BaseGenerator):
    def __init__(self):
        self.model = ZImageTurbo(quantize=8)

    def generate(self, prompt: str, steps: int, seed: int):
        # returns the image
        return self.model.generate_image(prompt=prompt, num_inference_steps=steps, seed=seed)
