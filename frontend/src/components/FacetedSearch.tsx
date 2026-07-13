import React from "react";
import type { FilterOptions, Filter } from "../types/index";
import { CategoryTree } from "./CategoryTree";
import { Separator } from "@/components/ui/separator";
import {
  Combobox,
  ComboboxChips,
  ComboboxChip,
  ComboboxChipsInput,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxList,
  ComboboxValue,
  useComboboxAnchor,
} from "@/components/ui/combobox";

const PORT_OPTIONS = [
  { value: null, label: "Both" },
  { value: "inputs" as const, label: "In" },
  { value: "outputs" as const, label: "Out" },
];

interface FacetedSearchProps {
  filters: Filter;
  availableFilterOptions: FilterOptions;
  onFilterChange: (filters: Filter) => void;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}

function FacetCombobox({
  values,
  selected,
  onValueChange,
}: {
  label?: string;
  values: string[];
  selected: string[];
  onValueChange: (values: string[]) => void;
}) {
  const anchor = useComboboxAnchor();
  return (
    <Combobox multiple autoHighlight items={values} value={selected} onValueChange={onValueChange}>
      <ComboboxChips ref={anchor} className="w-full">
        <ComboboxValue>
          {(selectedValues: string[]) => (
            <React.Fragment>
              {selectedValues.map((v: string) => (
                <ComboboxChip key={v}>{v}</ComboboxChip>
              ))}
              <ComboboxChipsInput placeholder={selected.length === 0 ? "any" : ""} />
            </React.Fragment>
          )}
        </ComboboxValue>
      </ComboboxChips>
      <ComboboxContent anchor={anchor}>
        <ComboboxEmpty>No options</ComboboxEmpty>
        <ComboboxList>
          {(item: string) => (
            <ComboboxItem key={item} value={item}>
              {item}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  filters,
  availableFilterOptions,
  onFilterChange,
}) => {
  const selectedTypes = (filters.artifact_type ?? []).map(String);

  const toggleType = (val: string) => {
    const updated = selectedTypes.includes(val)
      ? selectedTypes.filter((t) => t !== val)
      : [...selectedTypes, val];
    onFilterChange({ ...filters, artifact_type: updated });
  };

  const typeBtn = (label: string, active: boolean, onClick: () => void) => (
    <button
      key={label}
      type="button"
      onClick={onClick}
      className={`w-full rounded-md border px-3 py-1.5 text-left text-sm capitalize transition-colors ${
        active
          ? "border-foreground font-medium"
          : "border-border text-muted-foreground hover:border-foreground/50 hover:text-foreground"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-5 px-4 py-3">
      {/* Category */}
      <div className="space-y-1.5">
        <SectionLabel>Category</SectionLabel>
        <CategoryTree
          category={filters.category ?? ""}
          categoryOptions={availableFilterOptions.category}
          onSelect={(category) => onFilterChange({ ...filters, category })}
        />
      </div>

      <Separator />

      {/* Node Type */}
      <div className="space-y-1.5">
        <SectionLabel>Node Type</SectionLabel>
        <div className="space-y-1">
          {typeBtn("All", selectedTypes.length === 0, () =>
            onFilterChange({ ...filters, artifact_type: [] }),
          )}
          {availableFilterOptions.artifact_type.map((t) => {
            const val = String(t);
            return typeBtn(val, selectedTypes.includes(val), () => toggleType(val));
          })}
        </div>
      </div>

      {/* Author */}
      <div className="space-y-1.5">
        <SectionLabel>Author</SectionLabel>
        <FacetCombobox
          label="Author"
          values={availableFilterOptions.author}
          selected={filters.author ?? []}
          onValueChange={(v) => onFilterChange({ ...filters, author: v })}
        />
      </div>

      {/* Keywords */}
      <div className="space-y-1.5">
        <SectionLabel>Keywords</SectionLabel>
        <FacetCombobox
          label="Keywords"
          values={availableFilterOptions.keywords ?? []}
          selected={filters.keywords ?? []}
          onValueChange={(v) => onFilterChange({ ...filters, keywords: v })}
        />
      </div>

      {/* Annotations */}
      <div className="space-y-3">
        <SectionLabel>Annotations</SectionLabel>

        <div className="space-y-1.5">
          <SectionLabel>Direction</SectionLabel>
          <div className="flex overflow-hidden rounded-md border text-xs">
            {PORT_OPTIONS.map(({ value, label }, i) => {
              const active = (filters.port_type ?? null) === value;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => onFilterChange({ ...filters, port_type: value })}
                  className={[
                    "flex flex-1 items-center justify-center py-1.5 transition-colors",
                    i > 0 ? "border-l" : "",
                    active
                      ? "bg-primary text-primary-foreground font-medium"
                      : "text-muted-foreground hover:bg-muted",
                  ].join(" ")}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-1.5">
          <SectionLabel>Datatype</SectionLabel>
          <FacetCombobox
            label="Datatype"
            values={availableFilterOptions.datatypes ?? []}
            selected={filters.datatypes ?? []}
            onValueChange={(v) => onFilterChange({ ...filters, datatypes: v })}
          />
        </div>

        <div className="space-y-1.5">
          <SectionLabel>Unit</SectionLabel>
          <FacetCombobox
            label="Unit"
            values={availableFilterOptions.units ?? []}
            selected={filters.units ?? []}
            onValueChange={(v) => onFilterChange({ ...filters, units: v })}
          />
        </div>

        <div className="space-y-1.5">
          <SectionLabel>Quantity</SectionLabel>
          <FacetCombobox
            label="Quantity"
            values={availableFilterOptions.quantities ?? []}
            selected={filters.quantities ?? []}
            onValueChange={(v) => onFilterChange({ ...filters, quantities: v })}
          />
        </div>
      </div>

      {/* Clear all */}
      <button
        type="button"
        onClick={() =>
          onFilterChange({
            ...filters,
            category: "",
            artifact_type: [],
            author: [],
            keywords: [],
            datatypes: [],
            units: [],
            quantities: [],
            port_type: null,
          })
        }
        className="w-full text-left text-sm underline underline-offset-2 text-muted-foreground hover:text-foreground transition-colors"
      >
        Clear all
      </button>
    </div>
  );
};
