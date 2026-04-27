from .health import router as health_router
from .data import router as data_router
from .trends import router as trends_router
from .reports import router as reports_router
from .demographic import router as demographic_router
from .forecast import router as forecast_router

__all__ = [
    "health_router",
    "data_router", 
    "trends_router",
    "reports_router",
    "demographic_router",
    "forecast_router"
]
