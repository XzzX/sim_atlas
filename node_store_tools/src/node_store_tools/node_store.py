import hashlib
import importlib
import inspect
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import requests
from node_store_spec.models import NodeRequest, NodeResponse, NodeType, PythonImport
from python_workflow_definition.models import (
    PythonWorkflowDefinitionInputNode,
    PythonWorkflowDefinitionOutputNode,
    PythonWorkflowDefinitionWorkflow,
)

from node_store_tools.DotDict import DotDict

from .parser import get_function_metadata


class NodeStore:
    def __init__(self, api_url: str, author: str, email: str) -> None:
        self.api_url = api_url
        self.author = author
        self.email = email

    def upload_module(self, module: str | ModuleType) -> None:
        """Upload all functions and classes from a module to the specified API endpoint.

        Args:
            module (str | ModuleType): The module name or module object to upload.
            email (str): The email of the author.
            module (str | ModuleType): The module name or module object to upload.
        """
        if isinstance(module, str):
            module = importlib.import_module(module)

        for k, v in module.__dict__.items():
            if k.startswith("_"):
                continue

            if inspect.isfunction(v):
                response = self.upload_function(v)
                if response.status_code == 200:
                    print(f"✓ Stored function: {response.json()}")
                else:
                    print(f"✗ Failed function: {response.json()}")

            if isinstance(v, PythonWorkflowDefinitionWorkflow):
                response = self.upload_python_workflow_definition(v)
                if response.status_code == 200:
                    print(f"✓ Stored PWD: {response.json()}")
                else:
                    print(f"✗ Failed PWD: {response.json()}")

    def upload_function(self, func: Callable) -> requests.Response:
        """Upload node metadata to the specified API endpoint.

        Args:
            node (Node): The node metadata to upload.
        """

        from importlib.metadata import requires, version

        if inspect.isfunction(func) or inspect.ismethod(func):
            node_type = NodeType.FUNCTION
            source_code = inspect.getsource(func)
            source_code = textwrap.dedent(source_code.replace("\\r\\n", ""))
            source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()
        else:
            raise ValueError("Provided node is neither a function nor a class")

        metadata = get_function_metadata(func)

        request_data = NodeRequest(
            python_import=PythonImport(
                module=func.__module__,
                version=version(func.__module__.partition(".")[0]),
                qualname=func.__qualname__,
            ),
            author=self.author,
            email=self.email,
            **metadata.model_dump(),
            source_code=source_code,
            source_code_hash=source_code_hash,
            node_type=node_type,
            dependencies=requires(func.__module__.partition(".")[0]),
        )

        response = requests.post(
            f"{self.api_url}/nodes/",
            json=request_data.model_dump(),
        )
        return response

    def upload_python_workflow_definition(
        self, workflow: PythonWorkflowDefinitionWorkflow
    ) -> requests.Response:
        source_code = workflow.dump_json()
        source_code_hash = hashlib.sha256(source_code.encode()).hexdigest()

        arguments = {}
        returns_unpacked = {}
        for node in workflow.nodes:
            if isinstance(node, PythonWorkflowDefinitionInputNode):
                arguments[node.name] = None
            if isinstance(node, PythonWorkflowDefinitionOutputNode):
                returns_unpacked[node.name] = None

        request_data = NodeRequest(
            author=self.author,
            email=self.email,
            source_code=source_code,
            source_code_hash=source_code_hash,
            arguments=arguments,
            returns_unpacked=returns_unpacked,
            node_type=NodeType.PYTHON_WORKFLOW_DEFINITION,
        )

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
