from .auth import router as auth_router
from .notes import router as notes_router
from .prompts import router as prompts_router
from .categories import router as categories_router

__all__ = ["auth_router", "notes_router", "prompts_router", "categories_router"]
