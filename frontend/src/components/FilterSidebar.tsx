import React, { useState } from "react";
import { PanelLeftCloseIcon, PanelLeftOpenIcon, SlidersHorizontalIcon } from "lucide-react";
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
      <div
        className="flex w-10 shrink-0 flex-col items-center border-r py-3"
        style={{ background: "var(--node-th-bg)" }}
      >
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
    <div
      className="flex w-[185px] shrink-0 flex-col border-r"
      style={{ background: "var(--node-th-bg)" }}
    >
      <div
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor: "var(--border)" }}
      >
        <span
          className="flex items-center gap-1.5 text-[9.5px] font-bold uppercase tracking-[.12em]"
          style={{ color: "var(--node-th-fg)" }}
        >
          <SlidersHorizontalIcon className="size-3.5" />
          Filters
        </span>
        <button
          type="button"
          aria-label="Close filters"
          onClick={() => setOpen(false)}
          className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelLeftCloseIcon className="size-4" />
        </button>
      </div>
      <div className="overflow-y-auto">
        <FacetedSearch
          filters={filters}
          availableFilterOptions={availableFilterOptions}
          onFilterChange={onFilterChange}
        />
      </div>
    </div>
  );
};
