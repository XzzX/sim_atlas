import type { Annotation, TypeNode } from "@/interfaces/BackendSchema";

export type CompatibilityResult =
  | "match" // datatypes equal (or both null) — no warning
  | "unit-mismatch" // datatypes equal but unit or quantity differs — amber
  | "type-mismatch" // datatypes both non-null and not equal — red
  | "unknown"; // at least one datatype is null → treated as "any" → no warning

// ---------------------------------------------------------------------------
// Structural compatibility: output (a) must be assignable to input (b)
// Strict rule: every member of `a` must be assignable to at least one member
// of `b` (output ⊆ input).
// Bare generic (e.g. "list" with no args) acts as a wildcard for any
// parameterisation of the same name.
// ---------------------------------------------------------------------------

export function typesCompatible(a: TypeNode, b: TypeNode): boolean {
  // a is union → every member of a must be assignable to b
  if (a.kind === "union") {
    return a.members.every((m) => typesCompatible(m, b));
  }
  // b is union → a must be compatible with at least one member of b
  if (b.kind === "union") {
    return b.members.some((m) => typesCompatible(a, m));
  }

  // Wildcard: bare "list" matches "list[int]" and vice-versa
  if (a.name !== b.name) return false;

  // Same name — if either side is bare (no args), it's a wildcard
  const aArgs = a.kind === "generic" ? a.args : [];
  const bArgs = b.kind === "generic" ? b.args : [];
  if (aArgs.length === 0 || bArgs.length === 0) return true;

  // Both parameterised: same arity + each arg compatible
  if (aArgs.length !== bArgs.length) return false;
  return aArgs.every((arg, i) => {
    const bArg = bArgs[i];
    return bArg !== undefined && typesCompatible(arg, bArg);
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function checkCompatibility(
  a: Annotation | null | undefined,
  b: Annotation | null | undefined,
): CompatibilityResult {
  const ta = a?.datatype?.ast ?? null;
  const tb = b?.datatype?.ast ?? null;

  // null = any: no warning
  if (ta === null || tb === null) return "unknown";

  // datatype mismatch
  if (!typesCompatible(ta, tb)) return "type-mismatch";

  // datatypes match — check unit and quantity
  const ua = a?.unit ?? null;
  const ub = b?.unit ?? null;
  const qa = a?.quantity ?? null;
  const qb = b?.quantity ?? null;

  if (
    (ua !== null && ub !== null && ua !== ub) ||
    (qa !== null && qb !== null && qa !== qb)
  ) {
    return "unit-mismatch";
  }

  return "match";
}
