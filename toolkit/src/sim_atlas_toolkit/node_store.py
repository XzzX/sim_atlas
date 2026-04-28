import contextlib
import importlib
import importlib.metadata
import inspect
import logging
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import requests

from sim_atlas_toolkit.parsers.metadata import Metadata

from .config import load_config
from .models import (
    NodeRequest,
)
from .parser import get_metadata

logger = logging.getLogger("SimAtlas")


class NodeStore:
    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        cfg = load_config()
        self.api_url = api_url if api_url is not None else cfg.api_url
        self.api_key = api_key if api_key is not None else cfg.api_key or None

    def upload_module(  # noqa: PLR0912
        self,
        module: str | ModuleType,
        update_existing: bool = False,
        parsers: list[Callable[[Any], Metadata | None]] | None = None,
        recursive: Literal["no", "import", "filesystem"] = "no",
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
                module.__name__
                + "."
                + ".".join(
                    str(path.relative_to(module_path).with_suffix("")).split("/")
                )
                for path in submodule_paths
            )
            for submodule_path in submodule_paths:
                self.upload_module(
                    submodule_path,
                    update_existing=update_existing,
                    parsers=parsers,
                    recursive="no",
                    **kwargs,
                )

        if hasattr(module, "__all__"):
            items = ((k, module.__dict__[k]) for k in module.__all__)
        else:
            items = module.__dict__.items()

        num_uploads = 0
        successful_uploads = 0
        for k, v in items:
            if inspect.ismodule(v):
                if recursive == "import" and v.__name__.startswith(module.__name__):
                    self.upload_module(
                        v,
                        update_existing=update_existing,
                        parsers=parsers,
                        recursive=recursive,
                        **kwargs,
                    )
                continue

            if not hasattr(v, "__module__"):
                continue

            if not v.__module__.startswith(module.__name__):
                continue

            if k.startswith("_"):
                continue

            num_uploads += 1
            try:
                response = self.upload(
                    v, update_existing=update_existing, parsers=parsers, **kwargs
                )
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

    def upload(  # noqa: PLR0912
        self,
        obj: Any,
        update_existing: bool = False,
        parsers: list[Callable[[Any], Metadata | None]] | None = None,
        **kwargs: dict[str, Any],
    ) -> requests.Response:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        if isinstance(obj, NodeRequest):
            response = requests.post(
                f"{self.api_url}/nodes/",
                json=obj.model_dump(),
                headers=headers,
            )
            return response

        if inspect.ismodule(obj):
            raise ValueError(
                "Will not automatically upload modules. Use upload_module instead."
            )

        general_metadata: dict[str, Any] = {}

        with contextlib.suppress(Exception):
            if dependencies := importlib.metadata.requires(
                obj.__module__.partition(".")[0]
            ):
                general_metadata["dependencies"] = dependencies

        try:
            package_metadata = importlib.metadata.metadata(
                obj.__module__.partition(".")[0]
            ).json
        except Exception as _:
            package_metadata = {}

        if author := package_metadata.get("author"):
            general_metadata["author_name"] = author
        if email := package_metadata.get("author_email"):
            general_metadata["author_email"] = email

        with contextlib.suppress(Exception):
            project_url = package_metadata.get("project_url")
            if project_url is not None:
                for item in project_url:
                    key, url = item.split(", ")
                    if key.lower() in ["homepage"]:
                        general_metadata["homepage_url"] = url
                        continue
                    if key.lower() in ["documentation"]:
                        general_metadata["documentation_url"] = url
                        continue
                    if key.lower() in ["source", "code", "repository", "github"]:
                        general_metadata["source_url"] = url
                        continue

        metadata = get_metadata(obj, parsers)
        metadata_dict = metadata.model_dump()
        metadata_dict.update(general_metadata)
        if v := metadata_dict.get("python_import"):
            metadata_dict["name"] = v
        metadata_dict.update(kwargs)

        request_data = NodeRequest.model_validate(metadata_dict)

        response = requests.post(
            f"{self.api_url}/nodes",
            json=request_data.model_dump(),
            headers=headers,
        )
        return response
