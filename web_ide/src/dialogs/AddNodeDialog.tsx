import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { type Filter, type FilterOptions } from "../interfaces/BackendSchema";
import type { InputDataElement } from "../nodes/InputNode";
import type { OutputDataElement } from "../nodes/OutputNode";
import type { NodeData } from "../nodes/FunctionNode";
import { simAtlasAPI } from "../services/api";
import {
  ArrowDownToLine,
  ArrowUpDown,
  ArrowUpFromLine,
  BotIcon,
  SearchIcon,
} from "lucide-react";

const PORT_OPTIONS = [
  { value: null, Icon: ArrowUpDown, label: "Both" },
  { value: "inputs" as const, Icon: ArrowDownToLine, label: "Inputs" },
  { value: "outputs" as const, Icon: ArrowUpFromLine, label: "Outputs" },
];

const EMPTY_FILTER: Filter = {
  category: null,
  artifact_type: ["function"],
  author: null,
  keywords: null,
  datatypes: null,
  units: null,
  quantities: null,
  port_type: null,
};

type SearchMode = "normal" | "semantic";

interface AddNodeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    nodeData: InputDataElement | OutputDataElement | NodeData,
  ) => void;
  initialSearchQuery?: string;
  initialFilter?: Filter;
  connectingHandleType?: "source" | "target";
}

