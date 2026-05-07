import type { Annotation } from "@/interfaces/BackendSchema";

export type CompatibilityResult =
  | "match" // datatypes equal (or both null) — no warning
  | "unit-mismatch" // datatypes equal but unit or quantity differs — amber
  | "type-mismatch" // datatypes both non-null and not equal — red
  | "unknown"; // at least one datatype is null → treated as "any" → no warning

// ---------------------------------------------------------------------------
// Type AST
// ---------------------------------------------------------------------------

interface SimpleNode {
  kind: "simple";
  name: string;
}
interface GenericNode {
  kind: "generic";
  name: string;
  args: TypeNode[];
}
interface UnionNode {
  kind: "union";
  members: TypeNode[];
}
type TypeNode = SimpleNode | GenericNode | UnionNode;

// ---------------------------------------------------------------------------
// Parser
// Parses canonical Python type strings produced by the toolkit:
//   "int", "None", "list[int]", "dict[str, float]", "int | float"
// ---------------------------------------------------------------------------

function parseType(s: string): TypeNode {
  const ctx = { src: s.trim(), pos: 0 };
  const node = parseUnion(ctx);
  return node;
}

interface ParseCtx {
  src: string;
  pos: number;
}

function parseUnion(ctx: ParseCtx): TypeNode {
  const members: TypeNode[] = [parseGeneric(ctx)];
  while (ctx.src.startsWith(" | ", ctx.pos)) {
    ctx.pos += 3; // consume " | "
    members.push(parseGeneric(ctx));
  }
  return members.length === 1 ? members[0] : { kind: "union", members };
}

function parseGeneric(ctx: ParseCtx): TypeNode {
  const name = parseName(ctx);
  if (ctx.src[ctx.pos] !== "[") {
    return { kind: "simple", name };
  }
  ctx.pos++; // consume "["
  const args: TypeNode[] = [parseUnion(ctx)];
  while (ctx.src[ctx.pos] === ",") {
    ctx.pos++; // consume ","
    if (ctx.src[ctx.pos] === " ") ctx.pos++; // consume optional space
    args.push(parseUnion(ctx));
  }
  ctx.pos++; // consume "]"
  return { kind: "generic", name, args };
}

function parseName(ctx: ParseCtx): string {
  const start = ctx.pos;
  while (ctx.pos < ctx.src.length && /[\w.]/.test(ctx.src[ctx.pos] ?? "")) {
    ctx.pos++;
  }
  return ctx.src.slice(start, ctx.pos);
}

// ---------------------------------------------------------------------------
// Structural compatibility: output (a) must be assignable to input (b)
// Strict rule: every member of `a` must be assignable to at least one member
// of `b` (output ⊆ input).
// Bare generic (e.g. "list" with no args) acts as a wildcard for any
// parameterisation of the same name.
// ---------------------------------------------------------------------------

function typesCompatible(a: TypeNode, b: TypeNode): boolean {
  // a is union → every member of a must be assignable to b
  if (a.kind === "union") {
    return a.members.every((m) => typesCompatible(m, b));
  }
  // b is union → a must be compatible with at least one member of b
  if (b.kind === "union") {
    return b.members.some((m) => typesCompatible(a, m));
  }

  // Wildcard: bare "list" matches "list[int]" and vice-versa
  const aName = a.kind === "generic" ? a.name : a.name;
  const bName = b.kind === "generic" ? b.name : b.name;
  if (aName !== bName) return false;

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
  const ta = a?.datatype ?? null;
  const tb = b?.datatype ?? null;

  // null = any: no warning
  if (ta === null || tb === null) return "unknown";

  // datatype mismatch
  if (!typesCompatible(parseType(ta), parseType(tb))) return "type-mismatch";

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
