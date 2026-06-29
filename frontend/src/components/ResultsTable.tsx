import React from "react";
import { Link } from "react-router-dom";
import { UserIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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

function PortList({ ports }: { ports: Annotation[] }) {
  if (ports.length === 0) return <span className="text-muted-foreground">—</span>;
  return (
    <ul className="space-y-1">
      {ports.map((p, i) => (
        <li key={i} className="flex flex-wrap items-center gap-1">
          <span className="text-muted-foreground">•</span>
          {p.label && <code className="text-xs">{p.label}</code>}
          {p.datatype && <Badge variant="outline">{p.datatype}</Badge>}
        </li>
      ))}
    </ul>
  );
}

interface ResultsTableProps {
  loading: boolean;
  items: ScoredSearchItem[];
}

export const ResultsTable: React.FC<ResultsTableProps> = ({ loading, items }) => {
  if (loading) {
    return (
      <div className="flex min-h-56 flex-col items-center justify-center gap-3 rounded-xl border bg-card p-4">
        <div className="size-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
        <p className="text-sm text-muted-foreground">Loading nodes...</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="min-h-[400px] rounded-xl border bg-card p-3 sm:p-4">
        <Alert variant="info">
          No nodes found. Try adjusting your search query or filters.
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-[400px] rounded-xl border bg-card">
      {/* Legend */}
      <div className="flex gap-4 border-b px-4 py-2">
        {Object.entries(TYPE_LABEL).map(([key, label]) => (
          <span key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={`size-2.5 rounded-sm ${TYPE_COLOR[key] ?? "bg-muted"}`} />
            {label}
          </span>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2">Node</th>
              <th className="px-4 py-2">Inputs</th>
              <th className="px-4 py-2">Outputs</th>
            </tr>
          </thead>
          <tbody>
            {items.map(({ node }) => {
              const dotColor = TYPE_COLOR[node.artifact_type] ?? "bg-muted";
              const desc = ("brief_description" in node ? node.brief_description : null)
                ?? node.description
                ?? null;
              return (
                <tr key={node.id} className="border-b last:border-b-0 hover:bg-muted/30">
                  <td className="px-4 py-3 align-top">
                    <div className="flex items-start gap-2">
                      <span className={`mt-1.5 size-2 shrink-0 rounded-full ${dotColor}`} />
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
                    <PortList ports={node.inputs} />
                  </td>
                  <td className="px-4 py-3 align-top">
                    <PortList ports={node.outputs} />
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
