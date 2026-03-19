import React from "react";
import { NodeMetadata, NodeType } from "../types/index";
import {
  User,
  Calendar,
  ClipboardCopyIcon,
  ExternalLinkIcon,
  FileDownIcon,
  Code,
  GitBranch,
  Box,
  Zap,
  HouseIcon,
  BookIcon,
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
import { ButtonGroup } from "./ui/button-group";
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group";
import { TabsContent, TabsList, Tabs, TabsTrigger } from "./ui/tabs";

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
  const [useAISummary, setUseAISummary] = React.useState(false);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const handleDownload = (filename: string, content: string) => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();

    URL.revokeObjectURL(url);
  };

  return (
    <Card
      className="h-full cursor-pointer pt-0 border-1 border-chart-1"
      // onClick={() => onSelect?.(node)}
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
          {node.python_import && (
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
          {node.node_type === NodeType.PYTHON_WORKFLOW_DEFINITION && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                window.open("ide/?wf_hash=" + node.source_code_hash);
              }}
            >
              <ExternalLinkIcon />
              Web IDE
            </Button>
          )}
          {node.node_type === NodeType.PYTHON_WORKFLOW_DEFINITION && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleDownload(node.python_import + ".json", node.source_code);
              }}
            >
              <FileDownIcon />
              Download
            </Button>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="inputs">
          <TabsList variant="line">
            <TabsTrigger value="human_description">
              <Zap size={14} className="mr-2" />
              Description
            </TabsTrigger>
            <TabsTrigger value="ai_description">
              Ai Generated Description
            </TabsTrigger>
          </TabsList>

          <Card className="border-2">
            <CardContent>
              <TabsContent value="human_description">
                <p className="whitespace-pre-wrap">
                  {node.docstring || "No description available"}
                </p>
              </TabsContent>
              <TabsContent value="ai_description">
                <p className="whitespace-pre-wrap">
                  {node.ai_docstring || "No description available"}
                </p>
              </TabsContent>
            </CardContent>
          </Card>
        </Tabs>
      </CardContent>
      <CardContent className="space-y-4">
        <Tabs defaultValue="inputs">
          <TabsList variant="line">
            <TabsTrigger value="inputs">
              <Zap size={14} className="mr-2" />
              Inputs ({node.inputs.length})
            </TabsTrigger>
            <TabsTrigger value="outputs">
              <Box size={14} className="mr-2" />
              Outputs ({node.outputs.length})
            </TabsTrigger>
            <TabsTrigger value="dependencies">
              <GitBranch size={14} className="mr-2" />
              Dependencies ({node.dependencies ? node.dependencies.length : 0})
            </TabsTrigger>
            <TabsTrigger value="source">
              <Code size={14} className="mr-2" />
              Source Code
            </TabsTrigger>
          </TabsList>

          <Card className="border-2">
            <CardContent>
              <TabsContent value="inputs">
                {node.inputs.length === 0 ? (
                  <p className="mb-0 text-muted-foreground">No inputs</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-muted-foreground">
                          <th className="py-2 pr-3">Label</th>
                          <th className="py-2 pr-3">Data Type</th>
                          <th className="py-2 pr-3">Unit</th>
                          <th className="py-2 pr-3">Quantity</th>
                          <th className="py-2 pr-3">Default</th>
                        </tr>
                      </thead>
                      <tbody>
                        {node.inputs.map((input, idx) => (
                          <tr key={idx} className="border-b last:border-b-0">
                            <td className="py-2 pr-3">
                              <code>{input.label ?? "-"}</code>
                            </td>
                            <td className="py-2 pr-3">
                              {input.datatype ? (
                                <Badge variant="outline">
                                  {input.datatype}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="py-2 pr-3">{input.unit ?? "-"}</td>
                            <td className="py-2 pr-3">
                              {input.quantity ?? "-"}
                            </td>
                            <td className="py-2 pr-3">
                              {input.has_default_value ? (
                                <Badge variant="success">Yes</Badge>
                              ) : (
                                <Badge variant="outline">No</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="outputs">
                {node.outputs.length === 0 ? (
                  <p className="mb-0 text-muted-foreground">No outputs</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-muted-foreground">
                          <th className="py-2 pr-3">Label</th>
                          <th className="py-2 pr-3">Data Type</th>
                          <th className="py-2 pr-3">Unit</th>
                          <th className="py-2 pr-3">Quantity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {node.outputs.map((output, idx) => (
                          <tr key={idx} className="border-b last:border-b-0">
                            <td className="py-2 pr-3">
                              <code>{output.label ?? "-"}</code>
                            </td>
                            <td className="py-2 pr-3">
                              {output.datatype ? (
                                <Badge variant="outline">
                                  {output.datatype}
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="py-2 pr-3">{output.unit ?? "-"}</td>
                            <td className="py-2 pr-3">
                              {output.quantity ?? "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="dependencies">
                {!node.dependencies || node.dependencies.length === 0 ? (
                  <p className="mb-0 text-muted-foreground">No dependencies</p>
                ) : (
                  <div className="space-y-2">
                    {node.dependencies.map((dep, idx) => (
                      <code
                        key={idx}
                        className="block rounded-md bg-muted px-2 py-1"
                      >
                        {dep}
                      </code>
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="source">
                <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                  <code>{node.source_code}</code>
                </pre>
              </TabsContent>
            </CardContent>
          </Card>
        </Tabs>
      </CardContent>
      <CardContent>
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
