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
}

export default function SearchBar({ query, onQueryChange, items }: SearchBarProps) {
  return (
    <CardContent className="pb-4">
      <Autocomplete value={query} onValueChange={onQueryChange} items={items} autoHighlight>
        <AutocompleteInput placeholder="Search nodes and workflows…" />
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
