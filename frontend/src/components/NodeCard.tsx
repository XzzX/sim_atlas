import React from "react";
import { type ArtifactResponse } from "../types/index";
import { Card } from "@/components/ui/card";
import { ArtifactHeader, ArtifactContent, ArtifactFooter } from "./artifact";

interface NodeCardProps {
  node: ArtifactResponse;
  score?: number;
}

export const NodeCard: React.FC<NodeCardProps> = ({ node, score }) => {
  return (
    <Card className="h-full pt-0 border-1 border-chart-1">
      <ArtifactHeader node={node} score={score} />
      <ArtifactContent node={node} />
      <ArtifactFooter node={node} />
    </Card>
  );
};
