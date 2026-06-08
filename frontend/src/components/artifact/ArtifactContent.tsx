import React from "react";
import { type ArtifactResponse, ArtifactType } from "../../types/index";
import { Code, GitBranch, Box, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TabsContent, TabsList, Tabs, TabsTrigger } from "@/components/ui/tabs";

interface ArtifactContentProps {
  node: ArtifactResponse;
}

export const ArtifactContent: React.FC<ArtifactContentProps> = ({ node }) => {
  return (
    <>
      <CardContent className="space-y-4">
        <Tabs
          defaultValue={
            node.ai_description && !node.docstring
              ? "ai_description"
              : "human_description"
          }
        >
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
                  {node.ai_description || "No description available"}
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
            {node.artifact_type === ArtifactType.function && (
              <TabsTrigger value="dependencies">
                <GitBranch size={14} className="mr-2" />
                Dependencies ({node.dependencies ? node.dependencies.length : 0})
              </TabsTrigger>
            )}
            {node.artifact_type === ArtifactType.function && (
              <TabsTrigger value="source">
                <Code size={14} className="mr-2" />
                Source Code
              </TabsTrigger>
            )}
            {node.artifact_type === ArtifactType.workflow && (
              <TabsTrigger value="workflow_definition">
                <GitBranch size={14} className="mr-2" />
                Workflow Definition
              </TabsTrigger>
            )}
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

              {node.artifact_type === ArtifactType.function && (
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
              )}
              {node.artifact_type === ArtifactType.function && (
                <TabsContent value="source">
                  <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                    <code>{node.source_code}</code>
                  </pre>
                </TabsContent>
              )}
              {node.artifact_type === ArtifactType.workflow && (
                <TabsContent value="workflow_definition">
                  <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                    <code>{JSON.stringify(node.definition, null, 2)}</code>
                  </pre>
                </TabsContent>
              )}
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

        {node.artifact_type === ArtifactType.function &&
          node.dependencies &&
          node.dependencies.length > 0 && (
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
    </>
  );
};
