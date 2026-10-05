"""Typo-tolerant keyword ranking over catalog nodes.

Keyword search is the leg that always runs: it needs no embedding provider, and
it keeps the exact identifier matches that a vector index blurs away. Queries
reaching the catalog are sentence-shaped ("compute the gradient of a temperature
field") and typed by people, so matching is per-token and forgiving:

* every query token also matches catalog tokens that are close in spelling
  (trigram similarity), so "temprature" finds "temperature";
* the query's trailing token additionally matches as a prefix (the user may
  still be typing it), so "compute the gradient of a temp" already matches
  "temperature".

Scoring is "best field per term": each query term counts once per node, at
the weight of the most important field it hits, scaled by match quality and
IDF. Taking the best field rather than summing over fields keeps text that a
node repeats (its name is usually also its import path and often a keyword)
from being counted several times. Pure functions only: no storage, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from math import log

from sim_atlas.models import NodeMetadata

# Identifiers are the point: splitting on every non-alphanumeric turns
# "ase.md.get_temperature" into the tokens a sentence-shaped query contains.
_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")
# CamelCase parts of one word: "HTTPServerNode" -> "HTTP", "Server", "Node".
# The first branch keeps an acronym together up to the next capitalised part.
_CAMEL_PART_PATTERN = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")

MIN_QUERY_TOKEN_LEN = 3

# Shorter tokens have too few trigrams for similarity to tell a typo from a
# different word ("fcc" vs "bcc").
MIN_FUZZY_TOKEN_LEN = 4
# Jaccard similarity of padded trigram sets. "temprature"/"temperature" is
# 0.64 and "gradiant"/"gradient" 0.5, while "mesh"/"mess" is 0.43.
FUZZY_THRESHOLD = 0.45

# Match quality: an exact hit counts fully; a completion of the trailing
# token or a near spelling counts less, so the exact word always ranks first.
_PREFIX_QUALITY = 0.9
_FUZZY_QUALITY = 0.8  # multiplied by the trigram similarity

# A hit in the callable's name says far more than one buried in a docstring.
_NAME_WEIGHT = 3.0
_IMPORT_WEIGHT = 2.0
_KEYWORD_WEIGHT = 2.0
_BRIEF_WEIGHT = 2.0
_DOCSTRING_WEIGHT = 1.0
_CATEGORY_WEIGHT = 1.0
_PORT_WEIGHT = 1.0


def tokenize(text: str) -> list[str]:
    """Split *text* into lowercase alphanumeric tokens, CamelCase included.

    A CamelCase word yields its parts followed by the whole word, so
    "BuildMgGrainBoundary" is found by "grain" while "buildmg" still matches
    the whole word as a prefix. The whole word comes last because ``rank``
    prefix-expands a query's trailing token.
    """
    tokens: list[str] = []
    for word in _WORD_PATTERN.findall(text):
        parts = [part.lower() for part in _CAMEL_PART_PATTERN.findall(word)]
        tokens.extend(parts)
        if len(parts) > 1:
            tokens.append(word.lower())
    return tokens


def token_starts(text: str) -> set[int]:
    """The offsets in *text* at which a ``tokenize`` token begins."""
    return {
        part.start()
        for word in _WORD_PATTERN.finditer(text)
        for part in _CAMEL_PART_PATTERN.finditer(text, word.start(), word.end())
    }


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


@lru_cache(maxsize=65536)
def _trigrams(token: str) -> frozenset[str]:
    # Padding as pg_trgm does lets word boundaries carry weight, so a shared
    # start of word counts for more than a shared middle.
    padded = f"  {token} "
    return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))


def trigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity of the padded trigram sets of *a* and *b*."""
    trigrams_a, trigrams_b = _trigrams(a), _trigrams(b)
    return len(trigrams_a & trigrams_b) / len(trigrams_a | trigrams_b)


def _could_be_similar(a: str, b: str) -> bool:
    """Cheap length bound: Jaccard can never exceed the size ratio of the sets."""
    shorter, longer = sorted((len(a) + 1, len(b) + 1))
    return shorter >= FUZZY_THRESHOLD * longer


def _expand(term: str, is_prefix: bool, vocabulary: set[str]) -> dict[str, float]:
    """The catalog tokens *term* matches, mapped to their match quality."""
    matches: dict[str, float] = {}
    fuzzy = len(term) >= MIN_FUZZY_TOKEN_LEN
    for token in vocabulary:
        if token == term:
            quality = 1.0
        elif is_prefix and token.startswith(term):
            quality = _PREFIX_QUALITY
        elif fuzzy and _could_be_similar(term, token):
            similarity = trigram_similarity(term, token)
            if similarity < FUZZY_THRESHOLD:
                continue
            quality = _FUZZY_QUALITY * similarity
        else:
            continue
        matches[token] = quality
    return matches


def _weighted_fields(node: NodeMetadata) -> list[tuple[float, str]]:
    port_text = " ".join(
        part
        for port in node.inputs + node.outputs
        for part in (port.label, port.unit, port.quantity, port.description)
        if part
    )
    return [
        (_NAME_WEIGHT, node.name),
        (_IMPORT_WEIGHT, node.python_import or ""),
        (_KEYWORD_WEIGHT, " ".join(node.keywords)),
        (_BRIEF_WEIGHT, node.brief_description or ""),
        (_DOCSTRING_WEIGHT, node.docstring or ""),
        (_CATEGORY_WEIGHT, node.category),
        (_PORT_WEIGHT, port_text),
    ]


def _token_weights(node: NodeMetadata) -> dict[str, float]:
    """Each token of *node* mapped to the weight of the best field holding it."""
    weights: dict[str, float] = {}
    for weight, text in _weighted_fields(node):
        for token in tokenize(text):
            weights[token] = max(weights.get(token, 0.0), weight)
    return weights


def _best_hit(weights: dict[str, float], matches: dict[str, float]) -> float:
    """The best ``field weight × match quality`` of one term in one node."""
    # Walk the smaller side: a short prefix can match thousands of tokens.
    if len(matches) < len(weights):
        pairs = ((weights.get(t, 0.0), q) for t, q in matches.items())
    else:
        pairs = ((w, matches.get(t, 0.0)) for t, w in weights.items())
    return max((w * q for w, q in pairs), default=0.0)


def rank(query: str, nodes: Iterable[NodeMetadata]) -> dict[str, float]:
    """Score *nodes* against *query*, as ``{node id: score}``.

    Only nodes that at least one query token touches are present; the rest
    are absent rather than scored zero. Scores are comparable within one call
    only — IDF is computed over the nodes passed in.

    A node's score sums, over the query terms, ``idf × field weight × match
    quality`` for the best hit of that term in the node. Repeating a word, or
    holding it in several fields, adds nothing beyond its best occurrence.
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

    token_weights = {node.id: _token_weights(node) for node in nodes}
    if not token_weights:
        return {}

    vocabulary = {token for weights in token_weights.values() for token in weights}
    total = len(token_weights)

    scores: dict[str, float] = {}
    for term, is_prefix in terms:
        matches = _expand(term, is_prefix, vocabulary)
        if not matches:
            continue
        best_by_node: dict[str, float] = {}
        for key, weights in token_weights.items():
            best = _best_hit(weights, matches)
            if best > 0.0:
                best_by_node[key] = best
        if not best_by_node:
            continue
        matching = len(best_by_node)
        idf = log(1 + (total - matching + 0.5) / (matching + 0.5))
        for key, best in best_by_node.items():
            scores[key] = scores.get(key, 0.0) + idf * best
    return scores
