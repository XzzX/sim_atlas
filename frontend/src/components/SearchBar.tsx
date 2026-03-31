import {
  Autocomplete,
  AutocompleteEmpty,
  AutocompleteInput,
  AutocompleteItem,
  AutocompleteList,
  AutocompletePopup,
  AutocompletePositioner,
} from "@/components/ui/autocomplete";
import { Label } from "@/components/ui/label";
import { CardContent } from "./ui/card";
import { BotIcon, SearchIcon } from "lucide-react";

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  items: string[];
  searchMode: "normal" | "semantic";
  onSearchModeChange: (mode: "normal" | "semantic") => void;
}

export default function SearchBar({
  query,
  onQueryChange,
  items,
  searchMode,
  onSearchModeChange,
}: SearchBarProps) {
  return (
    <CardContent className="border-b pb-4">
      <div className="mb-2 flex items-center justify-between">
        <Label>Query</Label>
        <div className="flex items-center gap-0.5 rounded-lg border p-0.5 text-xs">
          <button
            type="button"
            onClick={() => onSearchModeChange("normal")}
            className={`flex items-center gap-1 rounded-md px-2 py-1 transition-colors ${
              searchMode === "normal"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <SearchIcon className="size-3" />
            Normal
          </button>
          <button
            type="button"
            onClick={() => onSearchModeChange("semantic")}
            className={`flex items-center gap-1 rounded-md px-2 py-1 transition-colors ${
              searchMode === "semantic"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <BotIcon className="size-3" />
            AI Semantic
          </button>
        </div>
      </div>
      <Autocomplete
        value={query}
        onValueChange={onQueryChange}
        items={searchMode === "semantic" ? [] : items}
        autoHighlight
      >
        <AutocompleteInput
          id="item"
          placeholder={
            searchMode === "semantic"
              ? "Describe what you're looking for, then press Enter"
              : "Search for nodes and workflows"
          }
          onKeyDown={(e) => {
            if (searchMode === "semantic" && e.key === "Enter") {
              e.preventDefault();
              onQueryChange(query);
            }
          }}
        />
        {searchMode === "normal" && (
          <AutocompletePositioner sideOffset={6}>
            <AutocompletePopup>
              <AutocompleteEmpty>No Items found.</AutocompleteEmpty>
              <AutocompleteList>
                {(item: string, index: number) => (
                  <AutocompleteItem key={index} value={item}>
                    {item}
                  </AutocompleteItem>
                )}
              </AutocompleteList>
            </AutocompletePopup>
          </AutocompletePositioner>
        )}
      </Autocomplete>
    </CardContent>
  );
}
