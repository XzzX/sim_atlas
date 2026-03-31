from __future__ import annotations

import json
import os
from functools import reduce
from math import ceil

import numpy as np
from pydantic import BaseModel

from sim_atlas_backend.models import (
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeResponse,
    NodeType,
    ScoredSearchItem,
    ScoredSearchResponse,
    SearchResults,
)
from sim_atlas_backend.voyage_ai import create_embedding

from .storage_interface import StorageInterface


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute the cosine similarity between two vectors.

    Args:
        vec1 (list[float]): The first vector.
        vec2 (list[float]): The second vector.

    Returns:
        float: The cosine similarity between the two vectors.
    """

    # Convert to numpy arrays
    array1 = np.array(vec1)
    array2 = np.array(vec2)

    # Compute cosine similarity
    dot_product = np.dot(array1, array2)
    norm1 = np.linalg.norm(array1)
    norm2 = np.linalg.norm(array2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return similarity


class NodeFilter:
    def __init__(self, filter_options: Filter) -> None:
        self.category = (
            filter_options.category.lower() if filter_options.category else None
        )
        self.type = filter_options.type if filter_options.type else None
        self.author = filter_options.author if filter_options.author else None
        self.keywords = filter_options.keywords if filter_options.keywords else None
        self.datatypes = filter_options.datatypes if filter_options.datatypes else None
        self.units = filter_options.units if filter_options.units else None
        self.quantities = (
            filter_options.quantities if filter_options.quantities else None
        )

    def __call__(self, node: NodeMetadata) -> bool:  # noqa: PLR0911
        if self.category and not node.category.startswith(self.category):
            return False

        if self.type and node.node_type not in self.type:
            return False

        if self.author and node.author_name not in self.author:
            return False

        if self.keywords and not any(kw in node.keywords for kw in self.keywords):
            return False

        if self.datatypes and not any(
            dt in self.datatypes
            for dt in [input.datatype for input in node.inputs]
            + [output.datatype for output in node.outputs]
        ):
            return False

        if self.units and not any(
            unit in self.units
            for unit in [input.unit for input in node.inputs]
            + [output.unit for output in node.outputs]
        ):
            return False

        if self.quantities and not any(  # noqa: SIM103
            quantity in self.quantities
            for quantity in [input.quantity for input in node.inputs]
            + [output.quantity for output in node.outputs]
        ):
            return False

        return True


class FileSystemStorage(StorageInterface):
    """File-system-backed storage implementation for node metadata"""

    def __init__(self, filename: str | None = "filesystem.json") -> None:
        self._storage: dict[str, NodeMetadata] = {}
        self._filename = filename
        self._connected = False

        if self._filename is not None and os.path.exists(self._filename):
            try:
                with open(self._filename) as f:
                    data = json.load(f)
                    self._storage = {
                        k: NodeMetadata.model_validate(v) for k, v in data.items()
                    }
            except Exception:
                pass  # If loading fails, start with empty storage

        print(f"FileSystemStorage initialized with {len(self._storage)} items.")
        self._connected = True

    def _save_to_disk(self) -> None:
        """Save the current storage state to disk"""

        if self._filename is not None:
            with open(self._filename, "w") as f:
                json.dump(
                    {k: v.model_dump() for k, v in self._storage.items()},
                    f,
                    indent=2,
                    default=str,
                )

    def create(self, value: NodeMetadata) -> str:
        id = value.id
        if id in self._storage:
            raise ValueError(f"Node with id '{id}' already exists.")
        self._storage[id] = value
        self._save_to_disk()
        return id

    def read(self, id: str) -> NodeMetadata:
        if id not in self._storage:
            raise KeyError(id)
        return self._storage[id]

    def update(self, id: str, value: NodeMetadata) -> NodeMetadata:
        if id not in self._storage:
            raise KeyError(id)
        self._storage[id] = value
        self._save_to_disk()
        return value

    def delete(self, id: str) -> None:
        if id not in self._storage:
            raise KeyError(id)
        del self._storage[id]
        self._save_to_disk()

    def exists(self, id: str) -> bool:
        return id in self._storage

    def count(self) -> int:
        return len(self._storage)

    def get_filter_options(self) -> FilterOptions:
        # mutable defaults are ok here...
        # https://docs.pydantic.dev/latest/concepts/fields/#mutable-default-values
        class FilterOptionsSet(BaseModel):
            category: dict[str, set[str]] = {}
            type: set[NodeType] = set()
            author: set[str] = set()
            keywords: set[str] = set()
            datatypes: set[str] = set()
            units: set[str] = set()
            quantities: set[str] = set()

        def extract_categories(category: str) -> dict[str, set[str]]:
            parts = category.split(">")
            return {">".join(parts[:i]): {v} for i, v in enumerate(parts)}

        def extract_filter_options(node: NodeMetadata) -> FilterOptionsSet:
            return FilterOptionsSet(
                category=extract_categories(node.category),
                type={node.node_type},
                author={node.author_name},
                keywords=set(node.keywords),
                datatypes={input.datatype for input in node.inputs if input.datatype}
                | {output.datatype for output in node.outputs if output.datatype},
                units={input.unit for input in node.inputs if input.unit}
                | {output.unit for output in node.outputs if output.unit},
                quantities={input.quantity for input in node.inputs if input.quantity}
                | {output.quantity for output in node.outputs if output.quantity},
            )

        def merge_category(
            accumulator: dict[str, set[str]], new_element: tuple[str, set[str]]
        ) -> dict[str, set[str]]:
            key, value = new_element
            accumulator.setdefault(key, set()).update(value)
            return accumulator

        def merge_filter_options(
            options1: FilterOptionsSet, options2: FilterOptionsSet
        ) -> FilterOptionsSet:
            merged_categories = {**options1.category}
            merged_categories = reduce(
                merge_category, options2.category.items(), merged_categories
            )

            return FilterOptionsSet(
                category=merged_categories,
                type=options1.type | options2.type,
                author=options1.author | options2.author,
                keywords=options1.keywords | options2.keywords,
                datatypes=options1.datatypes | options2.datatypes,
                units=options1.units | options2.units,
                quantities=options1.quantities | options2.quantities,
            )

        filter_options_set = reduce(
            merge_filter_options,
            (extract_filter_options(node) for node in self._storage.values()),
            FilterOptionsSet(),
        )

        return FilterOptions(
            category={k: sorted(v) for k, v in filter_options_set.category.items()},
            type=sorted(filter_options_set.type),
            author=sorted(filter_options_set.author),
            keywords=sorted(filter_options_set.keywords),
            datatypes=sorted(filter_options_set.datatypes),
            units=sorted(filter_options_set.units),
            quantities=sorted(filter_options_set.quantities),
        )

    def _paginate(
        self, items: list[ScoredSearchItem], page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        safe_page = max(page, 1)
        safe_limit = max(limit, 1)
        total_items = len(items)
        total_pages = ceil(total_items / safe_limit) if total_items else 0

        start = (safe_page - 1) * safe_limit
        end = start + safe_limit

        return ScoredSearchResponse(
            results=SearchResults(
                data=items[start:end],
                page=safe_page,
                limit=safe_limit,
                total_items=total_items,
                total_pages=total_pages,
            )
        )

    def filter(self, filter: Filter) -> list[ScoredSearchItem]:
        item_filter: NodeFilter = NodeFilter(filter)

        return [
            ScoredSearchItem(score=1.0, node=item)
            for item in self._storage.values()
            if item_filter(item)
        ]

    def search(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> ScoredSearchResponse:
        item_filter: NodeFilter = NodeFilter(filter or Filter())
        filtered_items = (item for item in self._storage.values() if item_filter(item))

        def score_item(query: str, item: NodeMetadata) -> float:
            if query in item.python_import.lower():
                return 1.0
            if query in item.docstring.lower():
                return 0.5
            return 0.0

        scored_items = (
            item
            for item in (
                ScoredSearchItem(
                    score=score_item(query.lower(), item) if query else 1.0, node=item
                )
                for item in filtered_items
            )
            if item.score > 0.0
        )

        sorted_items = sorted(scored_items, key=lambda x: x.score, reverse=True)

        return self._paginate(sorted_items, page=page, limit=limit)

    def search_semantic(
        self, query: str, filter: Filter | None = None, page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        """
        Perform semantic search on node metadata.

        Args:
            query: Natural language search query
            filter: Filter criteria to narrow results
            limit: Maximum number of results to return

        Returns:
            List of relevant node metadata, ordered by relevance
        """
        # Generate embedding for the query
        query_embedding = create_embedding(query, input_type="query")

        item_filter = NodeFilter(filter or Filter())

        # Calculate similarities
        similarities: list[ScoredSearchItem] = []
        for _node_hash, node in self._storage.items():
            if node.embedding is not None and item_filter(node):
                similarity = cosine_similarity(query_embedding, node.embedding)
                similarities.append(
                    ScoredSearchItem(
                        score=similarity[0],
                        node=NodeResponse(**node.model_dump()),
                    )
                )

        # Sort by similarity (descending) and limit results
        similarities.sort(key=lambda x: x.score, reverse=True)

        return self._paginate(similarities, page=page, limit=limit)

    def enrich(self) -> None:
        documents = [node.docstring for node in self._storage.values()]
        embeddings = create_embedding(documents, input_type="document")
        for emb, item in zip(embeddings, self._storage.values(), strict=True):
            item.embedding = emb

        self._save_to_disk()
