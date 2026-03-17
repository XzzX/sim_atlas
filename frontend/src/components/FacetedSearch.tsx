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
  const [showFilters, setShowFilters] = useState(true);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Funnel className="size-4" />
          Filters
        </CardTitle>
        <CollapsibleRoot open={showFilters} onOpenChange={setShowFilters}>
          <CollapsibleTrigger render={<Button variant="outline" size="sm" />}>
            {showFilters ? "Hide" : "Show"}
          </CollapsibleTrigger>
        </CollapsibleRoot>
      </CardHeader>
      <CollapsibleRoot open={showFilters} onOpenChange={setShowFilters}>
        <CollapsibleContent>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Button variant="ghost" size="sm" onClick={onClearFilters}>
                <X className="mr-1 size-4" />
                Clear all
              </Button>
            </div>

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
        </CollapsibleContent>
      </CollapsibleRoot>
    </Card>
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
                <div className="flex items-center justify-between gap-2 w-full">
                  <span className="max-w-40 truncate">{item}</span>
                </div>
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </div>
  );
}
