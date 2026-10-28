"""Launch the canonical benefits app from the repository root."""
import importlib.util
from pathlib import Path
import sys

APP_FILE = Path(__file__).resolve().parent / "employee-benefits-qa" / "app.py"
spec = importlib.util.spec_from_file_location("_benefits_core", APP_FILE)
module = importlib.util.module_from_spec(spec)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load app module from {APP_FILE}")
sys.modules[spec.name] = module  # Flask resolves its module location through this registry.
spec.loader.exec_module(module)

app = module.app
enroll = module.enroll
configure = module.configure


def create_app(test_config=None):
    """Support the older --app app:create_app launch command using the same backend."""
    if test_config:
        app.config.update(test_config)
    return app


__all__ = ["app", "enroll", "configure", "create_app"]


if __name__ == "__main__":
    app.run(debug=True)
