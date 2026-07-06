import React from "react";
import { XIcon } from "lucide-react";
import { SheetRoot, SheetPortal, SheetBackdrop, SheetPopup, SheetClose, SheetTitle } from "@/components/ui/sheet";
import type { ExecutionResultMetadata } from "@/types/index";

interface RunDetailDrawerProps {
  execution: ExecutionResultMetadata | null;
  onClose: () => void;
  portalContainer: HTMLElement | null;
}

export const RunDetailDrawer: React.FC<RunDetailDrawerProps> = ({ execution, onClose, portalContainer }) => {
  return (
    <SheetRoot
      open={execution !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetPortal container={portalContainer}>
        <SheetBackdrop />
        <SheetPopup style={{ boxShadow: "var(--node-detail-shadow-drawer)" }}>
          {execution && (
            <>
              <div className="flex items-center justify-between border-b px-5 py-4">
                <div className="flex items-center gap-2">
                  <SheetTitle className="font-mono text-base font-semibold text-foreground">
                    {execution.id.slice(0, 8)}
                  </SheetTitle>
                  <span
                    className="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                    style={{ background: "var(--status-success-bg)", color: "var(--status-success-fg)" }}
                  >
                    success
                  </span>
                </div>
                <SheetClose className="rounded-md bg-muted p-1.5 text-muted-foreground hover:text-foreground">
                  <XIcon className="size-4" />
                </SheetClose>
              </div>
              <div className="flex-1 overflow-y-auto px-5 py-4 text-sm text-muted-foreground">
                Full run detail — input parameters, output, artifacts — lands in the next step.
              </div>
            </>
          )}
        </SheetPopup>
      </SheetPortal>
    </SheetRoot>
  );
};
