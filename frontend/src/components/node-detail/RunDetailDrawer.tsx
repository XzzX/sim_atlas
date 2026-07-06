import React from "react";
import { XIcon, DownloadIcon, FileTextIcon, ClipboardCopyIcon } from "lucide-react";
import { toast } from "sonner";
import { SheetRoot, SheetPortal, SheetBackdrop, SheetPopup, SheetClose, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { DatatypeBadge } from "@/components/DatatypeBadge";
import { formatBytes, formatTimestamp, downloadTextFile } from "@/lib/utils";
import type { Annotation, ExecutionResultMetadata } from "@/types/index";

interface RunDetailDrawerProps {
  execution: ExecutionResultMetadata | null;
  inputs: Annotation[];
  onClose: () => void;
  portalContainer: HTMLElement | null;
}

export const RunDetailDrawer: React.FC<RunDetailDrawerProps> = ({
  execution,
  inputs,
  onClose,
  portalContainer,
}) => {
  const datatypeFor = (label: string) => inputs.find((i) => i.label === label)?.datatype;
  const outputSize = execution ? new Blob([execution.outputs]).size : 0;

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
              <div className="border-b px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex min-w-0 items-center gap-2">
                    <SheetTitle className="truncate font-mono text-base font-semibold text-foreground">
                      {execution.id}
                    </SheetTitle>
                    <button
                      type="button"
                      title="Copy run ID"
                      onClick={() => {
                        void navigator.clipboard.writeText(execution.id);
                        toast.success("Run ID copied to clipboard");
                      }}
                      className="shrink-0 text-muted-foreground hover:text-foreground"
                    >
                      <ClipboardCopyIcon className="size-3.5" />
                    </button>
                    <span
                      className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold"
                      style={{ background: "var(--status-success-bg)", color: "var(--status-success-fg)" }}
                    >
                      success
                    </span>
                  </div>
                  <SheetClose className="flex size-[30px] shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground hover:text-foreground">
                    <XIcon className="size-4" />
                  </SheetClose>
                </div>
                <p className="mt-2 text-[12px] text-muted-foreground">
                  Finished {formatTimestamp(execution.creation_timestamp)}
                </p>
              </div>

              <div className="flex-1 overflow-y-auto px-5 py-4">
                <div className="text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">
                  Input parameters
                </div>
                <div className="mt-2 space-y-2">
                  {execution.inputs.map((input) => (
                    <div key={input.label} className="flex items-center gap-2 text-[13px]">
                      <span className="size-[6px] shrink-0 rounded-full" style={{ background: "var(--node-dot-input)" }} />
                      <span className="font-mono text-foreground">{input.label}</span>
                      <span className="font-mono text-muted-foreground">{String(input.value)}</span>
                      {datatypeFor(input.label) && <DatatypeBadge datatype={datatypeFor(input.label)!} />}
                    </div>
                  ))}
                </div>

                <div className="mt-6 text-[11px] font-semibold uppercase tracking-[.09em] text-muted-foreground">
                  Output
                </div>
                <div className="mt-2 rounded-lg border bg-muted/40 px-3 py-2">
                  <pre className="max-h-40 overflow-auto font-mono text-[12px] whitespace-pre-wrap text-foreground">
                    {execution.outputs}
                  </pre>
                </div>
                <button
                  type="button"
                  onClick={() => downloadTextFile(`${execution.id}-output.txt`, execution.outputs)}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[12px] font-medium"
                  style={{ borderColor: "var(--node-detail-accent)", color: "var(--node-detail-accent)" }}
                >
                  <FileTextIcon className="size-3.5" />
                  output.txt
                  <span className="text-muted-foreground">· {formatBytes(outputSize)}</span>
                  <DownloadIcon className="size-3.5" />
                </button>
              </div>

              <div className="flex gap-2 border-t px-5 py-4">
                <Button
                  variant="outline"
                  className="flex-1"
                  disabled
                  title="Not available yet — requires linking executions to a workflow"
                >
                  Open in workflow
                </Button>
                <Button
                  className="flex-1"
                  disabled
                  title="Not available yet — re-running a node isn't wired up"
                >
                  Re-run node
                </Button>
              </div>
            </>
          )}
        </SheetPopup>
      </SheetPortal>
    </SheetRoot>
  );
};
