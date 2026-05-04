import type { Annotation } from "@/interfaces/BackendSchema";

export type CompatibilityResult =
  | "match" // datatypes equal (or both null) — no warning
  | "unit-mismatch" // datatypes equal but unit or quantity differs — amber
  | "type-mismatch" // datatypes both non-null and not equal — red
  | "unknown"; // at least one datatype is null → treated as "any" → no warning

export function checkCompatibility(
  a: Annotation | null | undefined,
  b: Annotation | null | undefined,
): CompatibilityResult {
  const ta = a?.datatype ?? null;
  const tb = b?.datatype ?? null;

  // null = any: no warning
  if (ta === null || tb === null) return "unknown";

  // datatype mismatch
  if (ta !== tb) return "type-mismatch";

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
