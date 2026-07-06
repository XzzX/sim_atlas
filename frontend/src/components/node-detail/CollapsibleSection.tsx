import React, { useState } from "react";
import { CollapsibleRoot, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";

interface CollapsibleSectionProps {
  id: string;
  label: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  id,
  label,
  count,
  defaultOpen = false,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div id={id} className="scroll-mt-6">
      <CollapsibleRoot open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between py-1 text-left">
          <span className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">
              {label}
            </span>
            {count !== undefined && (
              <span
                className="inline-flex h-[18px] items-center justify-center rounded-full px-[7px] font-mono text-[11px] font-semibold"
                style={{ background: "var(--node-more-bg)", color: "var(--node-more-fg)" }}
              >
                {count}
              </span>
            )}
          </span>
          <span className="text-[12.5px] font-medium" style={{ color: "var(--node-detail-accent)" }}>
            {open ? "Hide ▾" : "Show ▸"}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-3">{children}</CollapsibleContent>
      </CollapsibleRoot>
    </div>
  );
};
