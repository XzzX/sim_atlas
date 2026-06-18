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

from sim_atlas_toolkit.models import (
    FunctionRequest,
    WorkflowRequest,
    artifact_request_adapter,
)
from sim_atlas_toolkit.parser import get_metadata
from sim_atlas_toolkit.parsers.metadata import Metadata

logger = logging.getLogger("SimAtlas")


class NodeStore:
    def __init__(self, api_url: str, api_key: str | None = None) -> None:
        self.api_url = api_url
        self.api_key = api_key

    def upload_module(  # noqa: PLR0912
        self,
        module: str | ModuleType,
        update_existing: bool = False,
        parsers: list[Callable[[Any], list[Metadata]]] | None = None,
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
                self.upload_module(
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
                    self.upload_module(
                        v,
                        update_existing=update_existing,
                        parsers=parsers,
                        recursive=recursive,
                        module_allowlist=module_allowlist,
                        **kwargs,
                    )
                continue

            if not hasattr(v, "__module__"):
                continue

            if not v.__module__.startswith(module.__name__) and not any(
                v.__module__.startswith(prefix) for prefix in (module_allowlist or [])
            ):
                continue

            if k.startswith("_"):
                continue

            try:
                responses = self.upload(
                    v, update_existing=update_existing, parsers=parsers, **kwargs
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

    def upload(  # noqa: PLR0912
        self,
        obj: Any,
        update_existing: bool = False,
        parsers: list[Callable[[Any], list[Metadata]]] | None = None,
        **kwargs: dict[str, Any],
    ) -> list[requests.Response]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        if isinstance(obj, (FunctionRequest, WorkflowRequest)):
            response = requests.post(
                f"{self.api_url}/artifacts",
                json=obj.model_dump(),
                headers=headers,
            )
            return [response]

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

        metadata_list = get_metadata(obj, parsers)
        responses: list[requests.Response] = []
        for metadata in metadata_list:
            metadata_dict = metadata.model_dump()
            metadata_dict.update(general_metadata)
            metadata_dict.update(kwargs)

            if metadata.children:

                for child in metadata.children:
                    responses = self.upload(child.obj, update_existing=update_existing, parsers=parsers, **kwargs)
                    if len(responses) > 1:
                        logger.warning(f"Expected at most one response for child {child.label}, got {len(responses)}")
                    response = responses[0] if responses else None
                    if response is not None and response.status_code in (HTTPStatus.CREATED, HTTPStatus.CONFLICT):
                        child_id = response.json() if isinstance(response.json(), str) else response.json().get("detail", response.json()).get("id")
                        metadata_dict.setdefault("children", []).append({"label": child.label, "id": child_id})

            request_data = artifact_request_adapter.validate_python(metadata_dict)

            responses.append(
                requests.post(
                    f"{self.api_url}/artifacts",
                    json=artifact_request_adapter.dump_python(request_data),
                    headers=headers,
                )
            )
        return responses
