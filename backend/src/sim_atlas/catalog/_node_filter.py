"""Facet filtering over catalog nodes, and the facet values the catalog offers."""

from __future__ import annotations

from collections.abc import Iterable
from functools import reduce

from pydantic import BaseModel

from sim_atlas.models import (
    AnnotationResponse,
    ArtifactType,
    Filter,
    FilterOptions,
    NodeMetadata,
)
from sim_atlas.type_utils import collect_datatypes, datatype_matches


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


def filter_options(nodes: Iterable[NodeMetadata]) -> FilterOptions:
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
        (extract_filter_options(node) for node in nodes),
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
