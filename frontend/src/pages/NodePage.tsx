import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeftIcon } from "lucide-react";
import { simAtlasAPI } from "../services/api";
import type { ArtifactResponse } from "../types/index";
import { NodeCard } from "../components/NodeCard";
import { Alert } from "@/components/ui/alert";
import { Toaster } from "@/components/ui/sonner";

export const NodePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
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

  return (
    <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8">
      <button
        type="button"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-2 hover:underline"
        onClick={() => void navigate(-1)}
      >
        <ArrowLeftIcon className="size-4" />
        Back to search
      </button>

      {loading ? (
        <div className="flex min-h-56 flex-col items-center justify-center gap-3">
          <div className="size-8 animate-spin rounded-full border-2 border-muted border-t-foreground" />
          <p className="text-sm text-muted-foreground">Loading node...</p>
        </div>
      ) : error ? (
        <Alert variant="destructive">{error}</Alert>
      ) : node ? (
        <NodeCard
          node={node}
          onReferenceClick={(refId) => void navigate(`/node/${refId}`)}
        />
      ) : (
        <Alert variant="info">Node not found.</Alert>
      )}
      <Toaster />
    </main>
  );
};
