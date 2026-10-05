from __future__ import annotations

import json
import logging
import os
from functools import reduce
from math import ceil
from pathlib import Path

from pydantic import BaseModel

from sim_atlas.embedding import create_embedding
from sim_atlas.models import (
    AnnotationResponse,
    ArtifactType,
    ExecutionResultMetadata,
    Filter,
    FilterOptions,
    NodeMetadata,
    NodeResponse,
    ScoredSearchItem,
    ScoredSearchResponse,
    SearchResults,
    Suggestion,
)
from sim_atlas.node_text import short_description
from sim_atlas.search import fusion, keyword, semantic, substring
from sim_atlas.settings import load_settings
from sim_atlas.storage.storage_interface import (
    ExecutionResultAlreadyExistsError,
    ExecutionResultDuplicateError,
    NodeAlreadyExistsError,
    NodeDuplicateError,
    StorageInterface,
)
from sim_atlas.storage.workflow_graph import WorkflowGraph
from sim_atlas.type_utils import collect_datatypes, datatype_matches

logger = logging.getLogger(__name__)


def _deserialize_node(data: dict[str, object]) -> NodeMetadata:
    node = NodeMetadata.model_validate(data)
    # Files written before WorkflowGraph may still carry derived references;
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

    def _annotations(self, node: NodeMetadata) -> list[AnnotationResponse]:
        if self.port_type == "inputs":
            return node.inputs
        if self.port_type == "outputs":
            return node.outputs
        return node.inputs + node.outputs

    def __call__(self, node: NodeMetadata) -> bool:  # noqa: PLR0911
        if self.category and not node.category.lower().startswith(self.category):
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

    NODES_FILENAME = "artifacts.json"
    EXECUTION_RESULTS_FILENAME = "execution_results.json"

    def __init__(self, path: Path | None = None) -> None:
        self._nodes: dict[str, NodeMetadata] = {}
        self._execution_results: dict[str, ExecutionResultMetadata] = {}
        self._path = path
        self._connected = False
        self._graph: WorkflowGraph | None = None

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

    def _nodes_changed(self) -> None:
        self._graph = None
        self._save_nodes_to_disk()

    def _hydrate[N: NodeResponse](self, node: N) -> N:
        """A copy of *node* with its derived workflow references filled in."""
        if self._graph is None:
            self._graph = WorkflowGraph(self._nodes)
        return self._graph.hydrate(node)

    def _hydrate_page(self, response: ScoredSearchResponse) -> ScoredSearchResponse:
        for item in response.results.data:
            item.node = self._hydrate(item.node)
        return response

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
        self._nodes_changed()
        return value

    def read_node(self, id: str) -> NodeMetadata:
        if id not in self._nodes:
            raise KeyError(id)
        return self._hydrate(self._nodes[id])

    def update_node(self, id: str, value: NodeMetadata) -> NodeMetadata:
        if id not in self._nodes:
            raise KeyError(id)
        self._nodes[id] = value
        self._nodes_changed()
        return value

    def delete_node(self, id: str) -> None:
        if id not in self._nodes:
            raise KeyError(id)
        del self._nodes[id]
        self._nodes_changed()

    def exists(self, id: str) -> bool:
        return id in self._nodes

    def count(self) -> int:
        return len(self._nodes)

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

        def extract_filter_options(node: NodeMetadata) -> FilterOptionsSet:
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
            (extract_filter_options(node) for node in self._nodes.values()),
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
            for item in self._nodes.values()
            if item_filter(item)
        ]

    def _filtered_nodes(self, filter: Filter | None) -> list[NodeMetadata]:
        item_filter = NodeFilter(filter or Filter())
        return [node for node in self._nodes.values() if item_filter(node)]

    @staticmethod
    def _scored(
        nodes: list[NodeMetadata], scores: dict[str, float]
    ) -> list[ScoredSearchItem]:
        """*nodes* that *scores* ranked, in their original order."""
        return [
            ScoredSearchItem(score=scores[node.id], node=node)
            for node in nodes
            if node.id in scores
        ]

    def _ranked_page(
        self, items: list[ScoredSearchItem], page: int, limit: int
    ) -> ScoredSearchResponse:
        """Sort *items* best-first (ties keep their order), paginate, hydrate."""
        items = sorted(items, key=lambda x: x.score, reverse=True)
        return self._hydrate_page(self._paginate(items, page=page, limit=limit))

    def search(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
        drop_unmatched: bool = True,
    ) -> ScoredSearchResponse:
        """Keyword search: typo-tolerant ranking over the filtered nodes.

        With ``drop_unmatched`` (the default) the query is a constraint and
        nodes it does not touch are excluded. With ``drop_unmatched=False``
        the filters alone decide membership and the query only orders what they
        returned, so adding a query can never shrink the result set.
        """
        filtered_items = self._filtered_nodes(filter)

        if not query or not query.strip():
            scored_items = [
                ScoredSearchItem(score=1.0, node=item) for item in filtered_items
            ]
        else:
            scores = keyword.rank(query, filtered_items)
            scored_items = [
                ScoredSearchItem(score=scores.get(item.id, 0.0), node=item)
                for item in filtered_items
                if not drop_unmatched or scores.get(item.id, 0.0) > 0.0
            ]

        return self._ranked_page(scored_items, page, limit)

    def _substring_hits(
        self, query: str, filter: Filter | None, *, case_sensitive: bool = False
    ) -> list[tuple[float, NodeMetadata]]:
        """Substring-leg hits that pass *filter*, best-first.

        Matches first, then filters the survivors — ``NodeFilter`` allocates
        ``inputs + outputs`` per node even with no port filter set, so
        matching first keeps the cost proportional to the match count instead
        of to the catalog size. Ties are broken by name, then id.
        """
        scores = substring.rank(
            query, self._nodes.values(), case_sensitive=case_sensitive
        )
        item_filter = NodeFilter(filter or Filter())
        hits = [
            (score, self._nodes[node_id])
            for node_id, score in scores.items()
            if item_filter(self._nodes[node_id])
        ]
        hits.sort(key=lambda hit: (-hit[0], hit[1].name.lower(), hit[1].id))
        return hits

    def search_substring(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
        case_sensitive: bool = False,
    ) -> ScoredSearchResponse:
        """Substring search over node names and import paths."""
        if not query or not query.strip():
            return self.search(query, filter, page=page, limit=limit)

        items = [
            ScoredSearchItem(score=score, node=node)
            for score, node in self._substring_hits(
                query, filter, case_sensitive=case_sensitive
            )
        ]
        return self._hydrate_page(self._paginate(items, page=page, limit=limit))

    def suggest(
        self, query: str, filter: Filter | None = None, limit: int = 10
    ) -> list[Suggestion]:
        """Cheap type-ahead lookup: the substring leg, projected to suggestions.

        No ``used_by``/connections hydration: this path exists to be fast.
        """
        hits = self._substring_hits(query, filter)
        return [self._to_suggestion(node) for _, node in hits[:limit]]

    @staticmethod
    def _to_suggestion(node: NodeMetadata) -> Suggestion:
        return Suggestion(
            id=node.id,
            name=node.name,
            python_import=node.python_import,
            artifact_type=node.artifact_type,
            short_description=short_description(node.brief_description, node.docstring),
            keywords=node.keywords,
        )

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

        filtered_nodes = self._filtered_nodes(filter)
        scores = semantic.rank(query_embedding, filtered_nodes)
        return self._ranked_page(self._scored(filtered_nodes, scores), page, limit)

    async def search_hybrid(
        self,
        query: str | None,
        filter: Filter | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> ScoredSearchResponse:
        """Hybrid search: weighted RRF of the substring, keyword and semantic legs.

        Without an embedding provider the semantic leg is skipped and the
        other two are fused, so search always works even without AI. A blank
        query has nothing to rank and returns the filtered set.

        Every leg sees every filtered node: unenriched nodes that have no
        embedding can still surface through the lexical legs, and nodes whose
        wording misses the query entirely can still surface through the
        semantic rank.
        """
        if not query or not query.strip():
            return self.search(query, filter, page=page, limit=limit)

        filtered_nodes = self._filtered_nodes(filter)
        legs = [
            fusion.Leg(fusion.SUBSTRING_WEIGHT, substring.rank(query, filtered_nodes)),
            fusion.Leg(fusion.KEYWORD_WEIGHT, keyword.rank(query, filtered_nodes)),
        ]
        if load_settings().embeddings_enabled:
            query_embedding = (await create_embedding([query], input_type="query"))[0]
            legs.append(
                fusion.Leg(
                    fusion.SEMANTIC_WEIGHT,
                    semantic.rank(query_embedding, filtered_nodes),
                    partial=True,
                )
            )

        fused = fusion.reciprocal_rank_fusion(legs)
        return self._ranked_page(self._scored(filtered_nodes, fused), page, limit)

    @staticmethod
    def _embedding_text(node: NodeMetadata) -> str:
        description = node.description or ""
        port_lines = [
            f"{a.label}: {a.description}"
            for a in node.inputs + node.outputs
            if a.label and a.description
        ]
        if not port_lines:
            return description
        return description + "\n" + "\n".join(port_lines)

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

    async def enrich(self, only_ids: list[str] | None = None) -> None:
        nodes_to_enrich = (
            [node for node in self._nodes.values() if node.id in only_ids]
            if only_ids
            else [node for node in self._nodes.values() if node.embedding is None]
        )
        nodes_to_embed = [node for node in nodes_to_enrich if node.description]
        documents = [self._embedding_text(node) for node in nodes_to_embed]
        if not documents:
            return
        embeddings = await create_embedding(documents, input_type="document")
        for emb, item in zip(embeddings, nodes_to_embed, strict=True):
            item.embedding = emb

        self._save_nodes_to_disk()

    async def embed_missing(self) -> None:
        nodes_to_embed = [
            node for node in self._nodes.values() if node.embedding is None
        ]

        documents = [self._embedding_text(node) for node in nodes_to_embed]
        if not documents:
            return
        embeddings = await create_embedding(documents, input_type="document")
        for emb, item in zip(embeddings, nodes_to_embed, strict=True):
            item.embedding = emb

        self._save_nodes_to_disk()
