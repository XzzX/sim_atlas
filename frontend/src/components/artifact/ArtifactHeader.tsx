import React from "react";
import { type ArtifactResponse, ArtifactType } from "../../types/index";
import {
  ClipboardCopyIcon,
  ExternalLinkIcon,
  FileDownIcon,
  Code,
  HouseIcon,
  BookIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

function generatePythonImportCommand(pythonImport: string) {
  return `import ${pythonImport}`;
}

const handleDownload = (filename: string, content: string) => {
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();

  URL.revokeObjectURL(url);
};

interface ArtifactHeaderProps {
  node: ArtifactResponse;
  score?: number;
}

export const ArtifactHeader: React.FC<ArtifactHeaderProps> = ({
  node,
  score,
}) => {
  return (
    <CardHeader className="bg-chart-1 pb-2 pt-4">
      <CardTitle className="text-lg">{node.name}</CardTitle>
      <CardDescription>
        <small>{node.id}</small>
      </CardDescription>
      <CardDescription>
        <Badge variant="secondary" className="mr-2">
          {node.artifact_type}
        </Badge>
        {score !== undefined && (
          <Badge variant="success">Score: {score.toFixed(2)}</Badge>
        )}
      </CardDescription>
      <CardAction className="space-x-2">
        {node.homepage_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(node.homepage_url, "_blank");
            }}
          >
            <HouseIcon /> Homepage
          </Button>
        )}
        {node.documentation_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(node.documentation_url, "_blank");
            }}
          >
            <BookIcon /> Documentation
          </Button>
        )}
        {node.source_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(node.source_url, "_blank");
            }}
          >
            <Code /> Sourcecode
          </Button>
        )}
        {node.artifact_type === ArtifactType.function && node.python_import && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              void navigator.clipboard.writeText(
                generatePythonImportCommand(node.python_import),
              );
              toast.success("Python import copied to clipboard");
            }}
          >
            <ClipboardCopyIcon /> Python Import
          </Button>
        )}
        {node.artifact_type === ArtifactType.workflow && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open("ide/?wf_hash=" + node.id);
            }}
          >
            <ExternalLinkIcon />
            Web IDE
          </Button>
        )}
        {node.artifact_type === ArtifactType.workflow && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleDownload(
                node.name + ".json",
                JSON.stringify(node.definition, null, 2),
              );
            }}
          >
            <FileDownIcon />
            Download
          </Button>
        )}
      </CardAction>
    </CardHeader>
  );
};
