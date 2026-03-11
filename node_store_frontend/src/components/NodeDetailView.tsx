import React from "react";
import { NodeMetadata } from "../types/index";
import {
  Code,
  User,
  Calendar,
  Box,
  GitBranch,
  Zap,
  ArrowLeft,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  TabsContent,
  TabsList,
  TabsRoot,
  TabsTrigger,
} from "@/components/ui/tabs";

interface NodeDetailViewProps {
  node: NodeMetadata;
  onClose: () => void;
}

export const NodeDetailView: React.FC<NodeDetailViewProps> = ({
  node,
  onClose,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8">
      <Button variant="ghost" className="mb-1" onClick={onClose}>
        <ArrowLeft size={18} className="mr-2" />
        Back to Search
      </Button>

      <div>
        <h1 className="mb-3 text-2xl font-semibold tracking-tight">
          {node.python_import}
        </h1>
        <div className="mb-1 flex flex-wrap gap-2">
          <Badge variant="secondary">{node.node_type}</Badge>
          {node.node_type === "function" && (
            <Badge variant="outline">Function</Badge>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="h-full">
          <CardContent className="space-y-4 pt-4">
            <div>
              <p className="mb-1 flex items-center text-xs text-muted-foreground">
                <User size={14} className="mr-2" />
                Author
              </p>
              <p className="font-medium">{node.author_name}</p>
              <p className="text-sm text-muted-foreground">
                {node.author_email}
              </p>
            </div>
            <div className="h-px bg-border" />
            <div>
              <p className="mb-1 flex items-center text-xs text-muted-foreground">
                <User size={14} className="mr-2" />
                Creator
              </p>
              <p className="font-medium">{node.creator_name}</p>
              <p className="text-sm text-muted-foreground">
                {node.creator_email}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardContent className="space-y-4 pt-4">
            <div>
              <p className="mb-1 flex items-center text-xs text-muted-foreground">
                <Calendar size={14} className="mr-2" />
                Created
              </p>
              <p className="font-medium">
                {formatDate(node.creation_timestamp)}
              </p>
            </div>
            <div className="h-px bg-border" />
            <div>
              <p className="mb-1 flex items-center text-xs text-muted-foreground">
                <Code size={14} className="mr-2" />
                Source Hash
              </p>
              <code className="break-all text-sm">{node.source_code_hash}</code>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Documentation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-3">
            <h3 className="mb-1 text-sm font-semibold text-muted-foreground">
              Description
            </h3>
            <p>{node.docstring || "No description available"}</p>
          </div>
          {node.ai_docstring && (
            <div>
              <h3 className="mb-1 text-sm font-semibold text-muted-foreground">
                AI Generated Summary
              </h3>
              <div className="rounded-md border bg-muted/40 p-3">
                <p className="mb-0">{node.ai_docstring}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <TabsRoot defaultValue="inputs">
        <TabsList>
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

        <TabsContent value="inputs">
          <Card>
            <CardContent className="pt-4">
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
                            <code>{input.label || "-"}</code>
                          </td>
                          <td className="py-2 pr-3">
                            {input.datatype ? (
                              <Badge variant="outline">{input.datatype}</Badge>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                          <td className="py-2 pr-3">{input.unit || "-"}</td>
                          <td className="py-2 pr-3">{input.quantity || "-"}</td>
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
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="outputs">
          <Card>
            <CardContent className="pt-4">
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
                            <code>{output.label || "-"}</code>
                          </td>
                          <td className="py-2 pr-3">
                            {output.datatype ? (
                              <Badge variant="outline">{output.datatype}</Badge>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                          <td className="py-2 pr-3">{output.unit || "-"}</td>
                          <td className="py-2 pr-3">
                            {output.quantity || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dependencies">
          <Card>
            <CardContent className="pt-4">
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
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="source">
          <Card>
            <CardContent className="pt-4">
              <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                <code>{node.source_code}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </TabsRoot>
    </main>
  );
};
