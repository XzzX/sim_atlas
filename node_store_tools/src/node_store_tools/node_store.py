import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

import requests
from node_store_spec.models import NodeRequest, NodeResponse, NodeType, PythonImport
from python_workflow_definition.models import (
    PythonWorkflowDefinitionWorkflow,
)

from node_store_tools.DotDict import DotDict

from .parser import get_metadata


class NodeStore:
    def __init__(self, api_url: str, author: str, email: str) -> None:
        self.api_url = api_url
        self.author = author
        self.email = email

    def upload_module(self, module: str | ModuleType) -> None:
        if isinstance(module, str):
            module = importlib.import_module(module)
            
        if hasattr(module, "__all__"):
            items = ((k, module.__dict__[k]) for k in module.__all__)
        else:
            items = module.__dict__.items()

        for k, v in items:
            if k.startswith("_"):
                continue

            try:
                response = self.upload(v)
            except Exception as e:
                print(f"✗ {k}: {v}\n{e}")
                continue

            if response.status_code == 200:
                print(f"✓ {k}: {v}\n{response.json()}")
            else:
                print(f"✗ {k}: {v}\n{response.json()}")

    def upload(self, obj: Any) -> requests.Response:
        """Upload node metadata to the specified API endpoint.

        Args:
            node (Node): The node metadata to upload.
        """

        from importlib.metadata import requires, version

        metadata = get_metadata(obj)

        try:
            python_import = PythonImport(
                module=obj.__module__,
                version=version(obj.__module__.partition(".")[0]),
                qualname=obj.__qualname__,
            )
        except Exception:
            python_import = None

        try:
            dependencies = requires(obj.__module__.partition(".")[0])
        except Exception:
            dependencies = None

        request_data = NodeRequest(
            python_import=python_import,
            author=self.author,
            email=self.email,
            **metadata.model_dump(),
            dependencies=dependencies,
        )

        print(request_data.model_dump())

        response = requests.post(
            f"{self.api_url}/nodes/",
            json=request_data.model_dump(),
        )
        return response

    def get_function(self, node_id: str) -> dict:
        """Retrieve node metadata from the specified API endpoint.

        Args:
            node_id (str): The ID of the node to retrieve.
        Returns:
            dict: The node metadata.
        """
        response = requests.get(f"{self.api_url}/nodes/{node_id}/")
        return response.json()

    def download_python_workflow_definition(
        self, node_id: str, filename: Path | str
    ) -> PythonWorkflowDefinitionWorkflow:
        response = requests.get(f"{self.api_url}/nodes/{node_id}/")
        if response.status_code != 200:
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

    def get_function_index(self) -> dict:
        response = requests.get(f"{self.api_url}/node-index/")
        index = DotDict({})
        for f in response.json():
            entry = index.create_path(f"{f['module']}.{f['qualname']}")
            entry.update(f)
        return index

    def search_function(self, query: str) -> list:
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

    def semantic_search_function(self, query: str) -> list:
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

    def filter(self, filter_params: dict | None = None) -> list:
        """Filter nodes based on provided criteria.

        Args:
            filter_params (dict): A dictionary of filter criteria.
        Returns:
            list: A list of node metadata matching the filter criteria.
        """
        response = requests.post(
            f"{self.api_url}/nodes/list",
            json=filter_params,
        )
        return response.json()
