import React, { useState } from "react";
import { SlidersHorizontalIcon, PanelLeftCloseIcon, PanelLeftOpenIcon } from "lucide-react";
import { Card, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { FacetedSearch } from "./FacetedSearch";
import type { Filter, FilterOptions } from "../types/index";

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
  const [open, setOpen] = useState(true);

  if (!open) {
    return (
      <div className="flex shrink-0 flex-col items-center pt-1">
        <button
          type="button"
          aria-label="Open filters"
          onClick={() => setOpen(true)}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelLeftOpenIcon className="size-4" />
        </button>
      </div>
    );
  }

  return (
    <Card className="w-56 shrink-0 overflow-hidden">
      <CardHeader className="border-b py-3">
        <CardTitle className="flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          <SlidersHorizontalIcon className="size-3.5" />
          Filters
        </CardTitle>
        <CardAction>
          <button
            type="button"
            aria-label="Close filters"
            onClick={() => setOpen(false)}
            className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <PanelLeftCloseIcon className="size-4" />
          </button>
        </CardAction>
      </CardHeader>
      <div className="overflow-y-auto">
        <FacetedSearch
          filters={filters}
          availableFilterOptions={availableFilterOptions}
          onFilterChange={onFilterChange}
        />
      </div>
    </Card>
  );
};
