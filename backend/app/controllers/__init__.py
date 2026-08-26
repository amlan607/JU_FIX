"""HTTP controllers (FastAPI routers) for the JU_FIX monolith.

Each module in this package exposes a module level ``router`` object. The
application factory discovers and mounts them automatically, so a developer can
add a feature by adding one controller file without editing a shared registry.
"""

from importlib import import_module
from pathlib import Path

from fastapi import APIRouter

_PACKAGE_DIR = Path(__file__).resolve().parent


def collect_routers() -> list[APIRouter]:
    """Import every controller module and collect its ``router``.

    Returns:
        list[APIRouter]: Every router found, in a stable alphabetical order.
    """
    routers: list[APIRouter] = []
    for path in sorted(_PACKAGE_DIR.glob("*_controller.py")):
        module = import_module(f"{__name__}.{path.stem}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            routers.append(router)
    return routers
