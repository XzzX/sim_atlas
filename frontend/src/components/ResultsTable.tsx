import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/alert";
import { splitName } from "@/lib/utils";
import { DatatypeBadge } from "@/components/DatatypeBadge";
import type { ScoredSearchItem, Annotation } from "../types/index";

// ── Port list ──────────────────────────────────────────────────────────────────

function PortList({
  ports,
  dotColor,
  cap,
}: {
  ports: Annotation[];
  dotColor: string;
  cap?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  if (ports.length === 0) return null;
  const limit = cap ?? ports.length;
  const visible = expanded ? ports : ports.slice(0, limit);
  const hidden = ports.length - limit;

  return (
    <div className="flex min-w-0 flex-col gap-[5px] overflow-hidden pt-0.5">
      {visible.map((p, i) => (
        <div key={i} className="flex min-w-0 items-center gap-[5px] overflow-hidden">
          <span className="size-[6px] shrink-0 rounded-full" style={{ background: dotColor }} />
          {p.label && (
            <span
              className="min-w-0 shrink truncate font-mono text-[11.5px] leading-none"
              style={{ color: "var(--node-io)" }}
            >
              {p.label}
            </span>
          )}
          {p.datatype && <DatatypeBadge datatype={p.datatype} />}
        </div>
      ))}
      {!expanded && hidden > 0 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(true);
          }}
          className="inline-flex w-fit items-center gap-1 rounded-[10px] border px-2.5 py-[3px] text-[10.5px] transition-colors duration-[120ms]"
          style={{
            background: "var(--node-more-bg)",
            borderColor: "var(--node-more-bd)",
            color: "var(--node-more-fg)",
          }}
        >
          +{hidden} more
          <svg
            width="9"
            height="9"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      )}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const GRID_COLS = "2fr 1fr 1fr";
const INPUTS_CAP = 3;

// ── Legend ─────────────────────────────────────────────────────────────────────

export const Legend: React.FC = () => (
  <div className="flex gap-4">
    {[
      { key: "function", label: "Function", color: "var(--node-accent-function)" },
      { key: "workflow", label: "Workflow", color: "var(--node-accent-workflow)" },
    ].map(({ key, label, color }) => (
      <span key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="inline-block h-3.5 w-1 rounded-full" style={{ background: color }} />
        {label}
      </span>
    ))}
  </div>
);

// ── ResultsTable ───────────────────────────────────────────────────────────────

interface ResultsTableProps {
  loading: boolean;
  items: ScoredSearchItem[];
  embedded?: boolean;
  error?: string | null;
  onDismissError?: () => void;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({
  loading,
  items,
  embedded,
  error,
  onDismissError,
}) => {
  const navigate = useNavigate();
  const wrapCls = embedded ? "" : "rounded-xl border bg-card";

  if (loading) {
    return (
      <div className={`flex min-h-56 flex-col items-center justify-center gap-3 p-4 ${wrapCls}`}>
        <div className="size-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
        <p className="text-sm text-muted-foreground">Loading nodes...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`min-h-[400px] p-3 sm:p-4 ${wrapCls}`}>
        <Alert variant="destructive" className="flex items-center justify-between gap-2">
          <span>{error}</span>
          {onDismissError && (
            <button
              type="button"
              className="text-sm underline underline-offset-2"
              onClick={onDismissError}
            >
              Dismiss
            </button>
          )}
        </Alert>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={`min-h-[400px] p-3 sm:p-4 ${wrapCls}`}>
        <Alert variant="info">No nodes found. Try adjusting your search query or filters.</Alert>
      </div>
    );
  }

  return (
    <div className={embedded ? "min-h-[400px] overflow-x-auto" : "min-h-[400px] overflow-x-auto rounded-xl border bg-card"}>
      {/* Column headers */}
      <div
        className="grid border-b px-7 py-[9px]"
        style={{ gridTemplateColumns: GRID_COLS, background: "var(--node-th-bg)" }}
      >
        {(["Node", "Inputs", "Outputs"] as const).map((h) => (
          <span
            key={h}
            className="text-[9.5px] font-bold uppercase tracking-[.09em]"
            style={{ color: "var(--node-th-fg)" }}
          >
            {h}
          </span>
        ))}
      </div>

      {/* Data rows */}
      {items.map(({ node }) => {
        const isWorkflow = node.artifact_type === "workflow";
        const accent = isWorkflow ? "var(--node-accent-workflow)" : "var(--node-accent-function)";
        const desc =
          ("brief_description" in node ? node.brief_description : null) ??
          node.description ??
          null;
        const { label, modulePath } = splitName(node.name);

        return (
          <div
            key={node.id}
            onClick={() => { void navigate(`/node/${node.id}`); }}
            className="grid cursor-pointer items-start border-b border-l-[6px] py-[13px] pr-6 pl-[25px] transition-colors duration-[120ms] last:border-b-0 hover:bg-[var(--node-hover)]"
            style={{ gridTemplateColumns: GRID_COLS, borderLeftColor: accent }}
          >
            {/* Node cell */}
            <div className="min-w-0 pr-4">
              <div className="mb-0.5 flex items-center gap-[7px]">
                <span
                  className="font-mono text-[13.5px] font-semibold leading-none tracking-[-0.3px]"
                  style={{ color: "var(--node-name)" }}
                  title={node.name}
                >
                  {label}
                </span>
              </div>
              {modulePath && (
                <div
                  className="mb-1.5 font-mono text-[10.5px] leading-none"
                  style={{ color: "var(--node-path)" }}
                >
                  {modulePath}
                </div>
              )}
              {desc && (
                <p className="line-clamp-2 text-[12.5px] leading-[1.45] text-muted-foreground">
                  {desc}
                </p>
              )}
            </div>

            {/* Inputs cell */}
            <PortList ports={node.inputs} dotColor="var(--node-dot-input)" cap={INPUTS_CAP} />

            {/* Outputs cell */}
            <PortList ports={node.outputs} dotColor="var(--node-dot-output)" />
          </div>
        );
      })}
    </div>
  );
};

