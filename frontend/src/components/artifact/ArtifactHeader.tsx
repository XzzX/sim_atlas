import React from "react";
import { ArtifactType } from "../../types/index";
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
  name: string;
  id: string;
  artifact_type: string;
  score?: number;
  homepage_url?: string;
  documentation_url?: string;
  source_url?: string;
  python_import?: string;
  download?: string;
}

export const ArtifactHeader: React.FC<ArtifactHeaderProps> = ({
  name,
  id,
  artifact_type,
  score,
  homepage_url,
  documentation_url,
  source_url,
  python_import,
  download,
}) => {
  return (
    <CardHeader className="bg-chart-1 pb-2 pt-4">
      <CardTitle className="text-lg">{name}</CardTitle>
      <CardDescription>
        <small>{id}</small>
      </CardDescription>
      <CardDescription>
        <Badge variant="secondary" className="mr-2">
          {artifact_type}
        </Badge>
        {score !== undefined && (
          <Badge variant="success">Score: {score.toFixed(2)}</Badge>
        )}
      </CardDescription>
      <CardAction className="space-x-2">
        {homepage_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(homepage_url, "_blank");
            }}
          >
            <HouseIcon /> Homepage
          </Button>
        )}
        {documentation_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(documentation_url, "_blank");
            }}
          >
            <BookIcon /> Documentation
          </Button>
        )}
        {source_url && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open(source_url, "_blank");
            }}
          >
            <Code /> Sourcecode
          </Button>
        )}
        {python_import && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              void navigator.clipboard.writeText(
                generatePythonImportCommand(python_import),
              );
              toast.success("Python import copied to clipboard");
            }}
          >
            <ClipboardCopyIcon /> Python Import
          </Button>
        )}
        {artifact_type === ArtifactType.workflow && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              window.open("ide/?wf_hash=" + id);
            }}
          >
            <ExternalLinkIcon />
            Web IDE
          </Button>
        )}
        {download && (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleDownload(
                name + ".json",
                JSON.stringify(download, null, 2),
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
