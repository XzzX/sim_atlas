import React, { useState } from "react";
import { Link } from "react-router-dom";
import { UserIcon } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import type { ScoredSearchItem, Annotation } from "../types/index";

const TYPE_COLOR: Record<string, string> = {
  function: "bg-chart-1",
  workflow: "bg-purple-500",
};

const TYPE_LABEL: Record<string, string> = {
  function: "Function",
  workflow: "Workflow",
};

const VISIBLE_COUNT = 4;

function PortList({ ports, dotClass }: { ports: Annotation[]; dotClass: string }) {
  const [expanded, setExpanded] = useState(false);
  if (ports.length === 0) return <span className="text-muted-foreground">—</span>;
  const visible = expanded ? ports : ports.slice(0, VISIBLE_COUNT);
  const hidden = ports.length - VISIBLE_COUNT;
  return (
    <ul className="space-y-1">
      {visible.map((p, i) => (
        <li key={i} className="flex flex-wrap items-center gap-1.5">
          <span className={`size-2.5 shrink-0 rounded-full ${dotClass}`} />
          {p.label && <code className="text-xs">{p.label}</code>}
          {p.datatype && (
            <span className="text-xs text-muted-foreground">{p.datatype}</span>
          )}
        </li>
      ))}
      {!expanded && hidden > 0 && (
        <li>
          <button
            type="button"
            className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2"
            onClick={() => setExpanded(true)}
          >
            +{hidden} more
          </button>
        </li>
      )}
    </ul>
  );
}

export const Legend: React.FC = () => (
  <div className="flex gap-4">
    {Object.entries(TYPE_LABEL).map(([key, label]) => (
      <span key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className={`inline-block h-3.5 w-1 rounded-full ${TYPE_COLOR[key] ?? "bg-muted"}`} />
        {label}
      </span>
    ))}
  </div>
);

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
        <Alert
          variant="destructive"
          className="flex items-center justify-between gap-2"
        >
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
        <Alert variant="info">
          No nodes found. Try adjusting your search query or filters.
        </Alert>
      </div>
    );
  }

  return (
    <div className={embedded ? "min-h-[400px]" : "min-h-[400px] rounded-xl border bg-card"}>
      <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ tableLayout: "fixed" }}>
            <colgroup>
              <col style={{ width: "50%" }} />
              <col style={{ width: "25%" }} />
              <col style={{ width: "25%" }} />
            </colgroup>
            <thead>
              <tr className="border-b text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-2">Node</th>
                <th className="px-4 py-2">Inputs</th>
                <th className="px-4 py-2">Outputs</th>
              </tr>
            </thead>
            <tbody>
              {items.map(({ node }) => {
                const barColor = TYPE_COLOR[node.artifact_type] ?? "bg-muted";
                const desc = ("brief_description" in node ? node.brief_description : null)
                  ?? node.description
                  ?? null;
                return (
                  <tr key={node.id} className="border-b last:border-b-0 hover:bg-muted/30">
                    <td className="px-4 py-3 align-top">
                      <div className="flex gap-2">
                        <span className={`self-stretch w-1 shrink-0 rounded-full ${barColor}`} />
                        <div className="min-w-0">
                          <Link
                            to={`/node/${node.id}`}
                            className="truncate font-medium hover:underline"
                            title={node.name}
                          >
                            {node.name}
                          </Link>
                          {desc && (
                            <p
                              className="mt-0.5 line-clamp-2 text-xs text-muted-foreground"
                              title={desc}
                            >
                              {desc}
                            </p>
                          )}
                          <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                            <UserIcon className="size-3" />
                            {node.author_name}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <PortList ports={node.inputs} dotClass="bg-blue-500" />
                    </td>
                    <td className="px-4 py-3 align-top">
                      <PortList ports={node.outputs} dotClass="bg-green-500" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
      </div>
    </div>
  );
};
