import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";

import { cn } from "@/lib/utils";

// A side-anchored panel built on the same Dialog primitive as ui/dialog.tsx,
// but absolutely positioned within a `position: relative` ancestor instead of
// fixed to the viewport — for overlays scoped to one card/section rather than
// the whole page.

const SheetRoot = DialogPrimitive.Root;
const SheetPortal = DialogPrimitive.Portal;
const SheetClose = DialogPrimitive.Close;
const SheetTitle = DialogPrimitive.Title;
const SheetDescription = DialogPrimitive.Description;

function SheetBackdrop({ className, ...props }: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      className={cn(
        "absolute inset-0 z-40 bg-[rgba(18,21,42,0.32)] data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0",
        className,
      )}
      {...props}
    />
  );
}

function SheetPopup({ className, ...props }: DialogPrimitive.Popup.Props) {
  return (
    <DialogPrimitive.Popup
      className={cn(
        "absolute inset-y-0 right-0 z-50 flex w-[460px] max-w-full flex-col overflow-hidden bg-card",
        "data-open:animate-in data-open:slide-in-from-right-8 data-open:duration-200",
        "data-closed:animate-out data-closed:slide-out-to-right-8 data-closed:duration-150",
        className,
      )}
      {...props}
    />
  );
}

export { SheetRoot, SheetPortal, SheetBackdrop, SheetPopup, SheetClose, SheetTitle, SheetDescription };
