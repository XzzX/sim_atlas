import React, { useState } from "react";
import {
  NodeType,
  FilterOptions,
  ScoredSearchResponse,
  Filter,
} from "../types/index";
import { Funnel, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  CollapsibleContent,
  CollapsibleRoot,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Label } from "./ui/label";

interface FacetedSearchProps {
  nodes: ScoredSearchResponse[];
  filters: Filter;
  availableFilterOptions: FilterOptions;
  onFilterChange: (filters: Filter) => void;
  onClearFilters: () => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  filters,
  availableFilterOptions,
  onFilterChange,
  onClearFilters,
}) => {
  return (
    <CardContent className="space-y-4">
      <Label>Facet Filters</Label>
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
            onFilterChange({
              ...filters,
              author: values,
            })
          }
        />
        <FacetPopover
          label="Keywords"
          values={availableFilterOptions.keywords ?? []}
          selected={filters.keywords ?? []}
          onValueChange={(values) =>
            onFilterChange({
              ...filters,
              keywords: values,
            })
          }
        />
        <FacetPopover
          label="Datatype"
          values={availableFilterOptions.datatypes ?? []}
          selected={filters.datatypes ?? []}
          onValueChange={(values) =>
            onFilterChange({
              ...filters,
              datatypes: values,
            })
          }
        />
        <FacetPopover
          label="Unit"
          values={availableFilterOptions.units ?? []}
          selected={filters.units ?? []}
          onValueChange={(values) =>
            onFilterChange({
              ...filters,
              units: values,
            })
          }
        />
        <FacetPopover
          label="Quantity"
          values={availableFilterOptions.quantities ?? []}
          selected={filters.quantities ?? []}
          onValueChange={(values) =>
            onFilterChange({
              ...filters,
              quantities: values,
            })
          }
        />
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
