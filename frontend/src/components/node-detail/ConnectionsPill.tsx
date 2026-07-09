import React from "react";
import { useNavigate } from "react-router-dom";
import { cn, pluralize } from "@/lib/utils";
import { ArtifactType, type Reference } from "@/types/index";

const ACCENT_VAR: Record<ArtifactType, string> = {
  [ArtifactType.function]: "var(--node-accent-function)",
  [ArtifactType.workflow]: "var(--node-accent-workflow)",
};

const VARIANT_STYLE = {
  input: {
    pillBg: "#eef1ff",
    pillFg: "#3651c9",
    pillHoverBg: "#e2e8ff",
    panelBg: "#fafbff",
    panelBorder: "#e7ebf8",
    headerFg: "#8891b5",
    rowBorder: "#edeff3",
    rowHoverBorder: "#cdd8ff",
    label: "from",
    header: "Connected from",
  },
  output: {
    pillBg: "#e5f5ea",
    pillFg: "#268a3d",
    pillHoverBg: "#d6efdd",
    panelBg: "#f4fbf6",
    panelBorder: "#d8eede",
    headerFg: "#5c9e71",
    rowBorder: "#e6f0e9",
    rowHoverBorder: "#bfe3c9",
    label: "to",
    header: "Connected to",
  },
} as const;

const KIND_GLYPH: Record<ArtifactType, string> = {
  [ArtifactType.function]: "ƒ",
  [ArtifactType.workflow]: "W",
};

interface ConnectionsVariantProps {
  variant: "input" | "output";
  connections: Reference[] | null | undefined;
}

interface ConnectionsPillProps extends ConnectionsVariantProps {
  isExpanded: boolean;
  onToggle: () => void;
  panelId: string;
}

export const ConnectionsPill: React.FC<ConnectionsPillProps> = ({
  variant,
  connections,
  isExpanded,
  onToggle,
  panelId,
}) => {
  const style = VARIANT_STYLE[variant];

  if (!connections || connections.length === 0) return null;

  return (
    <button
      type="button"
      aria-expanded={isExpanded}
      aria-controls={panelId}
      onClick={onToggle}
      className="inline-flex shrink-0 items-center gap-1 rounded-[20px] px-[9px] py-[3px] text-[11px] font-semibold transition-colors"
      style={{ background: isExpanded ? style.pillHoverBg : style.pillBg, color: style.pillFg }}
    >
      {connections.length} {style.label}
      <span aria-hidden="true">{isExpanded ? "⌄" : "›"}</span>
    </button>
  );
};

interface ConnectionsPanelProps extends ConnectionsVariantProps {
  panelId: string;
}

export const ConnectionsPanel: React.FC<ConnectionsPanelProps> = ({ variant, connections, panelId }) => {
  const navigate = useNavigate();
  const style = VARIANT_STYLE[variant];

  if (!connections || connections.length === 0) return null;

  const headerId = `${panelId}-header`;

  return (
    <div
      id={panelId}
      role="region"
      aria-labelledby={headerId}
      className="mt-2 rounded-[11px] px-[15px] py-[13px]"
      style={{ background: style.panelBg, border: `1px solid ${style.panelBorder}` }}
    >
      <div
        id={headerId}
        className="text-[10px] font-semibold uppercase tracking-[.06em]"
        style={{ color: style.headerFg }}
      >
        {style.header} · {pluralize(connections.length, "node")}
      </div>
      <div className="mt-2 max-h-[180px] space-y-1.5 overflow-y-auto">
        {connections.map((ref) => {
          const accent = ref.artifact_type
            ? ACCENT_VAR[ref.artifact_type]
            : "var(--muted-foreground)";
          return (
            <button
              key={ref.id}
              type="button"
              onClick={() => void navigate(`/node/${ref.id}`)}
              className="flex w-full min-w-0 items-center gap-2 rounded-[9px] bg-white px-[11px] py-2 text-left transition-colors"
              style={{ border: `1px solid ${style.rowBorder}` }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = style.rowHoverBorder;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = style.rowBorder;
              }}
            >
              <span
                className={cn("flex size-[18px] shrink-0 items-center justify-center rounded-[5px] font-mono text-[11px] font-semibold")}
                style={{ background: `color-mix(in oklab, ${accent} 14%, white)`, color: accent }}
              >
                {ref.artifact_type ? KIND_GLYPH[ref.artifact_type] : "•"}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-[12.5px] text-[#2a3042]">{ref.label}</span>
              <span
                className="shrink-0 rounded-[20px] px-2 py-[1px] font-mono text-[10.5px] font-semibold"
                style={{ background: "#eef0f4", color: "#6b7286" }}
              >
                {pluralize(ref.count, "link")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
