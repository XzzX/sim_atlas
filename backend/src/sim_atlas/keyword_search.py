"""BM25 keyword ranking over catalog artifacts.

Keyword search is the leg that always runs: it needs no embedding provider, and
it keeps the exact identifier matches that a vector index blurs away. Queries
reaching the catalog are sentence-shaped ("compute the gradient of a temperature
field"), so matching has to be per-token — a whole-query substring test finds
nothing. The query's trailing token is additionally treated as a prefix (the
user may still be typing it), so "compute the gradient of a temp" matches
"temperature" before the word is finished. Pure functions only: no storage, no
I/O.
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
    """The tokens of *query* worth matching on, in order.

    Tokens shorter than three characters are dropped, so short-but-meaningful
    domain tokens like "fcc" survive while noise like "of" does not. Real
    stopwords ("the", "for") are left to IDF, which weights them to near zero.

    That filter targets noise words in sentence-shaped queries. If it would
    leave nothing, the query was an identifier rather than a sentence — a
    lookup of "fn_a" splits into two short tokens — so every token is kept.

    The order is kept (rather than returning a set) because ``rank`` treats the
    last token specially: it may still be mid-word.
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


def _term_frequency(
    term_frequencies: dict[str, float], term: str, is_prefix: bool
) -> float:
    """The weighted frequency of *term* in one document's term-frequency bag.

    A prefix term is treated as a single synthetic term: its frequency is the
    sum across every token in the bag that starts with it, so a document
    containing "temperature" scores as if it contained the fragment "temp"
    once, not once per matching token.
    """
    if not is_prefix:
        return term_frequencies.get(term, 0.0)
    return sum(
        frequency
        for token, frequency in term_frequencies.items()
        if token.startswith(term)
    )


def rank(query: str, artifacts: Iterable[StoredArtifact]) -> dict[str, float]:
    """Score *artifacts* against *query*, as ``{artifact id: score}``.

    Only artifacts that at least one query token touches are present; the rest
    are absent rather than scored zero. Scores are comparable within one call
    only — IDF is computed over the artifacts passed in.

    The query's trailing token is matched as a prefix rather than a whole word,
    since it may still be mid-word ("compute the temp" should already surface
    "temperature"). Earlier tokens are matched exactly.
    """
    query_terms = query_tokens(query)
    if not query_terms:
        return {}

    # The last token may be incomplete; the rest are complete words. If the
    # trailing token also appears earlier, it is scored once, as a prefix —
    # its expansion already covers its own exact match.
    prefix_term = query_terms[-1]
    exact_terms = set(query_terms[:-1]) - {prefix_term}
    terms = [(term, False) for term in exact_terms] + [(prefix_term, True)]

    frequencies = {artifact.id: _term_frequencies(artifact) for artifact in artifacts}
    if not frequencies:
        return {}

    lengths = {key: sum(value.values()) for key, value in frequencies.items()}
    average_length = (sum(lengths.values()) / len(lengths)) or 1.0
    total = len(frequencies)

    scores: dict[str, float] = {}
    for term, is_prefix in terms:
        term_frequency_by_doc = {
            key: _term_frequency(value, term, is_prefix)
            for key, value in frequencies.items()
        }
        matching = [key for key, tf in term_frequency_by_doc.items() if tf > 0.0]
        if not matching:
            continue
        idf = log(1 + (total - len(matching) + 0.5) / (len(matching) + 0.5))
        for key in matching:
            frequency = term_frequency_by_doc[key]
            normalisation = 1 - _B + _B * lengths[key] / average_length
            scores[key] = scores.get(key, 0.0) + idf * (frequency * (_K1 + 1)) / (
                frequency + _K1 * normalisation
            )
    return scores
