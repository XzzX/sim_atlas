"""Pure ranking functions behind the storage search methods.

Three legs share one contract — ``rank(...) -> {node id: score}``, with
non-matches absent rather than scored zero — and ``fusion`` combines them:

* ``substring``: literal name/import matches, tiered then by coverage
* ``keyword``: typo-tolerant, best-field token scoring
* ``semantic``: cosine similarity to a precomputed query embedding
* ``fusion``: weighted reciprocal rank fusion of the legs

No storage and no I/O here; a storage backend composes these, or overrides
its ``search_*`` methods with a native implementation instead.
"""
