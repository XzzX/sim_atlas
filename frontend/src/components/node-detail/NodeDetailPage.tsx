import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeftIcon, ClipboardCopyIcon, HouseIcon, BookIcon, Code as CodeIcon, SquareTerminalIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { splitName } from "@/lib/utils";
import { simAtlasAPI } from "@/services/api";
import { TypeChip } from "./TypeChip";
import { ExecutionsTab } from "./ExecutionsTab";
import { OverviewTab } from "./OverviewTab";
import type { ArtifactResponse, ExecutionResultMetadata } from "../../types/index";

type TabValue = "overview" | "executions";

function isTabValue(value: string | null): value is TabValue {
  return value === "overview" || value === "executions";
}

interface NodeDetailPageProps {
  node: ArtifactResponse;
}

export const NodeDetailPage: React.FC<NodeDetailPageProps> = ({ node }) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [cardEl, setCardEl] = useState<HTMLDivElement | null>(null);

  const [executions, setExecutions] = useState<ExecutionResultMetadata[]>([]);
  const [executionsLoading, setExecutionsLoading] = useState(true);
  const [executionsError, setExecutionsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setExecutionsLoading(true);
        setExecutionsError(null);
        const result = await simAtlasAPI.getExecutionResults(node.id);
        if (!cancelled) setExecutions(result);
      } catch (err) {
        if (!cancelled) setExecutionsError("Failed to load executions. Please try again.");
        console.error(err);
      } finally {
        if (!cancelled) setExecutionsLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [node.id]);

  const tab: TabValue = isTabValue(searchParams.get("tab")) ? (searchParams.get("tab") as TabValue) : "overview";

  const setTab = (value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === "overview") {
      next.delete("tab");
    } else {
      next.set("tab", value);
    }
    setSearchParams(next);
  };

  const { label, modulePath } = splitName(node.name);
  const pythonImport = "python_import" in node ? (node.python_import ?? undefined) : undefined;

  const copyId = () => {
    void navigator.clipboard.writeText(node.id);
    toast.success("Node ID copied to clipboard");
  };

  const copyPythonImport = () => {
    if (!pythonImport) return;
    void navigator.clipboard.writeText(`import ${pythonImport}`);
    toast.success("Python import copied to clipboard");
  };

  return (
    <div className="min-h-screen w-full px-4 py-10 sm:px-8" style={{ background: "var(--node-detail-backdrop)" }}>
      <div
        className="mx-auto w-full max-w-7xl rounded-4xl p-4 sm:p-8"
        style={{
          background: "var(--node-detail-frame)",
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.055) 1.2px, transparent 1.2px)",
          backgroundSize: "24px 24px",
        }}
      >
        <div
          ref={setCardEl}
          className="relative overflow-hidden rounded-2xl bg-card"
          style={{ boxShadow: "var(--node-detail-shadow-card)" }}
        >
          {/* back link */}
          <div className="px-8 pt-[18px]">
            <button
              type="button"
              onClick={() => void navigate(-1)}
              className="inline-flex items-center gap-1 text-[13px] font-medium text-muted-foreground hover:text-foreground"
            >
              <ArrowLeftIcon className="size-3.5" />
              Back to search
            </button>
          </div>

          {/* header */}
          <div className="flex flex-wrap items-start justify-between gap-6 px-8 pt-3.5">
            <div className="min-w-0">
              <TypeChip artifactType={node.artifact_type} />
              <div className="mt-3 font-mono leading-snug break-all">
                {modulePath && <span className="text-[15px] text-muted-foreground">{modulePath}.</span>}
                <span className="text-2xl font-semibold text-foreground">{label}</span>
              </div>
              <div className="mt-2.5 flex items-center gap-2">
                <span className="text-[10px] font-semibold tracking-[.08em] text-muted-foreground">ID</span>
                <button
                  type="button"
                  onClick={copyId}
                  title="Copy node ID"
                  className="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground hover:text-foreground"
                >
                  {node.id}
                  <ClipboardCopyIcon className="size-3" />
                </button>
              </div>
            </div>

            <div className="flex flex-shrink-0 flex-wrap justify-end gap-2">
              {node.homepage_url && (
                <Button variant="outline" size="sm" className="rounded-md" onClick={() => window.open(node.homepage_url!, "_blank", "noopener,noreferrer")}>
                  <HouseIcon /> Homepage
                </Button>
              )}
              {node.documentation_url && (
                <Button variant="outline" size="sm" className="rounded-md" onClick={() => window.open(node.documentation_url!, "_blank", "noopener,noreferrer")}>
                  <BookIcon /> Documentation
                </Button>
              )}
              {node.source_url && (
                <Button variant="outline" size="sm" className="rounded-md" onClick={() => window.open(node.source_url!, "_blank", "noopener,noreferrer")}>
                  <CodeIcon /> Source code
                </Button>
              )}
              {node.artifact_type === "workflow" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-md"
                  onClick={() => window.open(`/ide/?wf_id=${encodeURIComponent(node.id)}`, "_blank", "noopener,noreferrer")}
                >
                  <SquareTerminalIcon /> Web IDE
                </Button>
              )}
              {pythonImport && (
                <Button
                  size="sm"
                  className="rounded-md border-[var(--node-detail-accent)] bg-[var(--node-detail-accent)] text-white hover:bg-[var(--node-detail-accent)]/90"
                  onClick={copyPythonImport}
                >
                  Python import
                </Button>
              )}
            </div>
          </div>

          {/* tabs */}
          <Tabs value={tab} onValueChange={(value) => setTab(String(value))} className="mt-[18px]">
            <TabsList variant="line" className="w-full justify-start gap-6 border-b px-8">
              <TabsTrigger value="overview" className="after:bg-[var(--node-detail-accent)]">
                Overview
              </TabsTrigger>
              <TabsTrigger value="executions" className="after:bg-[var(--node-detail-accent)]">
                Executions
                <span
                  className="inline-flex h-[18px] items-center justify-center rounded-full px-[7px] font-mono text-[11px] font-semibold"
                  style={{ background: "var(--node-more-bg)", color: "var(--node-more-fg)" }}
                >
                  {executionsLoading ? "…" : executions.length}
                </span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <OverviewTab
                node={node}
                executionsCount={executions.length}
                onNavigateToExecutions={() => setTab("executions")}
              />
            </TabsContent>
            <TabsContent value="executions">
              <ExecutionsTab
                inputs={node.inputs}
                executions={executions}
                loading={executionsLoading}
                error={executionsError}
                drawerContainer={cardEl}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};
