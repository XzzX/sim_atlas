import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import { type ArtifactResponse } from "@/types/index";
import { simAtlasAPI } from "@/services/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArtifactHeader,
  ArtifactDescription,
  ArtifactDetails,
  ArtifactMisc,
  ArtifactFooter,
} from "./artifact";
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
            {artifact && (
              <Card className="h-full pt-0 border-0 shadow-none">
                <ArtifactHeader
                  name={artifact.name}
                  id={artifact.id}
                  artifact_type={artifact.artifact_type}
                  homepage_url={artifact.homepage_url ?? undefined}
                  documentation_url={artifact.documentation_url ?? undefined}
                  source_url={artifact.source_url ?? undefined}
                  python_import={
                    "python_import" in artifact
                      ? artifact.python_import
                      : undefined
                  }
                />
                <ArtifactDescription
                  docstring={
                    "docstring" in artifact ? artifact.docstring : undefined
                  }
                  description={artifact.description ?? undefined}
                />
                <ArtifactDetails
                  inputs={artifact.inputs}
                  outputs={artifact.outputs}
                  dependencies={
                    "dependencies" in artifact
                      ? (artifact.dependencies ?? undefined)
                      : undefined
                  }
                  source_code={
                    "source_code" in artifact ? artifact.source_code : undefined
                  }
                />
                <ArtifactMisc keywords={artifact.keywords} />
                <ArtifactFooter node={artifact} />
              </Card>
            )}
          </div>
        </DialogPopup>
      </DialogPortal>
    </DialogRoot>
  );
};
