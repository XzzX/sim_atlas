import React from "react";
import { NodeMetadata, NodeType } from "../types/index";
import {
  User,
  Calendar,
  ClipboardCopyIcon,
  ExternalLinkIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { toast } from "sonner";
import { data } from "react-router-dom";

function generatePythonImportCommand(pythonImport: string) {
  return `import ${pythonImport}`;
}

interface NodeCardProps {
  node: NodeMetadata;
  score?: number;
  onSelect?: (node: NodeMetadata) => void;
}

export const NodeCard: React.FC<NodeCardProps> = ({
  node,
  score,
  onSelect,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Card
      className="h-full cursor-pointer pt-0 border-1 border-chart-1"
      onClick={() => onSelect?.(node)}
    >
      <CardHeader className="bg-chart-1 pb-2 pt-4">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="mb-2 text-lg">{node.python_import}</CardTitle>
            <Badge variant="secondary" className="mr-2">
              {node.node_type}
            </Badge>
            {score !== undefined && (
              <Badge variant="success">Score: {score.toFixed(2)}</Badge>
            )}
          </div>
        </div>
        <CardAction>
          {node.python_import && (
            <Button
              variant="outline"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                void navigator.clipboard.writeText(
                  generatePythonImportCommand(node.python_import),
                );
                toast.success("Python import copied to clipboard");
              }}
            >
              <ClipboardCopyIcon />
            </Button>
          )}
          {node.node_type === NodeType.PYTHON_WORKFLOW_DEFINITION && (
            <Button
              variant="outline"
              size="icon"
              onClick={(e) => {
                e.stopPropagation();
                window.open("ide/?wf_hash=" + node.source_code_hash);
              }}
            >
              <ExternalLinkIcon />
            </Button>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="mb-3">
          <h3 className="mb-1 text-sm font-semibold text-muted-foreground">
            Description
          </h3>
          <p className="whitespace-pre-wrap">
            {node.docstring || "No description available"}
          </p>
        </div>
        {node.ai_docstring && (
          <div>
            <h3 className="mb-1 text-sm font-semibold text-muted-foreground">
              AI Generated Summary
            </h3>
            <div className="rounded-md border bg-muted/40 p-3">
              <p className="mb-0 whitespace-pre-wrap">{node.ai_docstring}</p>
            </div>
          </div>
        )}

        <div className="mb-3 grid gap-2 md:grid-cols-2">
          <div>
            <small className="mb-2 block text-muted-foreground">
              <strong>Inputs ({node.inputs.length})</strong>
            </small>
            {node.inputs.length > 0 ? (
              <table className="w-full text-[0.72rem]">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-1">Label</th>
                    <th className="py-1">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {node.inputs.map((input, idx) => (
                    <tr key={idx} className="border-b last:border-b-0">
                      <td className="py-1">
                        <code className="text-[0.68rem]">
                          {input.label ?? "-"}
                        </code>
                      </td>
                      <td className="py-1">
                        {input.datatype ? (
                          <Badge variant="outline" className="text-[0.64rem]">
                            {input.datatype}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mb-0 text-sm text-muted-foreground">0</p>
            )}
          </div>

          <div>
            <small className="mb-2 block text-muted-foreground">
              <strong>Outputs ({node.outputs.length})</strong>
            </small>
            {node.outputs.length > 0 ? (
              <table className="w-full text-[0.72rem]">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-1">Label</th>
                    <th className="py-1">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {node.outputs.map((output, idx) => (
                    <tr key={idx} className="border-b last:border-b-0">
                      <td className="py-1">
                        <code className="text-[0.68rem]">
                          {output.label ?? "-"}
                        </code>
                      </td>
                      <td className="py-1">
                        {output.datatype ? (
                          <Badge variant="outline" className="text-[0.64rem]">
                            {output.datatype}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="mb-0 text-sm text-muted-foreground">0</p>
            )}
          </div>
        </div>

        {node.keywords && node.keywords.length > 0 && (
          <div className="mb-3">
            <small className="mb-2 block text-muted-foreground">
              <strong>Keywords</strong>
            </small>
            <div>
              {node.keywords.map((keyword, idx) => (
                <Badge key={idx} variant="secondary" className="mb-1 mr-1">
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {node.dependencies && node.dependencies.length > 0 && (
          <div className="mb-3">
            <small className="text-muted-foreground">
              <strong>Dependencies:</strong>
            </small>
            <div className="mt-1">
              {node.dependencies.slice(0, 3).map((dep, idx) => (
                <Badge key={idx} variant="outline" className="mb-1 mr-1">
                  {dep}
                </Badge>
              ))}
              {node.dependencies.length > 3 && (
                <Badge variant="outline" className="mb-1 mr-1">
                  +{node.dependencies.length - 3}
                </Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
      <CardFooter className="grid grid-cols-2 gap-2 bg-chart-1 text-xs text-muted-foreground">
        <small className="flex items-center">
          <User size={12} className="mr-1" />
          <span className={cn("truncate")}>{node.author_name}</span>
        </small>
        <small className="flex items-center justify-end">
          <Calendar size={12} className="mr-1" />
          {formatDate(node.creation_timestamp)}
        </small>
      </CardFooter>
    </Card>
  );
};
