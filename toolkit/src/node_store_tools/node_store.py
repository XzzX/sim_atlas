import importlib
import importlib.metadata
import inspect
from http import HTTPStatus
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Literal

import requests
from python_workflow_definition.models import (
    PythonWorkflowDefinitionWorkflow,
)

from .models import (
    Filter,
    NodeRequest,
    NodeResponse,
    NodeType,
    ScoredSearchResponse,
)
from .parser import get_metadata
import contextlib


class NodeStore:
    def __init__(self, api_url: str, author: str, email: str) -> None:
        self.api_url = api_url
        self.author = author
        self.email = email

    def upload_module(  # noqa: PLR0912
        self,
        module: str | ModuleType,
        recursive: Literal["no", "import", "filesystem"] = "no",
    ) -> None:
        print(f"Uploading module {module}...")
        try:
            if isinstance(module, str):
                module = importlib.import_module(module)
        except Exception as e:
            print(f"✗ Failed to import module {module}: {e}")
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
                self.upload_module(submodule_path)

        if hasattr(module, "__all__"):
            items = ((k, module.__dict__[k]) for k in module.__all__)
        else:
            items = module.__dict__.items()

        for k, v in items:
            if inspect.ismodule(v):
                if recursive == "import" and v.__name__.startswith(module.__name__):
                    self.upload_module(v, recursive=recursive)
                continue

            if not hasattr(v, "__module__"):
                continue

            if not v.__module__.startswith(module.__name__):
                continue

            if k.startswith("_"):
                continue

            try:
                self.upload(v)
            except Exception as e:
                print(f"✗ {k}: {v}\n{e}")
                continue

    def upload(self, obj: Any, **kwargs: dict[str, Any]) -> requests.Response:
        """Upload node metadata to the specified API endpoint.

        Args:
            node (Node): The node metadata to upload.
        """

        if isinstance(obj, NodeRequest):
            response = requests.post(
                f"{self.api_url}/nodes/",
                json=obj.model_dump(),
            )
            return response

        if inspect.ismodule(obj):
            raise ValueError(
                "Will not automatically upload modules. Use upload_module instead."
            )

        general_metadata: dict[str, Any] = {
            "author_name": self.author,
            "author_email": self.email,
        }

        with contextlib.suppress(Exception):
            dependencies = importlib.metadata.requires(obj.__module__.partition(".")[0])
            if dependencies is not None:
                general_metadata["dependencies"] = dependencies

        with contextlib.suppress(Exception):
            project_url = importlib.metadata.metadata(
                obj.__module__.partition(".")[0]
            ).json.get("project_url")
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

        metadata = get_metadata(obj)
        metadata_dict = metadata.model_dump()
        metadata_dict.update(general_metadata)
        metadata_dict.update(kwargs)
        if v := metadata_dict.get("python_import"):
            metadata_dict["name"] = v

        request_data = NodeRequest.model_validate(metadata_dict)

        response = requests.post(
            f"{self.api_url}/nodes",
            json=request_data.model_dump(),
        )
        return response

    def get_function(self, node_id: str) -> NodeResponse:
        """Retrieve node metadata from the specified API endpoint.

        Args:
            node_id (str): The ID of the node to retrieve.
        Returns:
            dict: The node metadata.
        """
        response = requests.get(f"{self.api_url}/nodes/{node_id}/")
        return NodeResponse.model_validate(response.json())

    def download_python_workflow_definition(
        self, node_id: str, filename: Path | str
    ) -> PythonWorkflowDefinitionWorkflow:
        response = requests.get(f"{self.api_url}/nodes/{node_id}/")
        if response.status_code != HTTPStatus.OK:
            raise ValueError(f"Node with ID {node_id} not found.")
        metadata = NodeResponse.model_validate(response.json())
        if metadata.node_type != NodeType.PYTHON_WORKFLOW_DEFINITION:
            raise ValueError(
                f"Node with ID {node_id} is not a PythonWorkflowDefinition."
            )
        workflow = PythonWorkflowDefinitionWorkflow.model_validate_json(
            metadata.source_code
        )
        with open(filename, "w") as f:
            f.write(metadata.source_code)
        return workflow

    def get_function_index(self) -> SimpleNamespace:
        response = requests.get(f"{self.api_url}/node-index/")

        ns = SimpleNamespace()
        for f in response.json():
            key_list = f"{f['module']}.{f['qualname']}".split(".")
            current = ns
            for key in key_list:
                if not hasattr(current, key):
                    setattr(current, key, SimpleNamespace())
                current = getattr(current, key)
            current = f"{f['module']}.{f['qualname']}"
        return ns

    def search_function(self, query: str) -> list[NodeResponse]:
        """Search for nodes matching the query using semantic search.

        Args:
            query (str): The search query string.
        Returns:
            list: A list of node metadata matching the query.
        """
        response = requests.post(
            f"{self.api_url}/nodes/search",
            params={"query": query},
        )
        return response.json()

    def semantic_search_function(self, query: str) -> list[ScoredSearchResponse]:
        """Search for nodes matching the query using semantic search.

        Args:
            query (str): The search query string.
        Returns:
            list: A list of node metadata matching the query.
        """
        response = requests.post(
            f"{self.api_url}/nodes/semantic_search",
            params={"query": query},
        )
        return response.json()

    def filter(self, filter_params: Filter | None = None) -> list[NodeResponse]:
        """Filter nodes based on provided criteria.

        Args:
            filter_params (dict): A dictionary of filter criteria.
        Returns:
            list: A list of node metadata matching the filter criteria.
        """
        response = requests.get(
            f"{self.api_url}/nodes",
        )
        return response.json()
