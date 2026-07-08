import React from "react";
import { type Annotation, type Reference } from "../../types/index";
import { Code, GitBranch, GitFork, Box, Zap, Link2, Share2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TabsContent, TabsList, Tabs, TabsTrigger } from "@/components/ui/tabs";

interface ArtifactDetailsProps {
  inputs?: Annotation[];
  outputs?: Annotation[];
  dependencies?: string[];
  source_code?: string;
  definition?: Record<string, unknown>;
  see_also?: Reference[];
  uses?: Reference[];
  used_by?: Reference[] | null;
  onReferenceClick?: (id: string) => void;
}

export const ArtifactDetails: React.FC<ArtifactDetailsProps> = ({
  inputs,
  outputs,
  dependencies,
  source_code,
  definition,
  see_also,
  uses,
  used_by,
  onReferenceClick,
}) => {
  const hasSeeAlso = see_also && see_also.length > 0;
  const hasUses = uses && uses.length > 0;
  const hasUsedBy = used_by && used_by.length > 0;

  return (
    <>
      <CardContent className="space-y-4">
        <Tabs defaultValue="inputs">
          <TabsList variant="line">
            {inputs && (
              <TabsTrigger value="inputs">
                <Zap size={14} className="mr-2" />
                Inputs ({inputs?.length ?? 0})
              </TabsTrigger>
            )}
            {outputs && (
              <TabsTrigger value="outputs">
                <Box size={14} className="mr-2" />
                Outputs ({outputs?.length ?? 0})
              </TabsTrigger>
            )}
            {dependencies && (
              <TabsTrigger value="dependencies">
                <GitBranch size={14} className="mr-2" />
                Dependencies ({dependencies.length})
              </TabsTrigger>
            )}
            {source_code && (
              <TabsTrigger value="source">
                <Code size={14} className="mr-2" />
                Source Code
              </TabsTrigger>
            )}
            {definition && (
              <TabsTrigger value="workflow_definition">
                <GitBranch size={14} className="mr-2" />
                Workflow Definition
              </TabsTrigger>
            )}
            {hasSeeAlso && (
              <TabsTrigger value="see_also">
                <Link2 size={14} className="mr-2" />
                See Also ({see_also.length})
              </TabsTrigger>
            )}
            {hasUses && (
              <TabsTrigger value="uses">
                <GitFork size={14} className="mr-2" />
                Uses ({uses.length})
              </TabsTrigger>
            )}
            {hasUsedBy && (
              <TabsTrigger value="used_by">
                <Share2 size={14} className="mr-2" />
                Used By ({used_by.length})
              </TabsTrigger>
            )}
          </TabsList>

          <Card className="border-2">
            <CardContent>
              {inputs && (
                <TabsContent value="inputs">
                  {inputs?.length === 0 ? (
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
                          {inputs?.map((input, idx) => (
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
                </TabsContent>)}

              {outputs && (
                <TabsContent value="outputs">
                  {outputs.length === 0 ? (
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
                          {outputs.map((output, idx) => (
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
                </TabsContent>)}

              {dependencies && (
                <TabsContent value="dependencies">
                  {!dependencies || dependencies.length === 0 ? (
                    <p className="mb-0 text-muted-foreground">No dependencies</p>
                  ) : (
                    <div className="space-y-2">
                      {dependencies.map((dep, idx) => (
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

              {source_code && (
                <TabsContent value="source">
                  <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                    <code>{source_code}</code>
                  </pre>
                </TabsContent>
              )}

              {definition && (
                <TabsContent value="workflow_definition">
                  <pre className="max-h-[500px] overflow-auto rounded-md bg-muted p-3 text-sm">
                    <code>{JSON.stringify(definition, null, 2)}</code>
                  </pre>
                </TabsContent>
              )}

              {hasSeeAlso && (
                <TabsContent value="see_also">
                  <div className="flex flex-wrap gap-1">
                    {see_also.map((ref) => (
                      <Badge
                        key={ref.id}
                        variant="outline"
                        className={onReferenceClick ? "cursor-pointer" : ""}
                        onClick={() => onReferenceClick?.(ref.id)}
                      >
                        {ref.label}
                      </Badge>
                    ))}
                  </div>
                </TabsContent>
              )}

              {hasUses && (
                <TabsContent value="uses">
                  <div className="flex flex-wrap gap-1">
                    {uses.map((ref) => (
                      <Badge
                        key={ref.id}
                        variant="outline"
                        className={onReferenceClick ? "cursor-pointer" : ""}
                        onClick={() => onReferenceClick?.(ref.id)}
                      >
                        {ref.label}
                      </Badge>
                    ))}
                  </div>
                </TabsContent>
              )}

              {hasUsedBy && (
                <TabsContent value="used_by">
                  <div className="flex flex-wrap gap-1">
                    {used_by.map((ref) => (
                      <Badge
                        key={ref.id}
                        variant="outline"
                        className={onReferenceClick ? "cursor-pointer" : ""}
                        onClick={() => onReferenceClick?.(ref.id)}
                      >
                        {ref.label}
                      </Badge>
                    ))}
                  </div>
                </TabsContent>
              )}

            </CardContent>
          </Card>
        </Tabs>
      </CardContent>
    </>
  );
};
