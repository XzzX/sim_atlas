import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRightIcon, ClipboardCopyIcon } from "lucide-react";
import { toast } from "sonner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { DatatypeBadge } from "@/components/DatatypeBadge";
import { TypeChip } from "./TypeChip";
import { CollapsibleSection } from "./CollapsibleSection";
import { cn, formatTimestamp } from "@/lib/utils";
import type { ArtifactResponse, Reference } from "@/types/index";

const REFERENCE_KIND_STYLE: Record<string, React.CSSProperties> = {
  "See also": { background: "var(--chip-union-bg)", color: "var(--chip-union-fg)" },
  "Used by": { background: "var(--chip-domain-bg)", color: "var(--chip-domain-fg)" },
  Uses: { background: "var(--chip-coll-bg)", color: "var(--chip-coll-fg)" },
};

interface SectionHeadingProps {
  id: string;
  label: string;
  count?: number;
}

const SectionHeading: React.FC<SectionHeadingProps> = ({ id, label, count }) => (
  <div id={id} className="flex scroll-mt-6 items-center gap-2">
    <span className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">{label}</span>
    {count !== undefined && (
      <span
        className="inline-flex h-[18px] items-center justify-center rounded-full px-[7px] font-mono text-[11px] font-semibold"
        style={{ background: "var(--node-more-bg)", color: "var(--node-more-fg)" }}
      >
        {count}
      </span>
    )}
  </div>
);

