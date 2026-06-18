import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { type ArtifactResponse } from "@/types/index";
import { simAtlasAPI } from "@/services/api";
import { Button } from "@/components/ui/button";
import { NodeCard } from "./NodeCard";
import {
  DialogRoot,
  DialogPortal,
  DialogBackdrop,
  DialogPopup,
} from "@/components/ui/dialog";

interface ReferenceModalProps {
  refId: string | null;
  open: boolean;
  onClose: () => void;
}

export const ReferenceModal: React.FC<ReferenceModalProps> = ({
  refId,
  open,
  onClose,
}) => {
  const [artifact, setArtifact] = useState<ArtifactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !refId) return;
    const id = refId;

    async function fetchArtifact() {
      setLoading(true);
      setError(null);
      setArtifact(null);
      try {
        const data = await simAtlasAPI.getNode(id);
        setArtifact(data);
      } catch {
        setError("Failed to load artifact.");
      } finally {
        setLoading(false);
      }
    }

    void fetchArtifact();
  }, [open, refId]);

  return (
    <DialogRoot
      open={open}
      onOpenChange={(isOpen: boolean) => {
        if (!isOpen) onClose();
      }}
    >
      <DialogPortal>
        <DialogBackdrop />
        <DialogPopup>
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 z-10"
              onClick={onClose}
            >
              <X size={16} />
            </Button>
            {loading && (
              <div className="flex items-center justify-center p-12 text-muted-foreground">
                Loading…
              </div>
            )}
            {error && (
              <div className="flex items-center justify-center p-12 text-destructive">
                {error}
              </div>
            )}
            {artifact && <NodeCard node={artifact} />}
          </div>
        </DialogPopup>
      </DialogPortal>
    </DialogRoot>
  );
};
