"""SQLAlchemy models for the single JU_FIX relational database.

Model modules are discovered automatically. Six developers work on separate
feature branches during the sprint, so a hand maintained import list in this
file would produce a merge conflict on every pull request and would break the
application whenever one feature had not been merged yet. Auto discovery keeps
each feature self contained: dropping ``app/models/<feature>.py`` into the
package is enough to register its tables.
"""

from importlib import import_module
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent


def _discover_model_modules() -> list[str]:
    """Return the module names inside ``app.models`` in a stable order.

    Returns:
        list[str]: Sorted module names, excluding private modules.
    """
    return sorted(
        path.stem
        for path in _PACKAGE_DIR.glob("*.py")
        if not path.stem.startswith("_")
    )


for _module_name in _discover_model_modules():
    import_module(f"{__name__}.{_module_name}")
