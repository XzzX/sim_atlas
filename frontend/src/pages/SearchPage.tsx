import React, { useState, useEffect } from "react";
import { Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import { simAtlasAPI } from "../services/api";
import {
  NodeMetadata,
  Filter,
  FilterOptions,
  ScoredSearchResponse,
} from "../types/index";
import { FacetedSearch } from "../components/FacetedSearch";
import { NodeCard } from "../components/NodeCard";
import { Alert } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { CategoryFilter } from "@/components/CategoryFilter";
import { Card, CardContent } from "@/components/ui/card";

const EMPTY_FILTER_OPTIONS: FilterOptions = {
  category: {},
  type: [],
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

export const SearchPage: React.FC<SearchPageProps> = ({
  searchQuery,
  setSearchQuery,
}) => {
  const navigate = useNavigate();
  const [allNodes, setAllNodes] = useState<ScoredSearchResponse[]>([]);
  // const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<Filter>({});
  const [availableFilterOptions, setAvailableFilterOptions] =
    useState<FilterOptions>(EMPTY_FILTER_OPTIONS);
  const [category, setCategory] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      const results = await simAtlasAPI.search(searchQuery, category, filters);
      setAllNodes(results);
    } catch (err) {
      setError("Search failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const debouncedSearch = useDebouncedCallback(() => {
    void performSearch();
  }, 500);

  const immediateSearch = () => {
    debouncedSearch.cancel();
    void performSearch();
  };

  useEffect(() => {
    void debouncedSearch();
  }, []);

  useEffect(() => {
    const loadFilterOptions = async () => {
      try {
        const options = await simAtlasAPI.getFilterOptions();
        setAvailableFilterOptions(options);
      } catch (err) {
        console.error("Failed to fetch filter options", err);
      }
    };

    void loadFilterOptions();

    return () => {
      debouncedSearch.cancel();
    };
  }, [debouncedSearch]);

  const handleClearFilters = () => {
    setFilters({});
    void debouncedSearch();
  };

  const handleNodeSelect = (node: NodeMetadata) => {
    void navigate(`/node/${node.source_code_hash}`);
  };

  return (
    <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8">
      <Card>
        <CardContent className="space-y-4 border-b">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="h-11 pl-9"
            placeholder="Search nodes by name, description, or functionality..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
              setSearchQuery(e.target.value);
              debouncedSearch();
            }}
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) =>
              e.key === "Enter" && immediateSearch()
            }
          />
        </CardContent>

        <CategoryFilter
          category={category}
          categoryOptions={availableFilterOptions.category}
          onCategoryChange={(category) => {
            setCategory(category);
            void debouncedSearch();
          }}
        />

        <FacetedSearch
          nodes={allNodes}
          filters={filters}
          availableFilterOptions={availableFilterOptions}
          onFilterChange={(filterOptions) => {
            setFilters(filterOptions);
            void debouncedSearch();
          }}
          onClearFilters={handleClearFilters}
        />
      </Card>
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
      <section className="min-h-[400px] rounded-xl border bg-card p-3 sm:p-4">
        {loading ? (
          <div className="flex min-h-56 flex-col items-center justify-center gap-3">
            <div className="size-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
            <p className="text-sm text-muted-foreground">Loading nodes...</p>
          </div>
        ) : allNodes.length === 0 ? (
          <Alert variant="info">
            No nodes found. Try adjusting your search query or filters.
          </Alert>
        ) : (
          <div className="grid gap-3">
            {allNodes.map((result) => (
              <NodeCard
                key={result.node.source_code_hash}
                node={result.node}
                score={result.score}
                onSelect={handleNodeSelect}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
};