export const AddNodeDialog: React.FunctionComponent<AddNodeDialogProps> = ({
  isOpen,
  onClose,
  onAdd,
  initialSearchQuery,
  initialFilter,
  connectingHandleType,
}) => {
  const [searchTerm, setSearchTerm] = useState(initialSearchQuery ?? "");
  const [searchMode, setSearchMode] = useState<SearchMode>("normal");
  const [filter, setFilter] = useState<Filter>(initialFilter ?? EMPTY_FILTER);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(
    null,
  );
  const [results, setResults] = useState<NodeData["metadata"][]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [expandControlNodes, setExpandControlNodes] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load filter options once
  useEffect(() => {
    simAtlasAPI.getFilterOptions().then(setFilterOptions).catch(console.error);
  }, []);

  const runSearch = useCallback(
    async (term: string, f: Filter, p: number, mode: SearchMode) => {
      setLoading(true);
      try {
        const resp = await simAtlasAPI.search(
          term || null,
          f,
          p,
          mode === "semantic",
        );
        setResults(resp.results.data.map((item) => item.node));
        setTotalPages(resp.results.total_pages);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Debounced re-search on term / filter / mode change
  useEffect(() => {
    if (!isOpen) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSearch(searchTerm, filter, 1, searchMode);
      setPage(1);
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchTerm, filter, searchMode, isOpen, runSearch]);

  const handleAdd = (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    data: InputDataElement | OutputDataElement | NodeData,
  ) => {
    const label =
      prompt("Please enter a name for the node", data.label) ?? data.label;
    onAdd(type, { ...data, label });
    setSearchTerm("");
    setFilter(EMPTY_FILTER);
    onClose();
  };

  const handleCancel = useCallback(() => {
    setSearchTerm("");
    setFilter(EMPTY_FILTER);
    onClose();
  }, [onClose]);

  // Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleCancel();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [handleCancel, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex justify-center items-center z-50"
      onClick={handleCancel}
    >
      <div
        className="bg-white rounded-lg shadow-md p-6 max-w-2xl w-11/12 max-h-[85vh] flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900">Add Node</h2>

        {/* Search bar + mode toggle */}
        <div className="flex gap-2 items-center">
          <input
            type="text"
            placeholder={
              searchMode === "semantic"
                ? "Describe what you're looking for…"
                : "Search nodes…"
            }
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (searchMode === "semantic" && e.key === "Enter") {
                if (debounceRef.current) clearTimeout(debounceRef.current);
                void runSearch(searchTerm, filter, 1, searchMode);
              }
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            autoFocus
          />
          <div className="flex overflow-hidden rounded border text-xs h-[38px]">
            {(
              [
                { mode: "normal" as const, Icon: SearchIcon, label: "Normal" },
                { mode: "semantic" as const, Icon: BotIcon, label: "AI" },
              ] as const
            ).map(({ mode, Icon, label }, i) => (
              <button
                key={mode}
                type="button"
                onClick={() => setSearchMode(mode)}
                className={[
                  "flex items-center gap-1 px-2 py-1 transition-colors",
                  i > 0 ? "border-l" : "",
                  searchMode === mode
                    ? "bg-blue-500 text-white"
                    : "text-gray-500 hover:bg-gray-100",
                ].join(" ")}
              >
                <Icon className="size-3" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 text-sm">
          {filterOptions && filterOptions.artifact_type.length > 0 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-500 uppercase">
                Node Type
              </label>
              <select
                value={filter.artifact_type?.[0] ?? ""}
                onChange={(e) =>
                  setFilter({
                    ...filter,
                    artifact_type: e.target.value ? [e.target.value] : null,
                  })
                }
                className="px-2 py-1 border border-gray-300 rounded text-sm bg-white focus:outline-none focus:border-blue-500"
              >
                <option value="">All</option>
                {filterOptions.artifact_type.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Port direction */}
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-500 uppercase">
              Direction
            </label>
            <div className="flex overflow-hidden rounded border h-[30px]">
              {PORT_OPTIONS.map(({ value, Icon, label }, i) => {
                const active = (filter.port_type ?? null) === value;
                return (
                  <button
                    key={label}
                    type="button"
                    title={label}
                    onClick={() => setFilter({ ...filter, port_type: value })}
                    className={[
                      "flex flex-1 items-center justify-center gap-1 px-2 text-xs transition-colors",
                      i > 0 ? "border-l" : "",
                      active
                        ? "bg-blue-500 text-white"
                        : "text-gray-500 hover:bg-gray-100",
                    ].join(" ")}
                  >
                    <Icon className="size-3" />
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {filterOptions && filterOptions.datatypes.length > 0 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-500 uppercase">
                Datatype
              </label>
              <select
                value={filter.datatypes?.[0] ?? ""}
                onChange={(e) =>
                  setFilter({
                    ...filter,
                    datatypes: e.target.value ? [e.target.value] : null,
                  })
                }
                className="px-2 py-1 border border-gray-300 rounded text-sm bg-white focus:outline-none focus:border-blue-500"
              >
                <option value="">All</option>
                {filterOptions.datatypes.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          )}

          {filterOptions && filterOptions.units.length > 0 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-500 uppercase">
                Unit
              </label>
              <select
                value={filter.units?.[0] ?? ""}
                onChange={(e) =>
                  setFilter({
                    ...filter,
                    units: e.target.value ? [e.target.value] : null,
                  })
                }
                className="px-2 py-1 border border-gray-300 rounded text-sm bg-white focus:outline-none focus:border-blue-500"
              >
                <option value="">All</option>
                {filterOptions.units.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>
          )}

          {filterOptions && filterOptions.quantities.length > 0 && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-500 uppercase">
                Quantity
              </label>
              <select
                value={filter.quantities?.[0] ?? ""}
                onChange={(e) =>
                  setFilter({
                    ...filter,
                    quantities: e.target.value ? [e.target.value] : null,
                  })
                }
                className="px-2 py-1 border border-gray-300 rounded text-sm bg-white focus:outline-none focus:border-blue-500"
              >
                <option value="">All</option>
                {filterOptions.quantities.map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex flex-col justify-end">
            <button
              onClick={() => setFilter(EMPTY_FILTER)}
              className="px-3 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-100 transition-colors"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Results list */}
        <div className="flex-1 overflow-y-auto border border-gray-200 rounded min-h-[200px]">
          {/* Control nodes */}
          <div>
            <button
              onClick={() => setExpandControlNodes(!expandControlNodes)}
              className="w-full px-3 py-2 bg-blue-50 border-b border-blue-200 text-xs font-semibold text-blue-700 uppercase hover:bg-blue-100 transition-colors flex items-center justify-between"
            >
              <span>Control Nodes</span>
              <span className="text-sm">{expandControlNodes ? "−" : "+"}</span>
            </button>
            {expandControlNodes && (
              <>
                {connectingHandleType !== "source" && (
                  <div
                    className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-blue-100 transition-colors bg-blue-50"
                    onClick={() =>
                      handleAdd("InputNode", { label: "Input", value: "" })
                    }
                  >
                    <div className="font-medium text-gray-900 text-sm mb-1">
                      Input
                    </div>
                    <div className="text-xs text-gray-500">
                      Input node for workflow entry points
                    </div>
                  </div>
                )}
                {connectingHandleType !== "target" && (
                  <div
                    className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-blue-100 transition-colors bg-blue-50"
                    onClick={() =>
                      handleAdd("OutputNode", { label: "Output", value: "" })
                    }
                  >
                    <div className="font-medium text-gray-900 text-sm mb-1">
                      Output
                    </div>
                    <div className="text-xs text-gray-500">
                      Output node for workflow results
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* API results */}
          {loading ? (
            <div className="px-6 py-6 text-center text-gray-400 text-sm">
              Loading…
            </div>
          ) : results.length > 0 ? (
            results.map((node) => (
              <div
                key={node.id}
                className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-100 last:border-b-0 transition-colors"
                onClick={() =>
                  handleAdd("FunctionNode", {
                    label: node.python_import?.split(".").pop() ?? "",
                    metadata: node,
                  })
                }
              >
                <div className="font-medium text-gray-900 text-sm mb-1">
                  {node.python_import}
                </div>
                <div className="text-xs text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis">
                  {node.docstring}
                </div>
              </div>
            ))
          ) : (
            <div className="px-6 py-6 text-center text-gray-500 text-sm">
              No nodes match your search
            </div>
          )}
        </div>

        {/* Pagination + footer */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => {
                const p = page - 1;
                setPage(p);
                void runSearch(searchTerm, filter, p, searchMode);
              }}
              className="px-2 py-1 text-sm border rounded disabled:opacity-40 hover:bg-gray-100 transition-colors"
            >
              ←
            </button>
            <span className="text-sm text-gray-500">
              {page} / {Math.max(totalPages, 1)}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => {
                const p = page + 1;
                setPage(p);
                void runSearch(searchTerm, filter, p, searchMode);
              }}
              className="px-2 py-1 text-sm border rounded disabled:opacity-40 hover:bg-gray-100 transition-colors"
            >
              →
            </button>
          </div>
          <Button onClick={handleCancel} variant="outline">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};
