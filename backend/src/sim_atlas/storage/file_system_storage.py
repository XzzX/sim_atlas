from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from sim_atlas.models import ExecutionResultMetadata, NodeMetadata
from sim_atlas.storage.storage_interface import (
    ExecutionResultAlreadyExistsError,
    ExecutionResultDuplicateError,
    NodeAlreadyExistsError,
    NodeDuplicateError,
    StorageInterface,
)

logger = logging.getLogger(__name__)


def _deserialize_node(data: dict[str, object]) -> NodeMetadata:
    node = NodeMetadata.model_validate(data)
    # Files written by older versions may still carry derived references;
    # stored nodes must not, so drop them rather than trusting stale values.
    return node.model_copy(
        update={
            "used_by": None,
            "inputs": [a.model_copy(update={"connections": None}) for a in node.inputs],
            "outputs": [
                a.model_copy(update={"connections": None}) for a in node.outputs
            ],
        }
    )


def _write_json_atomically(target: Path, payload: dict[str, object]) -> None:
    """Write *payload* as JSON to *target*, replacing it atomically.

    The data goes to a sibling temp file that is flushed and fsynced before being
    renamed over the target, so an interrupted write can never truncate the
    existing file.
    """
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)


class FileSystemStorage(StorageInterface):
    """File-system-backed storage implementation for node metadata"""

    NODES_FILENAME = "artifacts.json"
    EXECUTION_RESULTS_FILENAME = "execution_results.json"

    def __init__(self, path: Path | None = None) -> None:
        self._nodes: dict[str, NodeMetadata] = {}
        self._execution_results: dict[str, ExecutionResultMetadata] = {}
        self._path = path
        self._connected = False

        if self._path is not None:
            nodes_file = self._path / self.NODES_FILENAME
            if nodes_file.exists():
                with open(nodes_file) as f:
                    data = json.load(f)
                self._nodes = {k: _deserialize_node(v) for k, v in data.items()}

            execution_results_file = self._path / self.EXECUTION_RESULTS_FILENAME
            if execution_results_file.exists():
                with open(execution_results_file) as f:
                    data = json.load(f)
                self._execution_results = {
                    k: ExecutionResultMetadata.model_validate(v)
                    for k, v in data.items()
                }

        print(f"FileSystemStorage initialized with {len(self._nodes)} items.")
        self._connected = True

    def _save_nodes_to_disk(self) -> None:
        if self._path is None:
            return
        _write_json_atomically(
            self._path / self.NODES_FILENAME,
            {k: v.model_dump() for k, v in self._nodes.items()},
        )

    def _save_execution_results_to_disk(self) -> None:
        if self._path is None:
            return
        _write_json_atomically(
            self._path / self.EXECUTION_RESULTS_FILENAME,
            {k: v.model_dump() for k, v in self._execution_results.items()},
        )

    def create_node(
        self, value: NodeMetadata, check_source_hash: bool = True
    ) -> NodeMetadata:
        id = value.id
        if id in self._nodes:
            raise NodeAlreadyExistsError(self._nodes[id])
        if check_source_hash and value.hash:
            for node in self._nodes.values():
                if node.hash == value.hash:
                    raise NodeDuplicateError(node)
        self._nodes[id] = value
        self._save_nodes_to_disk()
        return value

    def read_node(self, id: str) -> NodeMetadata:
        if id not in self._nodes:
            raise KeyError(id)
        return self._nodes[id]

    def update_node(self, id: str, value: NodeMetadata) -> NodeMetadata:
        if id not in self._nodes:
            raise KeyError(id)
        self._nodes[id] = value
        self._save_nodes_to_disk()
        return value

    def delete_node(self, id: str) -> None:
        if id not in self._nodes:
            raise KeyError(id)
        del self._nodes[id]
        self._save_nodes_to_disk()

    def exists(self, id: str) -> bool:
        return id in self._nodes

    def count(self) -> int:
        return len(self._nodes)

    def nodes(self) -> list[NodeMetadata]:
        return list(self._nodes.values())

    def update_nodes(self, values: list[NodeMetadata]) -> None:
        missing = [value.id for value in values if value.id not in self._nodes]
        if missing:
            raise KeyError(missing[0])
        for value in values:
            self._nodes[value.id] = value
        self._save_nodes_to_disk()

    def create_execution_result(
        self, value: ExecutionResultMetadata, check_hash: bool = True
    ) -> ExecutionResultMetadata:
        id = value.id
        if id in self._execution_results:
            raise ExecutionResultAlreadyExistsError(value)
        if check_hash and value.hash:
            for result in self._execution_results.values():
                if result.hash == value.hash:
                    raise ExecutionResultDuplicateError(value)
        self._execution_results[id] = value
        self._save_execution_results_to_disk()
        return value

    def read_execution_result(self, id: str) -> ExecutionResultMetadata:
        if id not in self._execution_results:
            raise KeyError(id)
        return self._execution_results[id]

    def update_execution_result(
        self, id: str, value: ExecutionResultMetadata
    ) -> ExecutionResultMetadata:
        if id not in self._execution_results:
            raise KeyError(id)
        self._execution_results[id] = value
        self._save_execution_results_to_disk()
        return value

    def delete_execution_result(self, id: str) -> None:
        if id not in self._execution_results:
            raise KeyError(id)
        del self._execution_results[id]
        self._save_execution_results_to_disk()

    def read_execution_results_by_node(
        self, node_id: str
    ) -> list[ExecutionResultMetadata]:
        return [r for r in self._execution_results.values() if r.artifact_id == node_id]
