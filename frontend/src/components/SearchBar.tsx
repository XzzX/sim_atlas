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
import { splitName } from "@/lib/utils";
import type { NodeSuggestion } from "../types/index";

interface SearchBarProps {
  query: string;
  onQueryChange: (query: string) => void;
  suggestions: NodeSuggestion[];
  onSelectSuggestion: (suggestion: NodeSuggestion) => void;
  showEmpty?: boolean;
}

export default function SearchBar({
  query,
  onQueryChange,
  suggestions,
  onSelectSuggestion,
  showEmpty,
}: SearchBarProps) {
  return (
    <CardContent className="pb-4">
      <Autocomplete
        value={query}
        items={suggestions}
        // The server already matched name + import path (ADR-0020); Base UI's
        // default client-side `contains` filter would re-filter — and hide —
        // results it does not consider a substring match.
        filter={null}
        itemToStringValue={(s: NodeSuggestion) => s.name}
        // autoHighlight + Enter-selects would otherwise let a plain "run the
        // search" Enter press navigate away to the first suggestion.
        autoHighlight={false}
        onValueChange={(value, details) => {
          if (details.reason === "item-press") {
            const picked = suggestions.find((s) => s.name === value);
            if (picked) onSelectSuggestion(picked);
            return;
          }
          onQueryChange(value);
        }}
      >
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <AutocompleteInput
            placeholder="Search nodes and workflows…"
            className="h-11 rounded-[9px] border-[1.5px] pl-10 font-mono text-sm"
          />
        </div>
        <AutocompletePositioner sideOffset={6}>
          <AutocompletePopup>
            <AutocompleteEmpty>{showEmpty ? "No matches." : null}</AutocompleteEmpty>
            <AutocompleteList>
              {(item: NodeSuggestion) => {
                const { label, modulePath } = splitName(item.name);
                const accent =
                  item.artifact_type === "workflow"
                    ? "var(--node-accent-workflow)"
                    : "var(--node-accent-function)";
                return (
                  <AutocompleteItem
                    key={item.id}
                    value={item}
                    className="flex flex-col gap-0.5 border-l-[3px] pl-2.5"
                    style={{ borderLeftColor: accent }}
                  >
                    <span
                      className="font-mono text-[13px] font-semibold"
                      style={{ color: "var(--node-name)" }}
                    >
                      {label}
                    </span>
                    <span
                      className="font-mono text-[10.5px]"
                      style={{ color: "var(--node-path)" }}
                    >
                      {item.python_import ?? modulePath}
                    </span>
                  </AutocompleteItem>
                );
              }}
            </AutocompleteList>
          </AutocompletePopup>
        </AutocompletePositioner>
      </Autocomplete>
    </CardContent>
  );
}
