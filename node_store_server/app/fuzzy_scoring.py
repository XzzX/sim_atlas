import math
from numba import jit


@jit
def is_word_start(s: str, i: int) -> bool:
    if i == 0:
        return True
    return not s[i - 1].isalnum()


@jit
def is_camel_case_boundary(s: str, i: int) -> bool:
    if i == 0:
        return False
    return s[i].isupper() and s[i - 1].islower()


@jit
def weighted_fuzzy_score(query: str, candidate: str) -> float:
    """
    Optimized O(n * m) weighted subsequence matcher.
    Returns a float score (higher is better).
    Returns -inf if query is not a subsequence.
    """

    q = query
    c = candidate
    n = len(q)
    m = len(c)

    if n == 0:
        return 0.0

    prev = [-math.inf] * m
    curr = [-math.inf] * m

    # ---- Initialize first row ----
    for j in range(m):
        if q[0].lower() == c[j].lower():
            score = 1.0

            if j == 0:
                score += 3.0  # strong prefix bonus

            if is_word_start(c, j):
                score += 2.0

            if is_camel_case_boundary(c, j):
                score += 2.0

            prev[j] = score

    # ---- DP ----
    for i in range(1, n):
        best_prefix_score = -math.inf
        best_prefix_index = -1  # only used to compute gap

        for j in range(m):
            # Maintain prefix max
            if prev[j] > best_prefix_score:
                best_prefix_score = prev[j]
                best_prefix_index = j

            curr[j] = -math.inf

            if q[i].lower() != c[j].lower():
                continue

            if best_prefix_score == -math.inf:
                continue

            gap = j - best_prefix_index - 1
            score = best_prefix_score + 1.0

            # Consecutive bonus
            if gap == 0:
                score += 2.0

            # Gap penalty
            score -= gap * 0.15

            # Word start bonus
            if is_word_start(c, j):
                score += 1.5

            # CamelCase bonus
            if is_camel_case_boundary(c, j):
                score += 1.5

            curr[j] = score

        prev, curr = curr, prev

    best_score = max(prev)

    return best_score


@jit
def weighted_fuzzy_match(query: str | None, candidate: str) -> tuple[float, list[int]]:
    """
    Optimized O(n * m) weighted subsequence matcher.

    Returns:
        (score, positions)
    """

    if not query:
        return 1.0, [0]

    q = query
    c = candidate
    n = len(q)
    m = len(c)

    if n == 0:
        return 0.0, [0]

    # DP rows (rolling arrays)
    prev = [-math.inf] * m
    curr = [-math.inf] * m

    # Parent pointers for reconstruction
    parent = [[-1] * m for _ in range(n)]

    # ---- Initialize first row ----
    for j in range(m):
        if q[0].lower() == c[j].lower():
            score = 1.0

            if j == 0:
                score += 3.0  # strong prefix bonus

            if is_word_start(c, j):
                score += 2.0

            if is_camel_case_boundary(c, j):
                score += 2.0

            prev[j] = score

    # ---- DP ----
    for i in range(1, n):
        best_prefix_score = -math.inf
        best_prefix_index = -1

        for j in range(m):
            # Maintain prefix max for prev row
            if prev[j] > best_prefix_score:
                best_prefix_score = prev[j]
                best_prefix_index = j

            curr[j] = -math.inf

            if q[i].lower() != c[j].lower():
                continue

            if best_prefix_score == -math.inf:
                continue

            gap = j - best_prefix_index - 1
            score = best_prefix_score + 1.0

            # Consecutive bonus
            if gap == 0:
                score += 2.0

            # Gap penalty
            score -= gap * 0.15

            # Word start bonus
            if is_word_start(c, j):
                score += 1.5

            # CamelCase bonus
            if is_camel_case_boundary(c, j):
                score += 1.5

            curr[j] = score
            parent[i][j] = best_prefix_index

        prev, curr = curr, prev  # swap rows

    # ---- Find best end position ----
    best_score = -math.inf
    best_end = -1

    for j in range(m):
        if prev[j] > best_score:
            best_score = prev[j]
            best_end = j

    if best_score == -math.inf:
        return -math.inf, [0]

    # ---- Reconstruct match path ----
    positions: list[int] = []
    i = n - 1
    j = best_end

    while i >= 0:
        positions.append(j)
        j = parent[i][j]
        i -= 1

    positions.reverse()

    return best_score, positions
