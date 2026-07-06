import React from "react";
import { DownloadIcon } from "lucide-react";
import { formatBytes, formatTimestamp, downloadTextFile } from "@/lib/utils";
import type { ExecutionResultMetadata } from "@/types/index";

function downloadOutput(execution: ExecutionResultMetadata) {
  downloadTextFile(`${execution.id}-output.txt`, execution.outputs);
}

interface ExecutionRunRowProps {
  execution: ExecutionResultMetadata;
  onClick: () => void;
}

export const ExecutionRunRow: React.FC<ExecutionRunRowProps> = ({ execution, onClick }) => {
  const outputSize = new Blob([execution.outputs]).size;

  return (
    <div
      onClick={onClick}
      className="grid cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-colors hover:border-[var(--node-detail-hover-bd)] hover:shadow-[var(--node-detail-shadow-row-hover)]"
      style={{ gridTemplateColumns: "150px 1fr 130px" }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="size-[7px] shrink-0 rounded-full" style={{ background: "var(--status-success)" }} />
          <span className="truncate font-mono text-[13px] text-foreground" title={execution.id}>
            {execution.id.slice(0, 8)}
          </span>
        </div>
        <div className="mt-0.5 text-[11.5px] text-muted-foreground">{formatTimestamp(execution.creation_timestamp)}</div>
      </div>

      <div className="flex min-w-0 flex-wrap gap-1.5">
        {execution.inputs.map((input) => (
          <span
            key={input.label}
            className="inline-flex items-center gap-1 rounded-[7px] px-1.5 py-0.5 font-mono text-[11px]"
            style={{ background: "var(--node-more-bg)", color: "var(--node-more-fg)" }}
          >
            <span className="text-muted-foreground">{input.label}</span>
            {String(input.value)}
          </span>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            downloadOutput(execution);
          }}
          className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12px] font-medium transition-colors"
          style={{ borderColor: "var(--node-detail-accent)", color: "var(--node-detail-accent)" }}
        >
          <DownloadIcon className="size-3.5" />
          {formatBytes(outputSize)}
        </button>
      </div>
    </div>
  );
};
