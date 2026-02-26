import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Container, Spinner, Alert } from "react-bootstrap";
import { nodeAPI } from "../services/api";
import { NodeMetadata } from "../types/index";
import { NodeDetailView } from "../components/NodeDetailView";

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
        const fetchedNode = await nodeAPI.getNode(nodeHash);
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
      <div
        className="d-flex justify-content-center align-items-center"
        style={{ minHeight: "100vh" }}
      >
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Loading...</span>
        </Spinner>
      </div>
    );
  }

  if (error || !node) {
    return (
      <Container className="py-5">
        <Alert variant="danger">{error || "Node not found"}</Alert>
        <a href="/" className="btn btn-secondary">
          Back to Search
        </a>
      </Container>
    );
  }

  return <NodeDetailView node={node} onClose={handleClose} />;
};
