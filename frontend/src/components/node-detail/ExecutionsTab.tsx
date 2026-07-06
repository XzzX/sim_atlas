import React, { useMemo, useState } from "react";
import { XIcon, ChevronDownIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationPrevious,
  PaginationNext,
} from "@/components/ui/pagination";
import { ExecutionFilterSidebar } from "./ExecutionFilterSidebar";
import { ExecutionRunRow } from "./ExecutionRunRow";
import { RunDetailDrawer } from "./RunDetailDrawer";
import { deriveFilterSchema, filterExecutions, sortExecutions, type FilterValue } from "@/lib/executionFilters";
import type { Annotation, ExecutionResultMetadata } from "@/types/index";

const PAGE_SIZE = 10;

function describeFilter(filter: FilterValue): string {
  if (filter.kind === "range") {
    return `${filter.label}: ${filter.min ?? "…"}–${filter.max ?? "…"}`;
  }
  if (filter.kind === "toggle") {
    return `${filter.label}: ${filter.value ? "True" : "False"}`;
  }
  return `${filter.label}: ${filter.values.join(", ")}`;
}

function RunListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-xl bg-muted" />
      ))}
    </div>
  );
}

interface ExecutionsTabProps {
  inputs: Annotation[];
  executions: ExecutionResultMetadata[];
  loading: boolean;
  error: string | null;
  drawerContainer: HTMLElement | null;
}

export const ExecutionsTab: React.FC<ExecutionsTabProps> = ({
  inputs,
  executions,
  loading,
  error,
  drawerContainer,
}) => {
  const [filters, setFilters] = useState<FilterValue[]>([]);
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);
  const [selectedExecution, setSelectedExecution] = useState<ExecutionResultMetadata | null>(null);

  const filterSchema = useMemo(() => deriveFilterSchema(inputs, executions), [inputs, executions]);
  const filtered = useMemo(() => filterExecutions(executions, filters), [executions, filters]);
  const sorted = useMemo(() => sortExecutions(filtered, sort), [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * PAGE_SIZE;
  const paged = sorted.slice(start, start + PAGE_SIZE);

  const updateFilters = (next: FilterValue[]) => {
    setFilters(next);
    setPage(1);
  };

  const updateSort = (next: "newest" | "oldest") => {
    setSort(next);
    setPage(1);
  };

  if (loading) {
    return (
      <div className="flex">
        <div className="w-[262px] shrink-0 animate-pulse border-r" style={{ background: "var(--sidebar)" }} />
        <div className="min-w-0 flex-1 px-7 py-5">
          <RunListSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-8 py-6">
        <Alert variant="destructive">{error}</Alert>
      </div>
    );
  }

  return (
    <div className="flex">
      <ExecutionFilterSidebar fields={filterSchema} activeFilters={filters} onFiltersChange={updateFilters} />

      <div className="min-w-0 flex-1 px-7 py-5">
        <div className="flex items-center justify-between gap-4">
          <p className="text-[13px]">
            <span className="font-semibold text-foreground">{sorted.length}</span>{" "}
            <span className="text-muted-foreground">of {executions.length} executions</span>
          </p>
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex items-center gap-1 text-[12.5px] font-medium text-muted-foreground hover:text-foreground">
              {sort === "newest" ? "Newest" : "Oldest"}
              <ChevronDownIcon className="size-3.5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuRadioGroup value={sort} onValueChange={(v) => updateSort(v as "newest" | "oldest")}>
                <DropdownMenuRadioItem value="newest">Newest</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="oldest">Oldest</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {filters.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {filters.map((f) => (
              <span
                key={f.label}
                className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-medium"
                style={{ background: "var(--node-detail-hover-bd)", color: "var(--node-detail-accent)" }}
              >
                {describeFilter(f)}
                <button
                  type="button"
                  onClick={() => updateFilters(filters.filter((x) => x.label !== f.label))}
                  aria-label={`Remove ${f.label} filter`}
                >
                  <XIcon className="size-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div
          className="mt-4 grid gap-3 px-1 text-[9.5px] font-bold uppercase tracking-[.09em] text-muted-foreground"
          style={{ gridTemplateColumns: "150px 1fr 130px" }}
        >
          <span>Run</span>
          <span>Input parameters</span>
          <span className="text-right">Output</span>
        </div>

        {paged.length === 0 ? (
          <div className="mt-3">
            <Alert variant="info">
              {executions.length === 0
                ? "No executions recorded for this node yet."
                : "No executions match these filters."}
            </Alert>
          </div>
        ) : (
          <div className="mt-2 space-y-2">
            {paged.map((execution) => (
              <ExecutionRunRow
                key={execution.id}
                execution={execution}
                onClick={() => setSelectedExecution(execution)}
              />
            ))}
          </div>
        )}

        {sorted.length > 0 && (
          <div className="mt-4 flex items-center justify-between">
            <p className="text-[12px] text-muted-foreground">
              Showing {start + 1}–{Math.min(start + PAGE_SIZE, sorted.length)} of {sorted.length}
            </p>
            <Pagination className="mx-0 w-auto justify-end">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    aria-disabled={safePage <= 1}
                    tabIndex={safePage <= 1 ? -1 : undefined}
                    className={safePage <= 1 ? "pointer-events-none opacity-50" : ""}
                    onClick={(e) => {
                      e.preventDefault();
                      setPage(safePage - 1);
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  {safePage} / {totalPages}
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    aria-disabled={safePage >= totalPages}
                    tabIndex={safePage >= totalPages ? -1 : undefined}
                    className={safePage >= totalPages ? "pointer-events-none opacity-50" : ""}
                    onClick={(e) => {
                      e.preventDefault();
                      setPage(safePage + 1);
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </div>

      <RunDetailDrawer
        execution={selectedExecution}
        onClose={() => setSelectedExecution(null)}
        portalContainer={drawerContainer}
      />
    </div>
  );
};
