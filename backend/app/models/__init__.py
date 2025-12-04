import pkgutil
from pathlib import Path
# from .game import GameModel
# from .user import User

# __all__ = ["User", "GameModel"]


def load_all_models() -> None:
    """Load all models from this folder."""
    package_dir = Path(__file__).resolve().parent
    print(package_dir)
    modules = pkgutil.walk_packages(
        path=[str(package_dir)],
        prefix="backend.app.models.",
    )
    for module in modules:
        print(module)
        __import__(module.name)
