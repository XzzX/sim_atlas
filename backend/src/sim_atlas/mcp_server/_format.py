"""Render catalog artifacts as Python, for a CLI coding agent (ADR-0019).

Every result block leads with a reconstructed call signature and an import
statement; everything else is commented out, so the only line an agent can lift
into a script is the import. Pure functions only — no storage, no I/O.
"""

from sim_atlas.artifact_text import short_description
from sim_atlas.models import (
    AnnotationResponse,
    ArtifactType,
    NodeResponse,
    PackageRef,
    Reference,
    ScoredSearchResponse,
)

Artifact = NodeResponse

MAX_RESULTS = 5
MAX_DESCRIPTION_CHARS = 240
MAX_PORT_DESCRIPTION_CHARS = 120
MAX_PORT_NOTES = 12
MAX_DOCSTRING_CHARS = 4000
MAX_SOURCE_LINES = 600
MAX_SOURCE_CHARS = 24_000
MAX_PACKAGES = 3
MAX_REFERENCES = 5

_NO_IMPORT_FUNCTION = "# no import path recorded for this entry"


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def _is_workflow(artifact: Artifact) -> bool:
    return artifact.artifact_type == ArtifactType.WORKFLOW


def _callable_name(artifact: Artifact) -> str | None:
    """The bare callable name.

    ``python_import`` is ``module.qualname``; for flowrep artifacts ``name`` is
    dotted too, so both are reduced to their last segment.
    """
    for candidate in (artifact.python_import, artifact.name):
        if candidate:
            last = candidate.rsplit(".", 1)[-1]
            if last:
                return last
    return None


def _parameters(inputs: list[AnnotationResponse]) -> str:
    """Render parameters in declared order — the stored order is the call order."""
    parts: list[str] = []
    for index, port in enumerate(inputs):
        piece = port.label or f"arg{index}"
        if port.datatype:
            piece += f": {port.datatype}"
        if port.has_default_value:
            # Default *values* are not stored; "..." is the honest placeholder.
            piece += " = ..."
        parts.append(piece)
    return ", ".join(parts)


def _return_annotation(outputs: list[AnnotationResponse]) -> str:
    if not outputs:
        return " -> None"
    if len(outputs) == 1:
        datatype = outputs[0].datatype
        return f" -> {datatype}" if datatype else ""
    # Preserve arity: a caller unpacking the tuple needs to know how many.
    inner = ", ".join(port.datatype or "Any" for port in outputs)
    return f" -> tuple[{inner}]"


def render_signature(artifact: Artifact) -> str:
    name = _callable_name(artifact)
    if name is None:
        return "# <signature unavailable>"
    params = _parameters(artifact.inputs)
    return f"def {name}({params}){_return_annotation(artifact.outputs)}"


def render_import(artifact: Artifact) -> str:
    python_import = artifact.python_import or ""
    if not python_import:
        if _is_workflow(artifact):
            return (
                "# no import path recorded — this workflow is stored as a graph; "
                f'call get_workflow_source("{artifact.id}") for its definition'
            )
        return _NO_IMPORT_FUNCTION
    module, separator, qualname = python_import.rpartition(".")
    if not separator:
        return f"import {python_import}"
    return f"from {module} import {qualname}"


def _install_line(package: PackageRef) -> str:
    if package.ecosystem == "conda":
        spec = f"{package.name}={package.version}" if package.version else package.name
        channel = f" -c {package.channel}" if package.channel else ""
        return f"# install: conda install{channel} {spec}"
    spec = f'"{package.name}=={package.version}"' if package.version else package.name
    return f"# install: pip install {spec}"


def render_install(artifact: Artifact) -> list[str]:
    """Install hints, degrading to the import root when nothing was recorded.

    These describe what an uploader's environment contained (ADR-0012); they are
    suggestions for the user to confirm, never authoritative commands.
    """
    shown = artifact.packages[:MAX_PACKAGES]
    lines = [_install_line(package) for package in shown]
    remaining = len(artifact.packages) - len(shown)
    if remaining > 0:
        lines.append(f"# …and {remaining} more package(s)")
    if lines:
        return lines

    root = (artifact.python_import or "").split(".")[0]
    if root:
        return [
            "# install: not recorded; the callable lives in the "
            f"top-level module '{root}'"
        ]
    return []


def _port_note(label: str, port: AnnotationResponse) -> str | None:
    """A note only for ports that say something the signature does not."""
    bits: list[str] = []
    if port.has_default_value:
        bits.append("optional")
    if port.unit:
        bits.append(f"unit: {port.unit}")
    if port.quantity:
        bits.append(f"quantity: {port.quantity}")
    if port.description:
        bits.append(_truncate(port.description, MAX_PORT_DESCRIPTION_CHARS))
    if not bits:
        return None
    return f"# {label} — {'; '.join(bits)}"


def _output_label(port: AnnotationResponse, total: int, index: int) -> str:
    if total == 1:
        return "returns"
    return f"returns.{port.label or index}"


def _port_notes(artifact: Artifact) -> list[str]:
    notes: list[str] = []
    for index, port in enumerate(artifact.inputs):
        note = _port_note(port.label or f"arg{index}", port)
        if note:
            notes.append(note)
    total = len(artifact.outputs)
    for index, port in enumerate(artifact.outputs):
        note = _port_note(_output_label(port, total, index), port)
        if note:
            notes.append(note)
    if len(notes) <= MAX_PORT_NOTES:
        return notes
    hidden = len(notes) - MAX_PORT_NOTES
    return [
        *notes[:MAX_PORT_NOTES],
        f'# …{hidden} more annotated port(s), see get_function("{artifact.id}")',
    ]


