import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import { simAtlasAPI } from "../services/api";
import type {
  Filter,
  FilterOptions,
  ScoredSearchItem,
  ScoredSearchResponse,
} from "../types/index";
import { FacetedSearch } from "../components/FacetedSearch";
import { NodeCard } from "../components/NodeCard";
import { ReferenceModal } from "../components/ReferenceModal";
import { Alert } from "@/components/ui/alert";
import { CategoryFilter } from "@/components/CategoryFilter";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
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

/** Strip null/undefined values so URLSearchParams accepts the object. */
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

type SearchMode = "normal" | "semantic";

interface SearchCardProps {
  onSearchChange: (
    query: string,
    category: string,
    filters: Filter,
    page?: number,
  ) => void;
  availableFilterOptions: FilterOptions;
  suggestions: string[];
  page: number;
  totalPages: number;
  totalItems: number;
  searchMode: SearchMode;
  onSearchModeChange: (mode: SearchMode) => void;
}

export const SearchCard: React.FC<SearchCardProps> = ({
  onSearchChange,
  suggestions,
  availableFilterOptions,
  page,
  totalPages,
  totalItems,
  searchMode,
  onSearchModeChange,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState<string>(searchParams.get("c") ?? "");
  const [filters, setFilters] = useState<Filter>({
    category: searchParams.get("category") ?? EMPTY_FILTER.category,
    artifact_type: (searchParams.getAll("artifact_type")) ?? EMPTY_FILTER.artifact_type,
    author: searchParams.getAll("author") ?? EMPTY_FILTER.author,
    keywords: searchParams.getAll("keywords") ?? EMPTY_FILTER.keywords,
    datatypes: searchParams.getAll("datatypes") ?? EMPTY_FILTER.datatypes,
    units: searchParams.getAll("units") ?? EMPTY_FILTER.units,
    quantities: searchParams.getAll("quantities") ?? EMPTY_FILTER.quantities,
    port_type:
      (searchParams.get("port_type") as "inputs" | "outputs" | "both" | null) ??
      "both",
  });

  const handleSearch = () => {
    onSearchChange(query, category, filters, 1);
  };

  useEffect(() => {
    handleSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <React.Fragment>
      <Card>
        <CardHeader className="border-b">
          <CardTitle>Simulation Atlas</CardTitle>
          <CardDescription>
            Search and discover nodes and workflows across your projects.
          </CardDescription>
        </CardHeader>
        <SearchBar
          query={query}
          onQueryChange={(v) => {
            setQuery(v);
            setSearchParams(filtersToParams({ q: v, c: category }, filters));
            onSearchChange(v, category, filters);
          }}
          items={suggestions}
          searchMode={searchMode}
          onSearchModeChange={onSearchModeChange}
        />
        <CategoryFilter
          category={category}
          categoryOptions={availableFilterOptions.category}
          onCategoryChange={(v) => {
            setCategory(v);
            setSearchParams(filtersToParams({ q: query, c: v }, filters));
            onSearchChange(query, v, filters);
          }}
        />
        <FacetedSearch
          filters={filters}
          availableFilterOptions={availableFilterOptions}
          onFilterChange={(v) => {
            setFilters(v);
            setSearchParams(filtersToParams({ q: query, c: category }, v));
            onSearchChange(query, category, v);
          }}
        />
      </Card>
      <Card>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {totalItems} result{totalItems === 1 ? "" : "s"} total
          </p>
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
                  onClick={(event) => {
                    event.preventDefault();
                    onSearchChange(query, category, filters, 1);
                  }}
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
                  onClick={(event) => {
                    event.preventDefault();
                    onSearchChange(query, category, filters, page - 1);
                  }}
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
                  className={
                    page >= totalPages ? "pointer-events-none opacity-50" : ""
                  }
                  onClick={(event) => {
                    event.preventDefault();
                    onSearchChange(query, category, filters, page + 1);
                  }}
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
                  onClick={(event) => {
                    event.preventDefault();
                    onSearchChange(query, category, filters, totalPages);
                  }}
                >
                  <span className="hidden sm:block">Last</span>
                  <ChevronsRightIcon data-icon="inline-end" />
                </PaginationLink>
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </CardContent>
      </Card>
    </React.Fragment>
  );
};

interface ContentProps {
  loading: boolean;
  items: ScoredSearchItem[];
}

const Content: React.FC<ContentProps> = ({ loading, items }) => {
  const [dialogRefId, setDialogRefId] = useState<string | null>(null);

  return (
    <>
      <section className="min-h-[400px] rounded-xl border bg-card p-3 sm:p-4">
        {loading ? (
          <div className="flex min-h-56 flex-col items-center justify-center gap-3">
            <div className="size-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
            <p className="text-sm text-muted-foreground">Loading nodes...</p>
          </div>
        ) : items.length === 0 ? (
          <Alert variant="info">
            No nodes found. Try adjusting your search query or filters.
          </Alert>
        ) : (
          <div className="grid gap-5">
            {items.map((result) => (
              <NodeCard
                key={result.node.id}
                node={result.node}
                score={result.score}
                onReferenceClick={setDialogRefId}
              />
            ))}
          </div>
        )}
      </section>
      <ReferenceModal
        refId={dialogRefId}
        open={dialogRefId !== null}
        onClose={() => setDialogRefId(null)}
      />
    </>
  );
};

interface SearchPageProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const SearchPage: React.FC<SearchPageProps> = () => {
  const [searchMode, setSearchMode] = useState<SearchMode>("normal");
  const [searchResponse, setSearchResponse] = useState<ScoredSearchResponse>({
    results: {
      data: [],
      page: 1,
      limit: 10,
      total_items: 0,
      total_pages: 0,
    },
    aggregations: null,
  });
  const [availableFilterOptions, setAvailableFilterOptions] =
    useState<FilterOptions>(EMPTY_FILTER_OPTIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // useEffect(() => {
  //   setSearchParams((prev) => ({ ...prev, q: searchQuery }));
  // }, [searchQuery]);

  const debouncedSearch = useDebouncedCallback(
    async (
      query: string,
      category: string,
      filters: Filter,
      mode: SearchMode,
      // eslint-disable-next-line @typescript-eslint/no-inferrable-types
      page: number = 1,
    ) => {
      if (mode === "semantic" && !query.trim()) return;
      try {
        setLoading(true);
        setError(null);
        const results = await (mode === "semantic"
          ? simAtlasAPI.semanticSearch(query, category, filters, page)
          : simAtlasAPI.search(query, category, filters, page));
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
    const loadFilterOptions = async () => {
      try {
        await simAtlasAPI.getFilterOptions().then((options) => {
          setAvailableFilterOptions(options);
        });
      } catch (err) {
        console.error("Failed to fetch filter options", err);
      }
    };

    void loadFilterOptions();
  }, []);

  return (
    <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8">
      <SearchCard
        onSearchChange={(query, category, filters, page = 1) => {
          void debouncedSearch(query, category, filters, searchMode, page);
        }}
        suggestions={searchResponse.results.data
          .flatMap((result) =>
            result.node.name
          )}
        availableFilterOptions={availableFilterOptions}
        page={searchResponse.results.page}
        totalPages={searchResponse.results.total_pages}
        totalItems={searchResponse.results.total_items}
        searchMode={searchMode}
        onSearchModeChange={(mode) => {
          setSearchMode(mode);
        }}
      />
      {error && (
        <Alert
          variant="destructive"
          className="flex items-center justify-between gap-2"
        >
          <span>{error}</span>
          <button
            className="text-sm underline underline-offset-2"
            type="button"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </Alert>
      )}
      <Content loading={loading} items={searchResponse.results.data} />
      <Toaster />
    </main>
  );
};
