"""BM25 keyword ranking over catalog artifacts.

Keyword search is the leg that always runs: it needs no embedding provider, and
it keeps the exact identifier matches that a vector index blurs away. Queries
reaching the catalog are sentence-shaped ("compute the gradient of a temperature
field"), so matching has to be per-token — a whole-query substring test finds
nothing. Pure functions only: no storage, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from math import log

from sim_atlas.models import StoredArtifact

# Identifiers are the point: splitting on every non-alphanumeric turns
# "ase.md.get_temperature" into the tokens a sentence-shaped query contains.
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

MIN_QUERY_TOKEN_LEN = 3

# Standard BM25 term-saturation and length-normalisation constants.
_K1 = 1.5
_B = 0.75

# A hit in the callable's name says far more than one buried in a docstring.
_NAME_WEIGHT = 3.0
_IMPORT_WEIGHT = 2.0
_KEYWORD_WEIGHT = 2.0
_BRIEF_WEIGHT = 2.0
_DOCSTRING_WEIGHT = 1.0
_CATEGORY_WEIGHT = 1.0
_PORT_WEIGHT = 1.0


def tokenize(text: str) -> list[str]:
    """Split *text* into lowercase alphanumeric tokens."""
    return _TOKEN_PATTERN.findall(text.lower())


def query_tokens(query: str) -> list[str]:
    """The tokens of *query* worth matching on.

    Tokens shorter than three characters are dropped, so short-but-meaningful
    domain tokens like "fcc" survive while noise like "of" does not. Real
    stopwords ("the", "for") are left to IDF, which weights them to near zero.

    That filter targets noise words in sentence-shaped queries. If it would
    leave nothing, the query was an identifier rather than a sentence — a
    lookup of "fn_a" splits into two short tokens — so every token is kept.
    """
    tokens = tokenize(query)
    long_tokens = [token for token in tokens if len(token) >= MIN_QUERY_TOKEN_LEN]
    return long_tokens or tokens


def _weighted_fields(artifact: StoredArtifact) -> list[tuple[float, str]]:
    port_text = " ".join(
        part
        for port in artifact.inputs + artifact.outputs
        for part in (port.label, port.unit, port.quantity, port.description)
        if part
    )
    return [
        (_NAME_WEIGHT, artifact.name),
        (_IMPORT_WEIGHT, artifact.python_import or ""),
        (_KEYWORD_WEIGHT, " ".join(artifact.keywords)),
        (_BRIEF_WEIGHT, artifact.brief_description or ""),
        (_DOCSTRING_WEIGHT, artifact.docstring or ""),
        (_CATEGORY_WEIGHT, artifact.category),
        (_PORT_WEIGHT, port_text),
    ]


def _term_frequencies(artifact: StoredArtifact) -> dict[str, float]:
    """Weighted term frequencies for one artifact, fields folded into one bag."""
    frequencies: dict[str, float] = {}
    for weight, text in _weighted_fields(artifact):
        for token in tokenize(text):
            frequencies[token] = frequencies.get(token, 0.0) + weight
    return frequencies


def rank(query: str, artifacts: Iterable[StoredArtifact]) -> dict[str, float]:
    """Score *artifacts* against *query*, as ``{artifact id: score}``.

    Only artifacts that at least one query token touches are present; the rest
    are absent rather than scored zero. Scores are comparable within one call
    only — IDF is computed over the artifacts passed in.
    """
    tokens = set(query_tokens(query))
    if not tokens:
        return {}

    frequencies = {artifact.id: _term_frequencies(artifact) for artifact in artifacts}
    if not frequencies:
        return {}

    lengths = {key: sum(value.values()) for key, value in frequencies.items()}
    average_length = (sum(lengths.values()) / len(lengths)) or 1.0
    total = len(frequencies)

    scores: dict[str, float] = {}
    for token in tokens:
        matching = [key for key, value in frequencies.items() if token in value]
        if not matching:
            continue
        idf = log(1 + (total - len(matching) + 0.5) / (len(matching) + 0.5))
        for key in matching:
            frequency = frequencies[key][token]
            normalisation = 1 - _B + _B * lengths[key] / average_length
            scores[key] = scores.get(key, 0.0) + idf * (frequency * (_K1 + 1)) / (
                frequency + _K1 * normalisation
            )
    return scores
