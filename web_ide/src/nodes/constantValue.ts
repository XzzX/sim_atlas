/**
 * A constant node's value is held as JSON text, so `"1"` (a string) and `1`
 * (a number) stay distinct and a half-typed value can sit in the editor.
 */
export type ParsedConstant = { ok: true; value: unknown } | { ok: false };

export function parseConstant(text: string): ParsedConstant {
  try {
    return { ok: true, value: JSON.parse(text) as unknown };
  } catch {
    return { ok: false };
  }
}

/** The JSON type of a parsed value, as shown on the node. */
export function constantType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "list";
  return typeof value;
}

/**
 * The value an export emits for a constant: the parsed JSON, or the raw text
 * when it is empty or not JSON, which is reported in *errors*.
 */
export function exportedConstant(label: string, text: string, errors: string[]): unknown {
  if (text.trim() === "") {
    errors.push(`Constant "${label}" has no value.`);
    return text;
  }
  const parsed = parseConstant(text);
  if (parsed.ok) return parsed.value;
  errors.push(`Constant "${label}" is not valid JSON: ${text}`);
  return text;
}