def render_hit(artifact: Artifact) -> str:
    kind = "workflow" if _is_workflow(artifact) else "function"
    lines = [
        render_signature(artifact),
        render_import(artifact),
        *render_install(artifact),
        f"# id: {artifact.id} ({kind})",
    ]
    summary = short_description(artifact.brief_description, artifact.docstring)
    if summary:
        lines.append(f"# {_truncate(summary, MAX_DESCRIPTION_CHARS)}")
    lines.extend(_port_notes(artifact))
    if _is_workflow(artifact):
        lines.append(f'# get_workflow_source("{artifact.id}") for the full pipeline.')
    return "\n".join(lines)


def render_no_matches(query: str | None) -> str:
    return "\n".join(
        [
            f'# No matches in the Simulation Atlas for "{query or ""}".',
            '# Try different domain wording, a broader query, kind="any", or '
            "find_by_signature(datatype=…, unit=…).",
            "# If a second attempt also finds nothing, the catalog does not cover "
            "this — write the code yourself.",
        ]
    )


def render_results(query: str | None, response: ScoredSearchResponse) -> str:
    items = response.results.data[:MAX_RESULTS]
    if not items:
        return render_no_matches(query)
    total = response.results.total_items
    header = (
        f'# {len(items)} of {total} matches in the Simulation Atlas for "{query or ""}"'
    )
    blocks = [render_hit(item.node) for item in items]
    footer = (
        "# Call get_function(id) for the full docstring. "
        "Import these — do not re-implement them."
    )
    return "\n\n".join([header, *blocks, footer])


def _render_references(label: str, references: list[Reference] | None) -> list[str]:
    if not references:
        return []
    shown = references[:MAX_REFERENCES]
    rendered = ", ".join(f"{ref.id} ({ref.label})" for ref in shown)
    remaining = len(references) - len(shown)
    suffix = f", …{remaining} more" if remaining > 0 else ""
    return [f"{label} {len(references)}: {rendered}{suffix}"]


def _render_ports(heading: str, ports: list[AnnotationResponse]) -> list[str]:
    if not ports:
        return []
    lines = [heading]
    for index, port in enumerate(ports):
        piece = f"  {port.label or f'arg{index}'}"
        if port.datatype:
            piece += f": {port.datatype}"
        if port.has_default_value:
            piece += " (optional)"
        annotations = [
            f"unit: {port.unit}" if port.unit else "",
            f"quantity: {port.quantity}" if port.quantity else "",
        ]
        present = [a for a in annotations if a]
        if present:
            piece += f" — {'; '.join(present)}"
        if port.description:
            piece += f" — {_truncate(port.description, MAX_PORT_DESCRIPTION_CHARS)}"
        lines.append(piece)
    return lines


def render_detail(artifact: Artifact) -> str:
    kind = "workflow" if _is_workflow(artifact) else "function"
    lines = [
        render_signature(artifact),
        render_import(artifact),
        *render_install(artifact),
        f"# id: {artifact.id} ({kind})",
        "",
        f"name: {artifact.name}",
        f"category: {artifact.category} | keywords: {', '.join(artifact.keywords)} "
        f"| author: {artifact.author_name}",
    ]

    docstring = (artifact.docstring or "").strip()
    if docstring:
        lines.extend(["", "Docstring:"])
        if len(docstring) > MAX_DOCSTRING_CHARS:
            lines.extend([docstring[:MAX_DOCSTRING_CHARS], "[docstring truncated]"])
        else:
            lines.append(docstring)

    ports = [
        *_render_ports("Parameters:", artifact.inputs),
        *_render_ports("Returns:", artifact.outputs),
    ]
    if ports:
        lines.extend(["", *ports])

    references = [
        *_render_references("Used by", artifact.used_by),
        *_render_references("See also", artifact.see_also),
    ]
    if references:
        lines.extend(["", *references])

    links = [
        f"docs {artifact.documentation_url}" if artifact.documentation_url else "",
        f"source {artifact.source_url}" if artifact.source_url else "",
        f"homepage {artifact.homepage_url}" if artifact.homepage_url else "",
    ]
    present_links = [link for link in links if link]
    if present_links:
        lines.extend(["", f"Links: {' | '.join(present_links)}"])

    if _is_workflow(artifact):
        lines.extend(
            [
                "",
                f'Source: call get_workflow_source("{artifact.id}") for this '
                "workflow's executable Python.",
            ]
        )
    return "\n".join(lines)


def render_source(artifact: Artifact) -> str:
    source = artifact.source_code or ""
    if not source.strip():
        return (
            f"# No source code is stored for workflow '{artifact.id}'. "
            "It is registered by graph definition only."
        )

    is_json_graph = source.lstrip().startswith("{")
    if is_json_graph:
        note = (
            "# This workflow is stored as a python_workflow_definition JSON graph, "
            "not executable Python. It describes which catalog functions are wired "
            "together; call get_function(id) on each to import them."
        )
    else:
        note = (
            "# Stored rendered Python of this workflow. Imports are as stored — "
            "check them against your environment."
        )

    header = [
        f"# workflow: {artifact.name}",
        f"# id: {artifact.id}",
        render_import(artifact),
        *render_install(artifact),
        note,
    ]

    lines = source.splitlines()
    truncated = False
    if len(lines) > MAX_SOURCE_LINES:
        lines = lines[:MAX_SOURCE_LINES]
        truncated = True
    body = "\n".join(lines)
    if len(body) > MAX_SOURCE_CHARS:
        body = body[:MAX_SOURCE_CHARS]
        truncated = True

    parts = ["\n".join(header), body]
    if truncated:
        total = len(source.splitlines())
        where = artifact.source_url or "the catalog UI"
        parts.append(
            f"# [truncated: showing the first {len(lines)} of {total} lines — "
            f"the full source is at {where}]"
        )
    return "\n\n".join(parts)
