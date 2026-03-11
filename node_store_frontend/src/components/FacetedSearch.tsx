import React, { useMemo, useState } from "react";
import { NodeType, FilterOptions, ScoredSearchResponse } from "../types/index";
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
  filters: FilterOptions;
  onFilterChange: (filters: FilterOptions) => void;
  onClearFilters: () => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  nodes,
  filters,
  onFilterChange,
  onClearFilters,
}) => {
  const [showFilters, setShowFilters] = useState(true);

  // Calculate available facet values based on current nodes
  const facets = useMemo(() => {
    const result = {
      nodeTypes: new Map<NodeType, number>(),
      authors: new Map<string, number>(),
      keywords: new Map<string, number>(),
      inputDatatypes: new Map<string, number>(),
      outputDatatypes: new Map<string, number>(),
    };

    nodes.forEach((node) => {
      // Count by node type
      result.nodeTypes.set(
        node.node.node_type,
        (result.nodeTypes.get(node.node.node_type) || 0) + 1,
      );

      // Count by author
      result.authors.set(
        node.node.author_name,
        (result.authors.get(node.node.author_name) || 0) + 1,
      );

      // Count by keywords
      if (node.node.keywords) {
        node.node.keywords.forEach((keyword) => {
          result.keywords.set(keyword, (result.keywords.get(keyword) || 0) + 1);
        });
      }

      // Count by input datatype
      node.node.inputs.forEach((input) => {
        if (input.datatype) {
          result.inputDatatypes.set(
            input.datatype,
            (result.inputDatatypes.get(input.datatype) || 0) + 1,
          );
        }
      });

      // Count by output datatype
      node.node.outputs.forEach((output) => {
        if (output.datatype) {
          result.outputDatatypes.set(
            output.datatype,
            (result.outputDatatypes.get(output.datatype) || 0) + 1,
          );
        }
      });
    });

    return result;
  }, [nodes]);

  const activeFilterCount = [
    filters.type?.length || 0,
    filters.author?.length || 0,
    filters.keywords?.length || 0,
    filters.inputDatatype?.length || 0,
    filters.outputDatatype?.length || 0,
  ].reduce((a, b) => a + b, 0);

  const nodeTypeOptions = Array.from(facets.nodeTypes.keys()).sort((a, b) =>
    a.localeCompare(b),
  );
  const authorOptions = Array.from(facets.authors.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([author]) => author);
  const keywordOptions = Array.from(facets.keywords.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([keyword]) => keyword);
  const inputDatatypeOptions = Array.from(facets.inputDatatypes.keys()).sort(
    (a, b) => a.localeCompare(b),
  );
  const outputDatatypeOptions = Array.from(facets.outputDatatypes.keys()).sort(
    (a, b) => a.localeCompare(b),
  );

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
              <p className="text-sm text-muted-foreground">
                {activeFilterCount} active filters
              </p>
              {activeFilterCount > 0 && (
                <Button variant="ghost" size="sm" onClick={onClearFilters}>
                  <X className="mr-1 size-4" />
                  Clear all
                </Button>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <FacetPopover
                label="Node Type"
                values={nodeTypeOptions}
                selected={(filters.type || []).map((value) => String(value))}
                counts={(value) => facets.nodeTypes.get(value as NodeType) || 0}
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
                counts={(value) => facets.authors.get(value) || 0}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, author: values })
                }
              />
              <FacetPopover
                label="Keywords"
                values={keywordOptions}
                selected={filters.keywords || []}
                counts={(value) => facets.keywords.get(value) || 0}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, keywords: values })
                }
              />
              <FacetPopover
                label="Input Type"
                values={inputDatatypeOptions}
                selected={filters.inputDatatype || []}
                counts={(value) => facets.inputDatatypes.get(value) || 0}
                onValueChange={(values) =>
                  onFilterChange({ ...filters, inputDatatype: values })
                }
              />
              <FacetPopover
                label="Output Type"
                values={outputDatatypeOptions}
                selected={filters.outputDatatype || []}
                counts={(value) => facets.outputDatatypes.get(value) || 0}
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
  counts: (value: string) => number;
  onValueChange: (values: string[]) => void;
}

function FacetPopover({
  label,
  values,
  selected,
  counts,
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
                  <span className="text-xs text-muted-foreground">
                    {counts(item)}
                  </span>
                </div>
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </div>
  );
}
