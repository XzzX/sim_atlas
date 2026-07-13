import { SearchIcon } from "lucide-react";
import {
  Autocomplete,
  AutocompleteEmpty,
  AutocompleteInput,
  AutocompleteItem,
  AutocompleteList,
  AutocompletePopup,
  AutocompletePositioner,
} from "@/components/ui/autocomplete";
import { CardContent } from "./ui/card";

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  items: string[];
  placeholder?: string;
}

export default function SearchBar({
  query,
  onQueryChange,
  items,
  placeholder = "Search nodes and workflows…",
}: SearchBarProps) {
  return (
    <CardContent className="pb-4">
      <Autocomplete value={query} onValueChange={onQueryChange} items={items} autoHighlight>
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <AutocompleteInput
            placeholder={placeholder}
            className="h-11 rounded-[9px] border-[1.5px] pl-10 font-mono text-sm"
          />
        </div>
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
      </Autocomplete>
    </CardContent>
  );
}
