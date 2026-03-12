import React, { useMemo, useState } from "react";
import {
  NodeType,
  FilterOptions,
  SearchFilters,
  ScoredSearchResponse,
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
  filters: SearchFilters;
  availableFilterOptions: FilterOptions;
  onFilterChange: (filters: SearchFilters) => void;
  onClearFilters: () => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  nodes,
  filters,
  availableFilterOptions,
  onFilterChange,
  onClearFilters,
}) => {
  const [showFilters, setShowFilters] = useState(true);

  const nodeTypeOptions = availableFilterOptions.type
    .slice()
    .sort((a, b) => a.localeCompare(b));
  const authorOptions = availableFilterOptions.author.slice().sort();
  const keywordOptions = availableFilterOptions.keywords.slice().sort();
  const inputDatatypeOptions: string[] = [];
  const outputDatatypeOptions: string[] = [];

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
                values={nodeTypeOptions}
                selected={(filters.type || []).map((value) => String(value))}
                onValueChange={(values) =>
                  onFilterChange({
                    ...filters,
                    type: values.filter((v) =>
                      Object.values(NodeType).includes(v as NodeType),
                    ) as NodeType[],
                  })
                }
              />
              <FacetPopover
                label="Author"
                values={authorOptions}
                selected={filters.author || []}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, author: values })
                }
              />
              <FacetPopover
                label="Keywords"
                values={keywordOptions}
                selected={filters.keywords || []}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, keywords: values })
                }
              />
              <FacetPopover
                label="Input Type"
                values={inputDatatypeOptions}
                selected={filters.inputDatatype || []}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, inputDatatype: values })
                }
              />
              <FacetPopover
                label="Output Type"
                values={outputDatatypeOptions}
                selected={filters.outputDatatype || []}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, outputDatatype: values })
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
