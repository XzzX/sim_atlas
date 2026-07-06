import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { simAtlasAPI } from "../services/api";
import type { ArtifactResponse } from "../types/index";
import { NodeDetailPage } from "../components/node-detail";
import { Alert } from "@/components/ui/alert";
import { Toaster } from "@/components/ui/sonner";

export const NodePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [node, setNode] = useState<ArtifactResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await simAtlasAPI.getNode(id);
        if (!cancelled) setNode(result);
      } catch (err) {
        if (!cancelled) setError("Failed to load node. Please try again.");
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div
        className="flex min-h-screen w-full flex-col items-center justify-center gap-3"
        style={{ background: "var(--node-detail-backdrop)" }}
      >
        <div className="size-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
        <p className="text-sm text-white/70">Loading node...</p>
      </div>
    );
  }

  return (
    <>
      {error ? (
        <div
          className="flex min-h-screen w-full items-start justify-center px-4 py-10"
          style={{ background: "var(--node-detail-backdrop)" }}
        >
          <Alert variant="destructive" className="mt-10 w-full max-w-2xl">
            {error}
          </Alert>
        </div>
      ) : node ? (
        <NodeDetailPage node={node} />
      ) : (
        <div
          className="flex min-h-screen w-full items-start justify-center px-4 py-10"
          style={{ background: "var(--node-detail-backdrop)" }}
        >
          <Alert variant="info" className="mt-10 w-full max-w-2xl">
            Node not found.
          </Alert>
        </div>
      )}
      <Toaster />
    </>
  );
};
