import React from "react";
import type { Filter, FilterOptions } from "../types/index";

// ── Chip category helper (mirrors ResultsTable) ────────────────────────────────

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

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="mb-2 text-[9.5px] font-semibold uppercase tracking-[.08em]"
      style={{ color: "var(--node-th-fg)" }}
    >
      {children}
    </p>
  );
}

function TypeRow({
  label,
  dot,
  active,
  onClick,
}: {
  label: string;
  dot?: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-[6px] rounded-md px-[10px] py-[6px] text-left text-[12.5px] transition-colors duration-[120ms] ${
        active
          ? "border border-border/60 bg-card font-medium text-foreground"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      {dot && (
        <span
          className="size-[5px] shrink-0 rounded-full"
          style={{ background: dot }}
        />
      )}
      {label}
    </button>
  );
}

// ── PORT_OPTIONS ────────────────────────────────────────────────────────────────

const PORT_OPTIONS: { value: null | "inputs" | "outputs"; label: string }[] = [
  { value: null, label: "Both" },
  { value: "inputs", label: "In" },
  { value: "outputs", label: "Out" },
];

// ── FilterSidebar ──────────────────────────────────────────────────────────────

interface FilterSidebarProps {
  filters: Filter;
  availableFilterOptions: FilterOptions;
  onFilterChange: (filters: Filter) => void;
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  filters,
  availableFilterOptions,
  onFilterChange,
}) => {
  const selectedTypes = filters.artifact_type ?? [];

  const setType = (val: string) => {
    onFilterChange({
      ...filters,
      artifact_type: selectedTypes.includes(val) ? [] : [val],
    });
  };

  const authorValue = (filters.author ?? [])[0] ?? "";
  const setAuthor = (v: string) => {
    onFilterChange({ ...filters, author: v.trim() ? [v.trim()] : [] });
  };

  const selectedDatatypes = filters.datatypes ?? [];
  const toggleDatatype = (dt: string) => {
    const updated = selectedDatatypes.includes(dt)
      ? selectedDatatypes.filter((d) => d !== dt)
      : [...selectedDatatypes, dt];
    onFilterChange({ ...filters, datatypes: updated });
  };

  // Treat "both" and null both as the "no direction filter" state for display
  const effectivePortType =
    filters.port_type === "both" || !filters.port_type ? null : filters.port_type;

  const clearAll = () =>
    onFilterChange({
      ...filters,
      artifact_type: [],
      author: [],
      keywords: [],
      datatypes: [],
      units: [],
      quantities: [],
      port_type: null,
    });

  return (
    <div
      className="flex w-[185px] shrink-0 flex-col gap-[18px] overflow-y-auto border-r p-5"
      style={{ background: "var(--node-th-bg)" }}
    >
      {/* "FILTERS" heading */}
      <div
        className="text-[9.5px] font-bold uppercase tracking-[.12em]"
        style={{ color: "var(--node-th-fg)" }}
      >
        Filters
      </div>

      {/* NODE TYPE */}
      <section>
        <SectionLabel>Node Type</SectionLabel>
        <div className="flex flex-col gap-[3px]">
          <TypeRow
            label="All"
            active={selectedTypes.length === 0}
            onClick={() => onFilterChange({ ...filters, artifact_type: [] })}
          />
          <TypeRow
            label="Function"
            dot="#2563eb"
            active={selectedTypes.includes("function")}
            onClick={() => setType("function")}
          />
          <TypeRow
            label="Workflow"
            dot="#7c3aed"
            active={selectedTypes.includes("workflow")}
            onClick={() => setType("workflow")}
          />
        </div>
      </section>

      {/* AUTHOR */}
      <section>
        <SectionLabel>Author</SectionLabel>
        <input
          type="text"
          value={authorValue}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="any author…"
          className="w-full rounded-md border bg-background px-[10px] py-[7px] text-xs text-foreground placeholder:text-muted-foreground/60 outline-none transition-colors focus:border-ring"
        />
      </section>

      {/* DATATYPE */}
      {availableFilterOptions.datatypes.length > 0 && (
        <section>
          <SectionLabel>Datatype</SectionLabel>
          <div className="flex flex-wrap gap-1">
            {availableFilterOptions.datatypes.map((dt) => {
              const active = selectedDatatypes.includes(dt);
              const cat = chipCategory(dt);
              return (
                <button
                  key={dt}
                  type="button"
                  onClick={() => toggleDatatype(dt)}
                  className={`rounded-[4px] border px-2 py-[3px] font-mono text-[10.5px] leading-none transition-colors duration-[120ms] ${
                    active ? "" : "border-border text-muted-foreground hover:border-border/80 hover:text-foreground"
                  }`}
                  style={
                    active
                      ? {
                          background: `var(--chip-${cat}-bg)`,
                          color: `var(--chip-${cat}-fg)`,
                          borderColor: `var(--chip-${cat}-bd)`,
                        }
                      : undefined
                  }
                >
                  {dt}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* DIRECTION */}
      <section>
        <SectionLabel>Direction</SectionLabel>
        <div className="flex gap-[3px]">
          {PORT_OPTIONS.map(({ value, label }) => {
            const active = effectivePortType === value;
            return (
              <button
                key={label}
                type="button"
                onClick={() => onFilterChange({ ...filters, port_type: value })}
                className={`flex-1 rounded-[5px] py-[5px] text-center text-[11px] font-medium transition-colors duration-[120ms] ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </section>

      {/* Clear all */}
      <div className="mt-auto border-t pt-4">
        <button
          type="button"
          onClick={clearAll}
          className="text-xs text-destructive transition-colors hover:text-destructive/70"
        >
          Clear all
        </button>
      </div>
    </div>
  );
};
