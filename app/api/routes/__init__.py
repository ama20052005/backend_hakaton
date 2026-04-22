from .health import router as health_router
from .data import router as data_router
from .analysis import router as analysis_router

# Для совместимости с main.py
health = health_router
data = data_router
analysis = analysis_router
