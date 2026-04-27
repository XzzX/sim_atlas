import React from "react";
import type { NodeType, FilterOptions, Filter } from "../types/index";
import { CardContent } from "@/components/ui/card";
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
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { ArrowDownToLine, ArrowUpDown, ArrowUpFromLine } from "lucide-react";

const PORT_OPTIONS = [
  { value: null, Icon: ArrowUpDown, label: "Both" },
  { value: "inputs" as const, Icon: ArrowDownToLine, label: "Inputs" },
  { value: "outputs" as const, Icon: ArrowUpFromLine, label: "Outputs" },
];

interface FacetedSearchProps {
  filters: Filter;
  availableFilterOptions: FilterOptions;
  onFilterChange: (filters: Filter) => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  filters,
  availableFilterOptions,
  onFilterChange,
}) => {
  return (
    <CardContent className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Facet Filters</Label>
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            onFilterChange({
              ...filters,
              type: [],
              author: [],
              keywords: [],
              datatypes: [],
              units: [],
              quantities: [],
              port_type: null,
            })
          }
        >
          Clear all
        </Button>
      </div>

      {/* General filters */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <FacetPopover
          label="Node Type"
          values={availableFilterOptions.type.map((t) => String(t))}
          selected={(filters.type ?? []).map((value) => String(value))}
          onValueChange={(values) =>
            onFilterChange({ ...filters, type: values as NodeType[] })
          }
        />
        <FacetPopover
          label="Author"
          values={availableFilterOptions.author}
          selected={filters.author ?? []}
          onValueChange={(values) =>
            onFilterChange({ ...filters, author: values })
          }
        />
        <FacetPopover
          label="Keywords"
          values={availableFilterOptions.keywords ?? []}
          selected={filters.keywords ?? []}
          onValueChange={(values) =>
            onFilterChange({ ...filters, keywords: values })
          }
        />
      </div>

      {/* Annotation filters — port direction scopes all three */}
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Annotations
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Direction
            </p>
            <div className="flex overflow-hidden rounded border text-xs h-[34px]">
              {PORT_OPTIONS.map(({ value, Icon, label }, i) => {
                const active = (filters.port_type ?? null) === value;
                return (
                  <button
                    key={label}
                    type="button"
                    title={label}
                    onClick={() =>
                      onFilterChange({ ...filters, port_type: value })
                    }
                    className={[
                      "flex flex-1 items-center justify-center gap-1 px-2 py-1 transition-colors",
                      i > 0 ? "border-l" : "",
                      active
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted",
                    ].join(" ")}
                  >
                    <Icon className="size-3" />
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <FacetPopover
            label="Datatype"
            values={availableFilterOptions.datatypes ?? []}
            selected={filters.datatypes ?? []}
            onValueChange={(values) =>
              onFilterChange({ ...filters, datatypes: values })
            }
          />
          <FacetPopover
            label="Unit"
            values={availableFilterOptions.units ?? []}
            selected={filters.units ?? []}
            onValueChange={(values) =>
              onFilterChange({ ...filters, units: values })
            }
          />
          <FacetPopover
            label="Quantity"
            values={availableFilterOptions.quantities ?? []}
            selected={filters.quantities ?? []}
            onValueChange={(values) =>
              onFilterChange({ ...filters, quantities: values })
            }
          />
        </div>
      </div>
    </CardContent>
  );
};

interface FacetPopoverProps {
  label: string;
  values: string[];
  selected: string[];
  onValueChange: (values: string[]) => void;
}

function FacetPopover({
  label,
  values,
  selected,
  onValueChange,
}: FacetPopoverProps) {
  const anchor = useComboboxAnchor();

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <Combobox
        multiple
        autoHighlight
        items={values}
        value={selected}
        onValueChange={onValueChange}
      >
        <ComboboxChips ref={anchor} className="w-full">
          <ComboboxValue>
            {(selectedValues: string[]) => (
              <React.Fragment>
                {selectedValues.map((value: string) => (
                  <ComboboxChip key={value}>{value}</ComboboxChip>
                ))}
                <ComboboxChipsInput
                  placeholder={`Search ${label.toLowerCase()}...`}
                />
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
    </div>
  );
}