interface OverviewTabProps {
  node: ArtifactResponse;
  executionsCount: number;
  onNavigateToExecutions: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ node, executionsCount, onNavigateToExecutions }) => {
  const navigate = useNavigate();

  const docstring = "docstring" in node ? (node.docstring ?? undefined) : undefined;
  const dependencies = "dependencies" in node ? node.dependencies : undefined;
  const usedBy = "used_by" in node ? node.used_by : undefined;
  const uses = "uses" in node ? node.uses : undefined;

  const [docTab, setDocTab] = useState<"docstring" | "description">(
    node.description && !docstring ? "description" : "docstring",
  );

  const references = useMemo(() => {
    const items: { kind: string; ref: Reference }[] = [
      ...(node.see_also ?? []).map((ref) => ({ kind: "See also", ref })),
      ...(usedBy ?? []).map((ref) => ({ kind: "Used by", ref })),
      ...(uses ?? []).map((ref) => ({ kind: "Uses", ref })),
    ];
    return items;
  }, [node.see_also, usedBy, uses]);

  const hasDependencies = dependencies != null;
  const hasReferences = references.length > 0;

  const navSections = useMemo(
    () => [
      { id: "documentation", label: "Documentation" },
      { id: "inputs", label: "Inputs" },
      { id: "outputs", label: "Outputs" },
      { id: "source", label: "Source code" },
      ...(hasDependencies ? [{ id: "dependencies", label: "Dependencies" }] : []),
      ...(hasReferences ? [{ id: "references", label: "References & related" }] : []),
    ],
    [hasDependencies, hasReferences],
  );

  const [activeSection, setActiveSection] = useState(navSections[0].id);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveSection(visible[0].target.id);
      },
      { rootMargin: "0px 0px -70% 0px", threshold: 0 },
    );
    navSections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [navSections]);

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const copySourceCode = () => {
    void navigator.clipboard.writeText(node.source_code);
    toast.success("Source code copied to clipboard");
  };

  return (
    <div className="flex">
      <div className="min-w-0 flex-1 space-y-8 px-[34px] py-7">
        {/* Documentation */}
        <div>
          <div className="flex items-center justify-between gap-4">
            <SectionHeading id="documentation" label="Documentation" />
            <ToggleGroup
              value={[docTab]}
              onValueChange={(next) => {
                if (next[0]) setDocTab(next[0] as "docstring" | "description");
              }}
              className="bg-muted"
            >
              <ToggleGroupItem value="docstring" size="sm">
                Docstring
              </ToggleGroupItem>
              <ToggleGroupItem value="description" size="sm">
                Description
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
          {docTab === "docstring" ? (
            <p className="mt-3 text-[14px] leading-[1.7] whitespace-pre-wrap text-foreground/80">
              {docstring ?? "No docstring available."}
            </p>
          ) : (
            <p className="mt-3 text-[14px] leading-[1.7] whitespace-pre-wrap text-foreground/80">
              {node.description ??
                "No long-form description has been provided for this node yet. Descriptions are curated notes that complement the auto-extracted docstring — add usage examples, caveats, or links to related workflows here."}
            </p>
          )}
        </div>

        {/* Inputs */}
        <div>
          <SectionHeading id="inputs" label="Inputs" count={node.inputs.length} />
          <div className="mt-3 overflow-hidden rounded-xl border">
            <div
              className="grid gap-3 bg-muted/50 px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[.06em] text-muted-foreground"
              style={{ gridTemplateColumns: "1.5fr 1.6fr 0.7fr 0.7fr" }}
            >
              <span>Label</span>
              <span>Data type</span>
              <span>Unit</span>
              <span>Default</span>
            </div>
            {node.inputs.length === 0 ? (
              <p className="px-4 py-3 text-sm text-muted-foreground">No inputs</p>
            ) : (
              node.inputs.map((input, idx) => (
                <div
                  key={idx}
                  className="grid items-center gap-3 border-t px-4 py-2.5"
                  style={{ gridTemplateColumns: "1.5fr 1.6fr 0.7fr 0.7fr" }}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="size-[7px] shrink-0 rounded-full" style={{ background: "var(--node-dot-input)" }} />
                    <span className="truncate font-mono text-[13px] text-foreground">{input.label ?? "—"}</span>
                  </span>
                  <span>
                    {input.datatype ? (
                      <DatatypeBadge datatype={input.datatype} />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </span>
                  <span className="font-mono text-[13px] text-muted-foreground">{input.unit ?? "—"}</span>
                  <span className="font-mono text-[13px] text-muted-foreground">
                    {input.has_default_value ? "Yes" : "—"}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Outputs */}
        <div>
          <SectionHeading id="outputs" label="Outputs" count={node.outputs.length} />
          <div className="mt-3 overflow-hidden rounded-xl border">
            <div
              className="grid gap-3 bg-muted/50 px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[.06em] text-muted-foreground"
              style={{ gridTemplateColumns: "1.2fr 1.2fr 0.6fr 0.8fr 1.8fr" }}
            >
              <span>Label</span>
              <span>Data type</span>
              <span>Unit</span>
              <span>Quantity</span>
              <span>Description</span>
            </div>
            {node.outputs.length === 0 ? (
              <p className="px-4 py-3 text-sm text-muted-foreground">No outputs</p>
            ) : (
              node.outputs.map((output, idx) => (
                <div
                  key={idx}
                  className="grid items-center gap-3 border-t px-4 py-2.5"
                  style={{ gridTemplateColumns: "1.2fr 1.2fr 0.6fr 0.8fr 1.8fr" }}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="size-[7px] shrink-0 rounded-full" style={{ background: "var(--node-dot-output)" }} />
                    <span className="truncate font-mono text-[13px] text-foreground">{output.label ?? "return"}</span>
                  </span>
                  <span>
                    {output.datatype ? (
                      <DatatypeBadge datatype={output.datatype} />
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </span>
                  <span className="font-mono text-[13px] text-muted-foreground">{output.unit ?? "—"}</span>
                  <span className="font-mono text-[13px] text-muted-foreground">{output.quantity ?? "—"}</span>
                  <span className="truncate text-[12.5px] text-muted-foreground">{output.description ?? "—"}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Source code */}
        <CollapsibleSection id="source" label="Source code">
          <div className="overflow-hidden rounded-xl border" style={{ borderColor: "#232840" }}>
            <div className="flex items-center justify-between px-3 py-2" style={{ background: "#1a1e30" }}>
              <span className="truncate font-mono text-[12px]" style={{ color: "#c8cee0" }}>
                {node.python_import ?? node.name}
              </span>
              <button
                type="button"
                onClick={copySourceCode}
                className="inline-flex shrink-0 items-center gap-1 text-[11.5px] font-medium"
                style={{ color: "var(--node-detail-accent)" }}
              >
                <ClipboardCopyIcon className="size-3" />
                Copy
              </button>
            </div>
            <pre
              className="max-h-[420px] overflow-auto p-4 font-mono text-[12.5px] leading-[1.75]"
              style={{ background: "#171b2b", color: "#c8cee0" }}
            >
              <code>{node.source_code}</code>
            </pre>
          </div>
        </CollapsibleSection>

        {/* Dependencies */}
        {hasDependencies && (
          <CollapsibleSection id="dependencies" label="Dependencies" count={dependencies.length}>
            {dependencies.length === 0 ? (
              <p className="text-sm text-muted-foreground">No dependencies</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {dependencies.map((dep) => (
                  <span
                    key={dep}
                    className="rounded-[7px] px-2 py-1 font-mono text-[12px]"
                    style={{ background: "var(--node-more-bg)", color: "var(--node-more-fg)" }}
                  >
                    {dep}
                  </span>
                ))}
              </div>
            )}
          </CollapsibleSection>
        )}

        {/* References & related */}
        {hasReferences && (
          <CollapsibleSection id="references" label="References & related" count={references.length}>
            <div className="space-y-1.5">
              {references.map(({ kind, ref }) => (
                <button
                  key={`${kind}-${ref.id}`}
                  type="button"
                  onClick={() => void navigate(`/node/${ref.id}`)}
                  className="flex w-full items-center gap-2 rounded-[10px] border px-3 py-2 text-left transition-colors hover:border-[var(--node-detail-hover-bd)]"
                >
                  <span
                    className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold"
                    style={REFERENCE_KIND_STYLE[kind]}
                  >
                    {kind}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[13px] text-foreground">{ref.label}</span>
                  <ArrowRightIcon className="size-3.5 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </div>
          </CollapsibleSection>
        )}
      </div>

      {/* Right rail */}
      <div className="w-[268px] shrink-0 space-y-6 border-l px-6 py-7" style={{ background: "var(--sidebar)" }}>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">
            On this page
          </div>
          <nav className="mt-2 space-y-0.5">
            {navSections.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => scrollToSection(s.id)}
                className={cn(
                  "block w-full border-l-2 py-1 pl-3 text-left text-[12.5px]",
                  activeSection === s.id ? "font-semibold text-foreground" : "font-medium text-muted-foreground",
                )}
                style={{ borderColor: activeSection === s.id ? "var(--node-detail-accent)" : "var(--border)" }}
              >
                {s.label}
              </button>
            ))}
          </nav>
        </div>

        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">Details</div>
          <div className="mt-2 space-y-2 text-[12.5px]">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Type</span>
              <TypeChip artifactType={node.artifact_type} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Created</span>
              <span className="text-foreground">{formatTimestamp(node.creation_timestamp)}</span>
            </div>
            <button type="button" onClick={onNavigateToExecutions} className="flex w-full items-center justify-between">
              <span className="text-muted-foreground">Executions</span>
              <span className="font-medium" style={{ color: "var(--node-detail-accent)" }}>
                {executionsCount} →
              </span>
            </button>
          </div>
        </div>

        {node.keywords.length > 0 && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">Keywords</div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {node.keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-md px-2 py-0.5 text-[11.5px]"
                  style={{ background: "var(--chip-domain-bg)", color: "var(--chip-domain-fg)" }}
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">Maintainer</div>
          <div className="mt-2">
            <p className="text-[13.5px] font-semibold text-foreground">{node.author_name}</p>
            <p className="font-mono text-[11.5px] text-muted-foreground">{node.author_email}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
