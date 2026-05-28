from __future__ import annotations

import asyncio
import json
import os
from functools import reduce
from math import ceil

import numpy as np
from pydantic import BaseModel
from tqdm.asyncio import tqdm as atqdm

from sim_atlas_backend.ai import create_ai_descriptions
from sim_atlas_backend.models import (
    Annotation,
    ArtifactType,
    Filter,
    FilterOptions,
    FunctionMetadata,
    FunctionResponse,
    ScoredSearchItem,
    ScoredSearchResponse,
    SearchResults,
    StoredArtifact,
    WorkflowMetadata,
    WorkflowResponse,
)
from sim_atlas_backend.voyage_ai import create_embedding

from .settings import load_settings
from .storage_interface import StorageInterface
from .type_utils import collect_datatypes, datatype_matches


def _deserialize_artifact(data: dict[str, object]) -> StoredArtifact:
    artifact_type = data.get("artifact_type")
    if artifact_type == ArtifactType.WORKFLOW:
        return WorkflowMetadata.model_validate(data)
    return FunctionMetadata.model_validate(data)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute the cosine similarity between two vectors.

    Args:
        vec1 (np.ndarray): The first vector.
        vec2 (np.ndarray): The second vector.

    Returns:
        float: The cosine similarity between the two vectors.
    """
    # Compute cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    return similarity


class NodeFilter:
    def __init__(self, filter_options: Filter) -> None:
        self.category = (
            filter_options.category.lower() if filter_options.category else None
        )
        self.type = (
            filter_options.artifact_type if filter_options.artifact_type else None
        )
        self.author = filter_options.author if filter_options.author else None
        self.keywords = filter_options.keywords if filter_options.keywords else None
        self.datatypes = filter_options.datatypes if filter_options.datatypes else None
        self.units = filter_options.units if filter_options.units else None
        self.quantities = (
            filter_options.quantities if filter_options.quantities else None
        )
        self.port_type = filter_options.port_type or "both"

    def _annotations(self, node: StoredArtifact) -> list[Annotation]:
        if self.port_type == "inputs":
            return node.inputs
        if self.port_type == "outputs":
            return node.outputs
        return node.inputs + node.outputs

    def __call__(self, node: StoredArtifact) -> bool:  # noqa: PLR0911
        if self.category and not node.category.startswith(self.category):
            return False

        if self.type and node.artifact_type not in self.type:
            return False

        if self.author and node.author_name not in self.author:
            return False

        if self.keywords and not any(kw in node.keywords for kw in self.keywords):
            return False

        annotations = self._annotations(node)

        if self.datatypes and not any(
            a.datatype is not None
            and any(datatype_matches(a.datatype, f) for f in self.datatypes)
            for a in annotations
        ):
            return False

        if self.units and not any(a.unit in self.units for a in annotations):
            return False

        if self.quantities and not any(  # noqa: SIM103
            a.quantity in self.quantities for a in annotations
        ):
            return False

        return True


class FileSystemStorage(StorageInterface):
    """File-system-backed storage implementation for node metadata"""

    def __init__(self, filename: str | None = "filesystem.json") -> None:
        self._storage: dict[str, StoredArtifact] = {}
        self._filename = filename
        self._connected = False

        if self._filename is not None and os.path.exists(self._filename):
            try:
                with open(self._filename) as f:
                    data = json.load(f)
                    self._storage = {
                        k: _deserialize_artifact(v) for k, v in data.items()
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

    def create(self, value: StoredArtifact, check_source_hash: bool = True) -> str:
        id = value.id
        if id in self._storage:
            raise ValueError(f"Node with id '{id}' already exists.")
        if check_source_hash and value.source_code_hash:
            for node in self._storage.values():
                if node.source_code_hash == value.source_code_hash:
                    raise ValueError(
                        f"Node with source_code_hash '{value.source_code_hash}' already exists."
                    )
        self._storage[id] = value
        self._save_to_disk()
        return id

    def read(self, id: str) -> StoredArtifact:
        if id not in self._storage:
            raise KeyError(id)
        return self._storage[id]

    def update(self, id: str, value: StoredArtifact) -> StoredArtifact:
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
            type: set[ArtifactType] = set()
            author: set[str] = set()
            keywords: set[str] = set()
            datatypes: set[str] = set()
            units: set[str] = set()
            quantities: set[str] = set()

        def extract_categories(category: str) -> dict[str, set[str]]:
            parts = category.split(">")
            return {">".join(parts[:i]): {v} for i, v in enumerate(parts)}

        def extract_filter_options(node: StoredArtifact) -> FilterOptionsSet:
            return FilterOptionsSet(
                category=extract_categories(node.category),
                type={node.artifact_type},
                author={node.author_name},
                keywords=set(node.keywords),
                datatypes={
                    leaf
                    for ann in (node.inputs + node.outputs)
                    if ann.datatype
                    for leaf in collect_datatypes(ann.datatype)
                },
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
            artifact_type=sorted(filter_options_set.type),
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

        def score_item(query: str, item: StoredArtifact) -> float:
            if isinstance(item, FunctionMetadata):
                search_field = item.python_import.lower()
            else:
                search_field = item.name.lower()
            if query in search_field:
                return 1.0
            if query in item.ai_summary.lower():
                return 0.8
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

    async def search_semantic(
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
        query_embedding = (await create_embedding([query], input_type="query"))[0]

        item_filter = NodeFilter(filter or Filter())

        # Calculate similarities
        similarities: list[ScoredSearchItem] = []
        for _node_hash, node in self._storage.items():
            if node.embedding is not None and item_filter(node):
                similarity = cosine_similarity(query_embedding, node.embedding)
                similarities.append(
                    ScoredSearchItem(
                        score=similarity,
                        node=FunctionResponse(**node.model_dump())
                        if isinstance(node, FunctionMetadata)
                        else WorkflowResponse(**node.model_dump()),
                    )
                )

        # Sort by similarity (descending) and limit results
        similarities.sort(key=lambda x: x.score, reverse=True)

        return self._paginate(similarities, page=page, limit=limit)

    async def search_hybrid(
        self, query: str, filter: Filter | None = None, page: int = 1, limit: int = 10
    ) -> ScoredSearchResponse:
        """Hybrid search combining semantic (cosine) and keyword ranking via RRF.

        Tokens shorter than 3 characters are dropped from keyword matching so that
        short-but-meaningful domain tokens like "fcc", "bcc", or "Al" are preserved
        while noise words like "of" or "is" are filtered out.  Unenriched nodes that
        have no embedding can still surface through the keyword rank.
        """
        min_token_len = 3
        tokens = [t for t in query.lower().split() if len(t) >= min_token_len]
        if not tokens:
            return await self.search_semantic(query, filter, page=page, limit=limit)

        item_filter = NodeFilter(filter or Filter())
        filtered_nodes = [n for n in self._storage.values() if item_filter(n)]

        # --- semantic rank (only nodes with embeddings) ---
        query_embedding = (await create_embedding([query], input_type="query"))[0]
        sem_scores: list[tuple[str, float]] = [
            (node.id, cosine_similarity(query_embedding, node.embedding))
            for node in filtered_nodes
            if node.embedding is not None
        ]
        sem_scores.sort(key=lambda x: x[1], reverse=True)
        sem_rank: dict[str, int] = {
            node_id: r + 1 for r, (node_id, _) in enumerate(sem_scores)
        }

        # --- keyword rank (all filtered nodes) ---
        hit_counts: list[tuple[str, int]] = []
        for node in filtered_nodes:
            if isinstance(node, FunctionMetadata):
                search_text = (
                    f"{node.name} {node.python_import} {node.ai_summary}".lower()
                )
            else:
                search_text = f"{node.name} {node.ai_summary}".lower()
            hits = sum(1 for tok in tokens if tok in search_text)
            if hits > 0:
                hit_counts.append((node.id, hits))
        hit_counts.sort(key=lambda x: x[1], reverse=True)
        kw_rank: dict[str, int] = {
            node_id: r + 1 for r, (node_id, _) in enumerate(hit_counts)
        }

        # --- RRF merge ---
        k = 60
        candidate_ids = set(sem_rank) | set(kw_rank)
        node_lookup: dict[str, StoredArtifact] = {n.id: n for n in filtered_nodes}
        scored: list[ScoredSearchItem] = [
            ScoredSearchItem(
                score=(1 / (k + sem_rank[nid]) if nid in sem_rank else 0.0)
                + (1 / (k + kw_rank[nid]) if nid in kw_rank else 0.0),
                node=FunctionResponse(**node_lookup[nid].model_dump())
                if isinstance(node_lookup[nid], FunctionMetadata)
                else WorkflowResponse(**node_lookup[nid].model_dump()),
            )
            for nid in candidate_ids
        ]
        scored.sort(key=lambda x: x.score, reverse=True)

        return self._paginate(scored, page=page, limit=limit)

    @staticmethod
    def _embedding_text(node: StoredArtifact) -> str:
        port_lines = [
            f"{a.label}: {a.description}"
            for a in node.inputs + node.outputs
            if a.label and a.description
        ]
        if not port_lines:
            return node.ai_description
        return node.ai_description + "\n" + "\n".join(port_lines)

    async def enrich(self, only_ids: list[str] | None = None) -> None:
        sem = asyncio.Semaphore(load_settings().llm_enrich_concurrency)
        nodes_to_enrich = (
            [node for node in self._storage.values() if node.id in only_ids]
            if only_ids
            else [node for node in self._storage.values() if node.embedding is None]
        )

        async def _enrich_one(v: StoredArtifact) -> None:
            async with sem:
                source_code = v.source_code if isinstance(v, FunctionMetadata) else None
                if not source_code:
                    return
                try:
                    output_labels = [a.label for a in v.outputs if a.label is not None]
                    v.ai_summary, v.ai_description, args = await create_ai_descriptions(
                        v.name, v.docstring, source_code, output_labels
                    )
                    for a in v.inputs + v.outputs:
                        if a.label and a.description is None:
                            a.description = args.get(a.label)
                except Exception as e:
                    print(f"Error occurred while enriching node {v.name}: {e}")
                    print(f"docstring: {v.docstring}")
                    print(f"source_code: {source_code}")

        await atqdm.gather(  # pyright: ignore[reportUnknownMemberType]
            *[_enrich_one(v) for v in nodes_to_enrich],
            desc="generating ai descriptions",
            total=len(nodes_to_enrich),
        )
        self._save_to_disk()

        nodes_to_embed = [node for node in nodes_to_enrich if node.ai_description]
        documents = [self._embedding_text(node) for node in nodes_to_embed]
        if not documents:
            return
        embeddings = await create_embedding(documents, input_type="document")
        for emb, item in zip(embeddings, nodes_to_embed, strict=True):
            item.embedding = emb

        self._save_to_disk()
