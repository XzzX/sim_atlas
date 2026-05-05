import React, { useState, useMemo, useCallback } from "react";
import type { Edge, ReactFlowJsonObject } from "@xyflow/react";
import type { WorkflowNode } from "../nodes/nodes";
import { toWorkflowDefinition } from "../exportWorkflow";

type ExportFormat = "python-workflow-definition" | "reactflow";

interface FormatOption {
  value: ExportFormat;
  label: string;
}

const FORMAT_OPTIONS: FormatOption[] = [
  { value: "python-workflow-definition", label: "Python Workflow Definition" },
  { value: "reactflow", label: "ReactFlow (native)" },
];

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

  const serialized = useMemo(() => {
    if (format === "reactflow") {
      return JSON.stringify(rfObject, null, 2);
    }
    return JSON.stringify(toWorkflowDefinition(nodes, edges), null, 2);
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
    a.download = "workflow.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [serialized]);

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
