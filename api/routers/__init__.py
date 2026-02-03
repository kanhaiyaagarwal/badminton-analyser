from .auth import router as auth_router
from .analysis import router as analysis_router
from .court import router as court_router
from .results import router as results_router
from .upload import router as upload_router
from .stream import router as stream_router

__all__ = [
    "auth_router",
    "analysis_router",
    "court_router",
    "results_router",
    "upload_router",
    "stream_router"
]
