type ChipCat = "domain" | "prim" | "num" | "df" | "coll" | "arr" | "union";

function chipCategory(datatype: string): ChipCat {
  const t = datatype.trim();
  if (t.startsWith("Union[") || t.startsWith("Optional[")) return "union";
  if (t.includes("|")) {
    const base = t.split("|")[0].trim();
    if (["float", "int", "complex"].includes(base)) return "num";
    if (["str", "bool", "bytes"].includes(base)) return "prim";
    return "union";
  }
  if (["float", "int", "complex"].includes(t)) return "num";
  if (["str", "bool", "bytes", "NoneType", "None"].includes(t)) return "prim";
  if (t === "DataFrame" || t.includes("DataFrame")) return "df";
  if (t === "ndarray" || t === "np.ndarray" || t.includes("ndarray")) return "arr";
  if (
    t.startsWith("list") || t.startsWith("List") ||
    t.startsWith("dict") || t.startsWith("Dict") ||
    t.startsWith("set")  || t.startsWith("Set")  ||
    t.startsWith("tuple")|| t.startsWith("Tuple")
  ) return "coll";
  if (/^[A-Z]/.test(t)) return "domain";
  return "prim";
}

function displayType(datatype: string): string {
  const t = datatype.trim();
  if (t.startsWith("Union[") && t.length > 12) return "Union[…]";
  return t;
}

export function DatatypeBadge({ datatype }: { datatype: string }) {
  const full = datatype.trim();
  const display = displayType(full);
  const cat = chipCategory(full);
  return (
    <span
      title={full !== display ? full : undefined}
      style={{
        background: `var(--chip-${cat}-bg)`,
        color: `var(--chip-${cat}-fg)`,
        border: `1px solid var(--chip-${cat}-bd)`,
      }}
      className="shrink-0 rounded-[4px] px-1.5 py-px font-mono text-[10px] leading-none"
    >
      {display}
    </span>
  );
}
