from .engines.base import BaseVideoEngine
from .engines.fal_wan_engine import FalWanEngine
from .engines.fal_wan_i2v_engine import FalWanI2VEngine
from .engines.fal_wan_i2v_lora_engine import FalWanI2VLoraEngine

VIDEO_ENGINES = {
    "fal-wan-flf2v": ("Wan 2.1 First-Last-Frame (fal.ai)", FalWanEngine),
    "fal-wan-i2v": ("Wan 2.1 Image-to-Video (fal.ai)", FalWanI2VEngine),
    "fal-wan-i2v-lora": ("Wan 2.1 I2V + LoRA (fal.ai)", FalWanI2VLoraEngine),
}

DEFAULT_ENGINE = "fal-wan-i2v"


class VideoManager:
    def __init__(self, engine_name: str = DEFAULT_ENGINE, engine_kwargs: dict = None):
        if engine_name not in VIDEO_ENGINES:
            raise ValueError(f"Unknown video engine: {engine_name}. Available: {list(VIDEO_ENGINES.keys())}")
        _, engine_cls = VIDEO_ENGINES[engine_name]
        self.engine_name = engine_name
        self.engine: BaseVideoEngine = engine_cls(**(engine_kwargs or {}))

    def generate_clip(self, **kwargs) -> bool:
        return self.engine.generate_clip(**kwargs)


def get_video_manager(engine_name: str = DEFAULT_ENGINE, engine_kwargs: dict = None):
    return VideoManager(engine_name=engine_name, engine_kwargs=engine_kwargs)
