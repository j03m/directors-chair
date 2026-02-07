from .engines.base import BaseVideoEngine
from .engines.fal_wan_engine import FalWanEngine


class VideoManager:
    def __init__(self):
        self.engine: BaseVideoEngine = FalWanEngine()

    def generate_clip(self, **kwargs) -> bool:
        return self.engine.generate_clip(**kwargs)


_manager = None

def get_video_manager():
    global _manager
    if _manager is None:
        _manager = VideoManager()
    return _manager
