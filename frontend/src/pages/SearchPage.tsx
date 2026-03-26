import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import { simAtlasAPI } from "../services/api";
import {
  Filter,
  FilterOptions,
  ScoredSearchItem,
  ScoredSearchResponse,
} from "../types/index";
import { FacetedSearch } from "../components/FacetedSearch";
import { NodeCard } from "../components/NodeCard";
import { Alert } from "@/components/ui/alert";
import { CategoryFilter } from "@/components/CategoryFilter";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import SearchBar from "@/components/SearchBar";
import { Toaster } from "@/components/ui/sonner";

const EMPTY_FILTER: Filter = {
  category: "",
  type: [],
  author: [],
  keywords: [],
  datatypes: [],
  units: [],
  quantities: [],
};

const EMPTY_FILTER_OPTIONS: FilterOptions = {
  category: {},
  type: [],
  author: [],
  keywords: [],
  datatypes: [],
  units: [],
  quantities: [],
};

interface SearchCardProps {
  onSearchChange: (query: string, category: string, filters: Filter) => void;
  availableFilterOptions: FilterOptions;
  suggestions: string[];
}

export const SearchCard: React.FC<SearchCardProps> = ({
  onSearchChange,
  suggestions,
  availableFilterOptions,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [category, setCategory] = useState<string>(searchParams.get("c") ?? "");
  const [filters, setFilters] = useState<Filter>({
    category: searchParams.get("category") ?? EMPTY_FILTER.category,
    type: searchParams.getAll("type") ?? EMPTY_FILTER.type,
    author: searchParams.getAll("author") ?? EMPTY_FILTER.author,
    keywords: searchParams.getAll("keywords") ?? EMPTY_FILTER.keywords,
    datatypes: searchParams.getAll("datatypes") ?? EMPTY_FILTER.datatypes,
    units: searchParams.getAll("units") ?? EMPTY_FILTER.units,
    quantities: searchParams.getAll("quantities") ?? EMPTY_FILTER.quantities,
  });

  const handleSearch = () => {
    onSearchChange(query, category, filters);
  };

  useEffect(() => {
    handleSearch();
  }, []);

  return (
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
          setSearchParams({ q: v, c: category, ...filters });
          onSearchChange(v, category, filters);
        }}
        items={suggestions}
      />
      <CategoryFilter
        category={category}
        categoryOptions={availableFilterOptions.category}
        onCategoryChange={(v) => {
          setCategory(v);
          setSearchParams({ q: query, c: v, ...filters });
          onSearchChange(query, v, filters);
        }}
      />
      <FacetedSearch
        filters={filters}
        availableFilterOptions={availableFilterOptions}
        onFilterChange={(v) => {
          setFilters(v);
          setSearchParams({ q: query, c: category, ...v });
          onSearchChange(query, category, v);
        }}
      />
    </Card>
  );
};

interface ContentProps {
  loading: boolean;
  items: ScoredSearchItem[];
}

const Content: React.FC<ContentProps> = ({ loading, items }) => {
  return (
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
              key={result.node.source_code_hash}
              node={result.node}
              score={result.score}
            />
          ))}
        </div>
      )}
    </section>
  );
};

interface SearchPageProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const SearchPage: React.FC<SearchPageProps> = () => {
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
    async (query: string, category: string, filters: Filter) => {
      try {
        setLoading(true);
        setError(null);
        const results = await simAtlasAPI.search(query, category, filters);
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
        onSearchChange={(query, category, filters) => {
          void debouncedSearch(query, category, filters);
        }}
        suggestions={searchResponse.results.data.map(
          (result) => result.node.python_import,
        )}
        availableFilterOptions={availableFilterOptions}
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
