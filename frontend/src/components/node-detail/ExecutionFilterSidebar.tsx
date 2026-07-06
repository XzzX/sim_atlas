import React from "react";
import { SlidersHorizontalIcon } from "lucide-react";
import { DatatypeBadge } from "@/components/DatatypeBadge";
import { Checkbox } from "@/components/ui/checkbox";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Slider, SliderControl, SliderTrack, SliderIndicator, SliderThumb } from "@/components/ui/slider";
import type { FilterField, FilterValue } from "@/lib/executionFilters";

interface ExecutionFilterSidebarProps {
  fields: FilterField[];
  activeFilters: FilterValue[];
  onFiltersChange: (filters: FilterValue[]) => void;
}

function upsert(filters: FilterValue[], value: FilterValue): FilterValue[] {
  return [...filters.filter((f) => f.label !== value.label), value];
}

function remove(filters: FilterValue[], label: string): FilterValue[] {
  return filters.filter((f) => f.label !== label);
}

function FieldLabel({ label, datatype }: { label: string; datatype: string }) {
  return (
    <div className="flex items-center gap-[5px]">
      <span className="size-[6px] shrink-0 rounded-full" style={{ background: "var(--node-dot-input)" }} />
      <span className="font-mono text-[11.5px] font-medium text-foreground">{label}</span>
      <DatatypeBadge datatype={datatype} />
    </div>
  );
}

function RangeFilterControl({
  field,
  activeFilters,
  onFiltersChange,
}: {
  field: Extract<FilterField, { kind: "range" }>;
  activeFilters: FilterValue[];
  onFiltersChange: (filters: FilterValue[]) => void;
}) {
  if (field.min === null || field.max === null) {
    return (
      <div className="space-y-1.5">
        <FieldLabel label={field.label} datatype={field.datatype} />
        <p className="text-[11px] text-muted-foreground">No executions yet</p>
      </div>
    );
  }

  const active = activeFilters.find(
    (f): f is Extract<FilterValue, { kind: "range" }> => f.kind === "range" && f.label === field.label,
  );
  const value: [number, number] = [active?.min ?? field.min, active?.max ?? field.max];

  return (
    <div className="space-y-1.5">
      <FieldLabel label={field.label} datatype={field.datatype} />
      <Slider
        min={field.min}
        max={field.max}
        value={value}
        onValueChange={(next) => {
          const [min, max] = next as number[];
          if (min === field.min && max === field.max) {
            onFiltersChange(remove(activeFilters, field.label));
          } else {
            onFiltersChange(upsert(activeFilters, { kind: "range", label: field.label, min, max }));
          }
        }}
      >
        <SliderControl>
          <SliderTrack>
            <SliderIndicator />
            <SliderThumb index={0} />
            <SliderThumb index={1} />
          </SliderTrack>
        </SliderControl>
      </Slider>
      <div className="flex justify-between font-mono text-[10.5px] text-muted-foreground">
        <span>{value[0]}</span>
        <span>{value[1]}</span>
      </div>
    </div>
  );
}

function ToggleFilterControl({
  field,
  activeFilters,
  onFiltersChange,
}: {
  field: Extract<FilterField, { kind: "toggle" }>;
  activeFilters: FilterValue[];
  onFiltersChange: (filters: FilterValue[]) => void;
}) {
  const active = activeFilters.find(
    (f): f is Extract<FilterValue, { kind: "toggle" }> => f.kind === "toggle" && f.label === field.label,
  );
  const current = active === undefined ? "any" : String(active.value);

  return (
    <div className="space-y-1.5">
      <FieldLabel label={field.label} datatype={field.datatype} />
      <ToggleGroup
        value={[current]}
        onValueChange={(next) => {
          const selected = next[0];
          if (!selected || selected === "any") {
            onFiltersChange(remove(activeFilters, field.label));
          } else {
            onFiltersChange(
              upsert(activeFilters, { kind: "toggle", label: field.label, value: selected === "true" }),
            );
          }
        }}
        className="bg-muted"
      >
        <ToggleGroupItem value="any" size="sm">Any</ToggleGroupItem>
        <ToggleGroupItem value="true" size="sm">True</ToggleGroupItem>
        <ToggleGroupItem value="false" size="sm">False</ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}

function ChecklistFilterControl({
  field,
  activeFilters,
  onFiltersChange,
}: {
  field: Extract<FilterField, { kind: "checklist" }>;
  activeFilters: FilterValue[];
  onFiltersChange: (filters: FilterValue[]) => void;
}) {
  const active = activeFilters.find(
    (f): f is Extract<FilterValue, { kind: "checklist" }> => f.kind === "checklist" && f.label === field.label,
  );
  const selected = new Set(active?.values ?? []);

  const toggle = (optionValue: string, checked: boolean) => {
    const next = new Set(selected);
    if (checked) next.add(optionValue);
    else next.delete(optionValue);
    if (next.size === 0) {
      onFiltersChange(remove(activeFilters, field.label));
    } else {
      onFiltersChange(upsert(activeFilters, { kind: "checklist", label: field.label, values: [...next] }));
    }
  };

  return (
    <div className="space-y-1.5">
      <FieldLabel label={field.label} datatype={field.datatype} />
      <div className="space-y-1">
        {field.options.map((option) => (
          <label key={option.value} className="flex cursor-pointer items-center gap-2 text-[12px]">
            <Checkbox
              checked={selected.has(option.value)}
              onCheckedChange={(checked) => toggle(option.value, checked)}
            />
            <span className="flex-1 truncate text-foreground">{option.value}</span>
            <span className="font-mono text-[10.5px] text-muted-foreground">{option.count}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

export const ExecutionFilterSidebar: React.FC<ExecutionFilterSidebarProps> = ({
  fields,
  activeFilters,
  onFiltersChange,
}) => {
  return (
    <div className="w-[262px] shrink-0 space-y-5 border-r px-5 py-5" style={{ background: "var(--sidebar)" }}>
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">
          <SlidersHorizontalIcon className="size-3.5" />
          Filters
        </span>
        {activeFilters.length > 0 && (
          <button
            type="button"
            onClick={() => onFiltersChange([])}
            className="text-[12px] font-medium"
            style={{ color: "var(--node-detail-accent)" }}
          >
            Clear all
          </button>
        )}
      </div>

      {fields.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">This node has no filterable inputs.</p>
      ) : (
        fields.map((field) => (
          <React.Fragment key={field.label}>
            {field.kind === "range" && (
              <RangeFilterControl field={field} activeFilters={activeFilters} onFiltersChange={onFiltersChange} />
            )}
            {field.kind === "toggle" && (
              <ToggleFilterControl field={field} activeFilters={activeFilters} onFiltersChange={onFiltersChange} />
            )}
            {field.kind === "checklist" && (
              <ChecklistFilterControl field={field} activeFilters={activeFilters} onFiltersChange={onFiltersChange} />
            )}
          </React.Fragment>
        ))
      )}
    </div>
  );
};
