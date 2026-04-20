from .health import router as health_router
from .data import router as data_router
from .analysis import router as analysis_router
from .municipalities import router as municipalities_router
from .trends import router as trends_router

__all__ = [
    "health_router",
    "data_router", 
    "analysis_router",
    "municipalities_router",
    "trends_router"
]