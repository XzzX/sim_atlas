import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { simAtlasAPI } from "../services/api";
import { NodeMetadata } from "../types/index";
import { NodeDetailView } from "../components/NodeDetailView";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export const DetailPage: React.FC = () => {
  const { nodeHash } = useParams<{ nodeHash: string }>();
  const navigate = useNavigate();
  const [node, setNode] = useState<NodeMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNode = async () => {
      if (!nodeHash) {
        setError("No node specified");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const fetchedNode = await simAtlasAPI.getNode(nodeHash);
        setNode(fetchedNode);
      } catch (err) {
        setError("Failed to load node details. Please try again.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchNode();
  }, [nodeHash]);

  const handleClose = () => {
    navigate("/");
  };

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="size-10 animate-spin rounded-full border-2 border-muted border-t-foreground" />
      </div>
    );
  }

  if (error || !node) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center gap-4 px-4">
        <Alert variant="destructive">{error || "Node not found"}</Alert>
        <Button variant="outline" onClick={handleClose}>
          Back to Search
        </Button>
      </main>
    );
  }

  return <NodeDetailView node={node} onClose={handleClose} />;
};
