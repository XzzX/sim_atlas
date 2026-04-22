import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { type NodeResponse } from "../interfaces/BackendSchema";
import type { InputDataElement } from "../nodes/InputNode";
import type { OutputDataElement } from "../nodes/OutputNode";
import type { NodeData } from "../nodes/FunctionNode";
import { type NodeFilter, nodeMatchesFilter } from "../interfaces/NodeFilter";

interface AddNodeDialogProps {
  allNodeMetadata: NodeResponse[];
  isOpen: boolean;
  onClose: () => void;
  onAdd: (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    nodeData: InputDataElement | OutputDataElement | NodeData,
  ) => void;
}

export const AddNodeDialog: React.FunctionComponent<AddNodeDialogProps> = ({
  allNodeMetadata,
  isOpen,
  onClose,
  onAdd,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [expandControlNodes, setExpandControlNodes] = useState(false);
  const [filter, setFilter] = useState<Partial<NodeFilter>>({
    portType: "both",
  });

  const resetFilters = () => {
    setFilter({ portType: "both" });
    setShowFilters(false);
  };

  const handleAdd = (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    data: InputDataElement | OutputDataElement | NodeData,
  ) => {
    const label =
      prompt("Please enter a name for the node", data.label) ?? data.label;
    onAdd(type, { ...data, label });
    setSearchTerm("");
    resetFilters();
    onClose();
  };

  const handleCancel = useCallback(() => {
    setSearchTerm("");
    resetFilters();
    onClose();
  }, [onClose]);

  const getUniqueValues = (key: keyof Pick<NodeResponse, "node_type">) => {
    const values = new Set<string>();
    allNodeMetadata.forEach((node) => {
      values.add(node[key]);
    });
    return Array.from(values).sort();
  };

  const getUniqueAnnotationValues = (key: "datatype" | "unit" | "quantity") => {
    const values = new Set<string>();
    allNodeMetadata.forEach((node) => {
      [...node.inputs, ...node.outputs].forEach((annotation) => {
        if (annotation[key]) {
          values.add(annotation[key]);
        }
      });
    });
    return Array.from(values).sort();
  };

  // Handle Escape key to close dialog
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        handleCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleCancel, isOpen]);

  const filteredNodes = useMemo(() => {
    return allNodeMetadata.filter((node) => {
      // Search filter
      if (searchTerm !== "") {
        const term = searchTerm.toLowerCase();
        if (
          !node.python_import?.toLowerCase().includes(term) &&
          !node.docstring.toLowerCase().includes(term)
        ) {
          return false;
        }
      }

      // Apply NodeFilter
      if (!nodeMatchesFilter(node, filter)) {
        return false;
      }

      return true;
    });
  }, [allNodeMetadata, searchTerm, filter]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex justify-center items-center z-50"
      onClick={handleCancel}
    >
      <div
        className="bg-white rounded-lg shadow-md p-6 max-w-2xl w-11/12 max-h-[80vh] flex flex-col gap-4"
        onClick={(e) => {
          e.stopPropagation();
        }}
      >
        <h2 className="text-xl font-semibold text-gray-900">Add Node</h2>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
            }}
            className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            autoFocus
          />
          <button
            onClick={() => {
              setShowFilters(!showFilters);
            }}
            className="px-3 py-2 border border-gray-300 rounded hover:bg-gray-100 transition-colors"
            title="Toggle filters"
          >
            ⚙️
          </button>
        </div>

        {showFilters && (
          <div className="p-3 bg-gray-50 border border-gray-200 rounded flex flex-col gap-3">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-gray-700 uppercase">
                Port Type
              </label>
              <div className="flex gap-3 flex-wrap">
                {(["inputs", "outputs", "both"] as const).map((type) => (
                  <label
                    key={type}
                    className="flex items-center gap-2 cursor-pointer text-sm text-gray-700"
                  >
                    <input
                      type="radio"
                      name="portType"
                      value={type}
                      checked={filter.portType === type}
                      onChange={(e) => {
                        setFilter({
                          ...filter,
                          portType: e.target.value as
                            | "inputs"
                            | "outputs"
                            | "both",
                        });
                      }}
                      className="cursor-pointer accent-blue-500"
                    />
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </label>
                ))}
              </div>
            </div>

            {getUniqueValues("node_type").length > 0 && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-gray-700 uppercase">
                  Node Type
                </label>
                <select
                  value={filter.nodeType ?? ""}
                  onChange={(e) => {
                    setFilter({
                      ...filter,
                      nodeType: e.target.value || undefined,
                    });
                  }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm bg-white cursor-pointer focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Node Types</option>
                  {getUniqueValues("node_type").map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {getUniqueAnnotationValues("datatype").length > 0 && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-gray-700 uppercase">
                  Data Type
                </label>
                <select
                  value={filter.datatype ?? ""}
                  onChange={(e) => {
                    setFilter({
                      ...filter,
                      datatype: e.target.value || undefined,
                    });
                  }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm bg-white cursor-pointer focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Data Types</option>
                  {getUniqueAnnotationValues("datatype").map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {getUniqueAnnotationValues("unit").length > 0 && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-gray-700 uppercase">
                  Unit
                </label>
                <select
                  value={filter.unit ?? ""}
                  onChange={(e) => {
                    setFilter({ ...filter, unit: e.target.value || undefined });
                  }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm bg-white cursor-pointer focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Units</option>
                  {getUniqueAnnotationValues("unit").map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {getUniqueAnnotationValues("quantity").length > 0 && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-gray-700 uppercase">
                  Quantity
                </label>
                <select
                  value={filter.quantity ?? ""}
                  onChange={(e) => {
                    setFilter({
                      ...filter,
                      quantity: e.target.value || undefined,
                    });
                  }}
                  className="px-2 py-1 border border-gray-300 rounded text-sm bg-white cursor-pointer focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Quantities</option>
                  {getUniqueAnnotationValues("quantity").map((q) => (
                    <option key={q} value={q}>
                      {q}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={resetFilters}
              className="px-3 py-1 text-sm border border-gray-300 rounded bg-white hover:bg-gray-100 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto border border-gray-200 rounded min-h-[200px]">
          {/* Control Nodes Collapsible Section */}
          <div>
            <button
              onClick={() => {
                setExpandControlNodes(!expandControlNodes);
              }}
              className="w-full px-3 py-2 bg-blue-50 border-b border-blue-200 text-xs font-semibold text-blue-700 uppercase hover:bg-blue-100 transition-colors flex items-center justify-between"
            >
              <span>Control Nodes</span>
              <span className="text-sm">{expandControlNodes ? "−" : "+"}</span>
            </button>

            {expandControlNodes && (
              <>
                <div
                  key="control_input"
                  className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-blue-100 transition-colors bg-blue-50"
                  onClick={() => {
                    handleAdd("InputNode", { label: "Input", value: "" });
                  }}
                >
                  <div className="font-medium text-gray-900 text-sm mb-1">
                    Input
                  </div>
                  <div className="text-xs text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis">
                    Input node for workflow entry points
                  </div>
                </div>
                <div
                  key="control_output"
                  className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-blue-100 transition-colors bg-blue-50"
                  onClick={() => {
                    handleAdd("OutputNode", { label: "Output", value: "" });
                  }}
                >
                  <div className="font-medium text-gray-900 text-sm mb-1">
                    Output
                  </div>
                  <div className="text-xs text-gray-500 whitespace-nowrap overflow-hidden text-ellipsis">
                    Output node for workflow results
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Regular Nodes */}
          {filteredNodes.length > 0 ? (
            filteredNodes.map((node) => (
              <div
                key={node.id}
                className="px-3 py-3 border-b border-gray-200 cursor-pointer hover:bg-gray-100 last:border-b-0 transition-colors"
                onClick={() => {
                  handleAdd("FunctionNode", {
                    label: node.python_import?.split(".").pop() ?? "",
                    metadata: node,
                  });
                }}
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
        <div className="flex gap-2 justify-end pt-2 border-t border-gray-200">
          <Button onClick={handleCancel} variant="outline">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};
