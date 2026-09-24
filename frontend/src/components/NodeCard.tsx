import React from "react";
import { type NodeResponse } from "../types/index";
import { Card } from "@/components/ui/card";
import {
  ArtifactHeader,
  ArtifactDescription,
  ArtifactDetails,
  ArtifactMisc,
  ArtifactFooter,
} from "./artifact";

interface NodeCardProps {
  node: NodeResponse;
  score?: number;
  onReferenceClick?: (id: string) => void;
}

export const NodeCard: React.FC<NodeCardProps> = ({
  node,
  score,
  onReferenceClick,
}) => {
  return (
    <Card className="h-full pt-0 border-1 border-chart-1">
      <ArtifactHeader
        name={node.name}
        id={node.id}
        artifact_type={node.artifact_type}
        score={score}
        homepage_url={node.homepage_url ?? undefined}
        documentation_url={node.documentation_url ?? undefined}
        source_url={node.source_url ?? undefined}
        python_import={node.python_import ?? undefined}
      />
      <ArtifactDescription
        docstring={node.docstring ?? undefined}
        description={node.description ?? undefined}
      />
      <ArtifactDetails
        inputs={node.inputs}
        outputs={node.outputs}
        dependencies={node.dependencies ?? undefined}
        source_code={node.source_code}
        see_also={node.see_also ?? []}
        uses={node.uses ?? []}
        used_by={node.used_by ?? undefined}
        onReferenceClick={onReferenceClick}
      />
      <ArtifactMisc keywords={node.keywords} />
      <ArtifactFooter node={node} />
    </Card>
  );
};
