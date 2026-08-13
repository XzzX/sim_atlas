import React, { useState, useMemo, useCallback } from "react";
import type { Edge, ReactFlowJsonObject } from "@xyflow/react";
import type { WorkflowNode } from "../nodes/nodes";
import { toWorkflowDefinition } from "../exportWorkflow";
import { toFlowrepRecipe } from "../exportFlowrep";

type ExportFormat = "python-workflow-definition" | "flowrep" | "reactflow";

interface FormatOption {
  value: ExportFormat;
  label: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  { value: "python-workflow-definition", label: "Python Workflow Definition" },
  { value: "flowrep", label: "flowrep (WorkflowRecipe)" },
  { value: "reactflow", label: "ReactFlow (native)" },
];

const FILE_NAMES: Record<ExportFormat, string> = {
  "python-workflow-definition": "workflow.json",
  flowrep: "workflow.flowrep.json",
  reactflow: "reactflow.json",
};

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  nodes: WorkflowNode[];
  edges: Edge[];
  rfObject: ReactFlowJsonObject<WorkflowNode, Edge> | null;
}

export const ExportDialog: React.FunctionComponent<ExportDialogProps> = ({
  isOpen,
  onClose,
  nodes,
  edges,
  rfObject,
}) => {
  const [format, setFormat] = useState<ExportFormat>(
    "python-workflow-definition",
  );
  const [copied, setCopied] = useState(false);

  const { serialized, errors, warnings } = useMemo((): {
    serialized: string;
    errors: string[];
    warnings: string[];
  } => {
    switch (format) {
      case "reactflow":
        return {
          serialized: JSON.stringify(rfObject, null, 2),
          errors: [],
          warnings: [],
        };
      case "flowrep": {
        const result = toFlowrepRecipe(nodes, edges);
        return {
          serialized: JSON.stringify(result.recipe, null, 2),
          errors: result.errors,
          warnings: result.warnings,
        };
      }
      case "python-workflow-definition":
        return {
          serialized: JSON.stringify(toWorkflowDefinition(nodes, edges), null, 2),
          errors: [],
          warnings: [],
        };
    }
  }, [format, nodes, edges, rfObject]);

  const handleCopy = useCallback(() => {
    void navigator.clipboard.writeText(serialized).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [serialized]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([serialized], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = FILE_NAMES[format];
    a.click();
    URL.revokeObjectURL(url);
  }, [serialized, format]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex justify-center items-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-md p-6 max-w-2xl w-11/12 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900">Export Workflow</h2>

        <div className="flex items-center gap-3">
          <label
            htmlFor="export-format"
            className="text-sm font-medium text-gray-700 whitespace-nowrap"
          >
            Format
          </label>
          <select
            id="export-format"
            value={format}
            onChange={(e) => setFormat(e.target.value as ExportFormat)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          >
            {FORMAT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {errors.length > 0 && (
          <div
            data-testid="export-errors"
            className="border border-red-300 bg-red-50 rounded p-3 max-h-32 overflow-y-auto"
          >
            <p className="text-sm font-medium text-red-800">
              {errors.length === 1 ? "1 problem" : `${errors.length} problems`} — this
              recipe will be rejected
            </p>
            <ul className="mt-1 list-disc list-inside text-sm text-red-700">
              {errors.map((message, index) => (
                <li key={index}>{message}</li>
              ))}
            </ul>
          </div>
        )}

        {warnings.length > 0 && (
          <div
            data-testid="export-warnings"
            className="border border-amber-300 bg-amber-50 rounded p-3 max-h-32 overflow-y-auto"
          >
            <p className="text-sm font-medium text-amber-800">
              {warnings.length === 1 ? "1 note" : `${warnings.length} notes`} — exported
              with changes
            </p>
            <ul className="mt-1 list-disc list-inside text-sm text-amber-700">
              {warnings.map((message, index) => (
                <li key={index}>{message}</li>
              ))}
            </ul>
          </div>
        )}

        <textarea
          readOnly
          value={serialized}
          className="w-full h-64 p-3 border border-gray-300 rounded bg-gray-50 font-mono text-sm focus:outline-none resize-none"
        />

        <div className="flex gap-2 justify-end">
          <button
            onClick={handleCopy}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors font-medium"
          >
            {copied ? "Copied!" : "Copy to Clipboard"}
          </button>
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors font-medium"
          >
            Download
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
