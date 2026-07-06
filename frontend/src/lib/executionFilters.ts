import type { Annotation, ExecutionResultMetadata } from "@/types/index";

export type ScalarKind = "int" | "float" | "bool" | "str";

export function classifyScalarDatatype(datatype: string): ScalarKind | null {
  const leaves = [...new Set(datatype.split("|").map((s) => s.trim()))].filter(
    (s) => s !== "None",
  );
  if (leaves.length !== 1) return null;
  const leaf = leaves[0];
  return leaf === "int" || leaf === "float" || leaf === "bool" || leaf === "str"
    ? leaf
    : null;
}

export type FilterField =
  | { kind: "range"; label: string; datatype: string; min: number | null; max: number | null }
  | { kind: "toggle"; label: string; datatype: string }
  | {
      kind: "checklist";
      label: string;
      datatype: string;
      options: { value: string; count: number }[];
    };

export function deriveFilterSchema(
  inputs: Annotation[],
  executions: ExecutionResultMetadata[],
): FilterField[] {
  const valuesByLabel = new Map<
    string,
    ExecutionResultMetadata["inputs"][number]["value"][]
  >();

  for (const execution of executions) {
    for (const input of execution.inputs) {
      const existing = valuesByLabel.get(input.label);
      if (existing) existing.push(input.value);
      else valuesByLabel.set(input.label, [input.value]);
    }
  }

  const valuesFor = (label: string) => valuesByLabel.get(label) ?? [];
  const fields: FilterField[] = [];
  for (const input of inputs) {
    if (!input.label || !input.datatype) continue;
    const kind = classifyScalarDatatype(input.datatype);
    if (!kind) continue;

    const raw = valuesFor(input.label);

    if (kind === "int" || kind === "float") {
      const numeric = raw.filter((v): v is number => typeof v === "number");
      fields.push({
        kind: "range",
        label: input.label,
        datatype: input.datatype,
        min: numeric.length ? Math.min(...numeric) : null,
        max: numeric.length ? Math.max(...numeric) : null,
      });
    } else if (kind === "bool") {
      fields.push({ kind: "toggle", label: input.label, datatype: input.datatype });
    } else {
      const strings = raw.filter((v): v is string => typeof v === "string");
      const counts = new Map<string, number>();
      for (const s of strings) counts.set(s, (counts.get(s) ?? 0) + 1);
      fields.push({
        kind: "checklist",
        label: input.label,
        datatype: input.datatype,
        options: [...counts.entries()]
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([value, count]) => ({ value, count })),
      });
    }
  }
  return fields;
}

export type FilterValue =
  | { kind: "range"; label: string; min: number | null; max: number | null }
  | { kind: "toggle"; label: string; value: boolean }
  | { kind: "checklist"; label: string; values: string[] };

function valueFor(execution: ExecutionResultMetadata, label: string) {
  return execution.inputs.find((v) => v.label === label)?.value;
}

function matchesFilter(execution: ExecutionResultMetadata, filter: FilterValue): boolean {
  const value = valueFor(execution, filter.label);
  if (filter.kind === "range") {
    if (typeof value !== "number") return false;
    if (filter.min !== null && value < filter.min) return false;
    return !(filter.max !== null && value > filter.max);
  }
  if (filter.kind === "toggle") {
    return typeof value === "boolean" && value === filter.value;
  }
  return value !== undefined && filter.values.includes(String(value)); // checklist
}

export function filterExecutions(
  executions: ExecutionResultMetadata[],
  filters: FilterValue[],
): ExecutionResultMetadata[] {
  return executions.filter((e) => filters.every((f) => matchesFilter(e, f)));
}

export function sortExecutions(
  executions: ExecutionResultMetadata[],
  sort: "newest" | "oldest",
): ExecutionResultMetadata[] {
  return [...executions].sort((a, b) => {
    const diff =
      new Date(a.creation_timestamp).getTime() - new Date(b.creation_timestamp).getTime();
    return sort === "newest" ? -diff : diff;
  });
}
