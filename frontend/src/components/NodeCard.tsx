import React from "react";
import { type ArtifactResponse } from "../types/index";
import { Card } from "@/components/ui/card";
import {
  ArtifactHeader,
  ArtifactDescription,
  ArtifactDetails,
  ArtifactMisc,
  ArtifactFooter,
} from "./artifact";

interface NodeCardProps {
  node: ArtifactResponse;
  score?: number;
}

export const NodeCard: React.FC<NodeCardProps> = ({ node, score }) => {
  return (
    <Card className="h-full pt-0 border-1 border-chart-1">
      <ArtifactHeader
        name={node.name}
        id={node.id}
        artifact_type={node.artifact_type}
        score={score}
        homepage_url={node.homepage_url}
        documentation_url={node.documentation_url}
        source_url={node.source_url}
        python_import={"python_import" in node ? node.python_import : undefined}
      />
      <ArtifactDescription
        docstring={node.docstring}
        description={node.ai_description}
        brief_description={node.ai_summary}
      />
      <ArtifactDetails
        inputs={node.inputs}
        outputs={node.outputs}
        dependencies={"dependencies" in node ? node.dependencies : undefined}
        source_code={"source_code" in node ? node.source_code : undefined}
        definition={"workflow_definition" in node ? node.workflow_definition : undefined}
      />
      <ArtifactMisc keywords={node.keywords} />
      <ArtifactFooter node={node} />
    </Card>
  );
};
