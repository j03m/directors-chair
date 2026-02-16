from .engines.fal_kling_engine import FalKlingEngine

VIDEO_ENGINES = {
    "kling-o3": ("Kling O3 Image-to-Video (fal.ai)", FalKlingEngine),
}

DEFAULT_ENGINE = "kling-o3"


def get_kling_engine(kling_params=None):
    """Get a Kling video engine instance."""
    return FalKlingEngine(kling_params=kling_params)
