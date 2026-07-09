import importlib
import inspect
import logging
import operator as op
from collections.abc import Callable, Generator
from functools import reduce
from http import HTTPStatus
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import requests

from sim_atlas_toolkit.node_store_api import NodeStoreAPI
from sim_atlas_toolkit.upload import upload

logger = logging.getLogger(__name__)


def upload_module(  # noqa: PLR0912, PLR0913
    ns: NodeStoreAPI,
    module: str | ModuleType,
    update_existing: bool = False,
    parsers: list[Callable[..., list[requests.Response]]] | None = None,
    recursive: Literal["no", "import", "filesystem"] = "no",
    module_allowlist: list[str] | None = None,
    **kwargs: dict[str, Any],
) -> None:
    try:
        if isinstance(module, str):
            module = importlib.import_module(module)
    except Exception as e:
        logger.error(f"Failed to import module {module}: {e}")
        return

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
        for submodule_path in submodule_paths:
            upload_module(
                ns,
                submodule_path,
                update_existing=update_existing,
                parsers=parsers,
                recursive="no",
                module_allowlist=module_allowlist,
                **kwargs,
            )

    if hasattr(module, "__all__"):
        items = ((k, getattr(module, k)) for k in module.__all__)
    else:
        items = module.__dict__.items()

    num_uploads = 0
    successful_uploads = 0
    for k, v in items:
        if inspect.ismodule(v):
            if recursive == "import" and v.__name__.startswith(module.__name__):
                upload_module(
                    ns,
                    v,
                    update_existing=update_existing,
                    parsers=parsers,
                    recursive=recursive,
                    module_allowlist=module_allowlist,
                    **kwargs,
                )
            continue

        if k.startswith("_"):
            continue

        if not hasattr(v, "__module__"):
            continue

        logger.debug(f"Checking {k} (module: {v.__module__})")

        if not v.__module__.startswith(module.__name__) and not any(
            v.__module__.startswith(prefix) for prefix in (module_allowlist or [])
        ):
            continue

        try:
            responses = upload(
                ns, v, update_existing=update_existing, parsers=parsers, **kwargs
            )
            num_uploads += len(responses)
            for response in responses:
                if response.status_code == HTTPStatus.CREATED:
                    successful_uploads += 1
                else:
                    logger.debug(
                        f"Failed to upload {k}: {response.status_code} {response.text}"
                    )
        except Exception as e:
            logger.debug(f"Failed to upload {k}: {v}\n{e}")
            continue

    logger.info(f"{successful_uploads}/{num_uploads} uploaded from {module}")


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
        return collected_objects

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
