import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import { simAtlasAPI } from "../services/api";
import type { Filter, FilterOptions, ScoredSearchResponse } from "../types/index";
import { ResultsTable, Legend } from "../components/ResultsTable";
import { FilterSidebar } from "../components/FilterSidebar";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { ChevronsLeftIcon, ChevronsRightIcon } from "lucide-react";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import SearchBar from "@/components/SearchBar";
import { Toaster } from "@/components/ui/sonner";

function filtersToParams(
  extra: Record<string, string>,
  f: Filter,
): Record<string, string | string[]> {
  const { category, artifact_type, author, keywords, datatypes, units, quantities, port_type } = f;
  return {
    ...extra,
    ...(category ? { category } : {}),
    ...(artifact_type ? { artifact_type } : {}),
    ...(author ? { author } : {}),
    ...(keywords ? { keywords } : {}),
    ...(datatypes ? { datatypes } : {}),
    ...(units ? { units } : {}),
    ...(quantities ? { quantities } : {}),
    ...(port_type ? { port_type } : {}),
  };
}

const EMPTY_FILTER: Filter = {
  category: "",
  artifact_type: [],
  author: [],
  keywords: [],
  datatypes: [],
  units: [],
  quantities: [],
  port_type: "both",
};

const EMPTY_FILTER_OPTIONS: FilterOptions = {
  category: {},
  artifact_type: [],
  author: [],
  keywords: [],
  datatypes: [],
  units: [],
  quantities: [],
};

interface SearchPageProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const SearchPage: React.FC<SearchPageProps> = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [filters, setFilters] = useState<Filter>({
    category: searchParams.get("category") ?? EMPTY_FILTER.category,
    artifact_type: searchParams.getAll("artifact_type"),
    author: searchParams.getAll("author"),
    keywords: searchParams.getAll("keywords"),
    datatypes: searchParams.getAll("datatypes"),
    units: searchParams.getAll("units"),
    quantities: searchParams.getAll("quantities"),
    port_type:
      (searchParams.get("port_type") as "inputs" | "outputs" | "both" | null) ?? "both",
  });

  const [searchResponse, setSearchResponse] = useState<ScoredSearchResponse>({
    results: { data: [], page: 1, limit: 10, total_items: 0, total_pages: 0 },
    aggregations: null,
  });
  const [availableFilterOptions, setAvailableFilterOptions] =
    useState<FilterOptions>(EMPTY_FILTER_OPTIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedSearch = useDebouncedCallback(
    // eslint-disable-next-line @typescript-eslint/no-inferrable-types
    async (q: string, f: Filter, page: number = 1) => {
      try {
        setLoading(true);
        setError(null);
        const results = await simAtlasAPI.search(q, f, page);
        setSearchResponse(results);
      } catch (err) {
        setError("Search failed. Please try again.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    },
    500,
  );

  useEffect(() => {
    void debouncedSearch(query, filters, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const options = await simAtlasAPI.getFilterOptions();
        setAvailableFilterOptions(options);
      } catch (err) {
        console.error("Failed to fetch filter options", err);
      }
    };
    void load();
  }, []);

  const updateQuery = (v: string) => {
    setQuery(v);
    setSearchParams(filtersToParams({ q: v }, filters));
    void debouncedSearch(v, filters);
  };

  const updateFilters = (v: Filter) => {
    setFilters(v);
    setSearchParams(filtersToParams({ q: query }, v));
    void debouncedSearch(query, v);
  };

  const goToPage = (page: number) => {
    void debouncedSearch(query, filters, page);
  };

  const { page, total_pages: totalPages, total_items: totalItems } = searchResponse.results;
  const suggestions = searchResponse.results.data.map((r) => r.node.name);
  const searchPlaceholder = filters.category
    ? `Search within ${filters.category.split(">").join(" › ")}…`
    : undefined;

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Card className="overflow-hidden">
        <CardHeader className="border-b">
          <CardTitle>Simulation Atlas</CardTitle>
          <CardDescription>
            Search and discover nodes and workflows across your projects.
          </CardDescription>
        </CardHeader>

        <SearchBar
          query={query}
          onQueryChange={updateQuery}
          items={suggestions}
          placeholder={searchPlaceholder}
        />

        <div className="flex border-t">
          <FilterSidebar
            filters={filters}
            availableFilterOptions={availableFilterOptions}
            onFilterChange={updateFilters}
          />

          <div className="flex min-w-0 flex-1 flex-col">
            {/* toolbar: result count + legend + pagination */}
            <div className="flex items-center justify-between gap-4 border-b bg-muted/30 px-4 py-2">
              <div className="flex items-center gap-4">
                <p className="text-sm text-muted-foreground">
                  {totalItems} result{totalItems === 1 ? "" : "s"}
                </p>
                <Legend />
              </div>
              <Pagination className="mx-0 w-auto justify-end">
                <PaginationContent>
                  <PaginationItem>
                    <PaginationLink
                      href="#"
                      size="default"
                      aria-label="Go to first page"
                      aria-disabled={page <= 1}
                      tabIndex={page <= 1 ? -1 : undefined}
                      className={`pl-1.5! ${page <= 1 ? "pointer-events-none opacity-50" : ""}`}
                      onClick={(e) => { e.preventDefault(); goToPage(1); }}
                    >
                      <ChevronsLeftIcon data-icon="inline-start" />
                      <span className="hidden sm:block">First</span>
                    </PaginationLink>
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      aria-disabled={page <= 1}
                      tabIndex={page <= 1 ? -1 : undefined}
                      className={page <= 1 ? "pointer-events-none opacity-50" : ""}
                      onClick={(e) => { e.preventDefault(); goToPage(page - 1); }}
                    />
                  </PaginationItem>
                  <PaginationItem>
                    {page} / {Math.max(totalPages, 1)}
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      aria-disabled={page >= totalPages}
                      tabIndex={page >= totalPages ? -1 : undefined}
                      className={page >= totalPages ? "pointer-events-none opacity-50" : ""}
                      onClick={(e) => { e.preventDefault(); goToPage(page + 1); }}
                    />
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationLink
                      href="#"
                      size="default"
                      aria-label="Go to last page"
                      aria-disabled={page >= totalPages}
                      tabIndex={page >= totalPages ? -1 : undefined}
                      className={`pr-1.5! ${page >= totalPages ? "pointer-events-none opacity-50" : ""}`}
                      onClick={(e) => { e.preventDefault(); goToPage(totalPages); }}
                    >
                      <span className="hidden sm:block">Last</span>
                      <ChevronsRightIcon data-icon="inline-end" />
                    </PaginationLink>
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>

            <ResultsTable
              loading={loading}
              items={searchResponse.results.data}
              embedded
              error={error}
              onDismissError={() => setError(null)}
            />
          </div>
        </div>
      </Card>
      <Toaster />
    </main>
  );
};
