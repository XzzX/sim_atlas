import importlib
import inspect
import logging
import operator as op
from collections.abc import Generator
from functools import reduce
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

logger = logging.getLogger(__name__)


def collect_objects(
    module: str | ModuleType,
    recursive: Literal["no", "import", "filesystem"] = "no",
    module_allowlist: list[str] | None = None,
) -> list[Any]:
    try:
        if isinstance(module, str):
            module = importlib.import_module(module)
    except Exception as e:
        logger.error(f"Failed to import module {module}: {e}")
        return []

    if recursive == "filesystem":
        module_path = Path(module.__path__[0])
        submodule_paths = module_path.glob("**/*.py")
        submodule_paths = (
            path for path in submodule_paths if not path.name.startswith("_")
        )
        submodule_paths = (
            ".".join(
                [module.__name__]
                + str(path.relative_to(module_path).with_suffix("")).split("/")
            )
            for path in submodule_paths
        )
        collected_objects = reduce(
            op.concat,
            [
                collect_objects(
                    submodule_path, recursive="no", module_allowlist=module_allowlist
                )
                for submodule_path in submodule_paths
            ],
            [],
        )
        return list(collected_objects)

    def collect_from_module(module: ModuleType) -> Generator[Any, None, None]:
        for k, v in module.__dict__.items():
            if inspect.ismodule(v):
                if recursive == "import" and v.__name__.startswith(module.__name__):
                    yield from collect_from_module(v)
                continue

            if k.startswith("_"):
                continue

            if not hasattr(v, "__module__"):
                continue

            if not v.__module__.startswith(module.__name__) and not any(
                v.__module__.startswith(prefix) for prefix in (module_allowlist or [])
            ):
                continue

            yield v

    collected_objects = list(collect_from_module(module))

    return collected_objects
