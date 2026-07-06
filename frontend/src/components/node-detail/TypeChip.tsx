import React from "react";
import { ArtifactType } from "../../types/index";
import { cn } from "@/lib/utils";

const ACCENT_VAR: Record<ArtifactType, string> = {
  [ArtifactType.function]: "var(--node-accent-function)",
  [ArtifactType.workflow]: "var(--node-accent-workflow)",
};

interface TypeChipProps {
  artifactType: ArtifactType;
  className?: string;
}

export const TypeChip: React.FC<TypeChipProps> = ({ artifactType, className }) => {
  const accent = ACCENT_VAR[artifactType];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-2.5 py-[3px] text-[11px] font-semibold uppercase tracking-[.05em]",
        className,
      )}
      style={{ background: `color-mix(in oklab, ${accent} 14%, white)`, color: accent }}
    >
      {artifactType}
    </span>
  );
};
