import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { TabsContent, TabsList, Tabs, TabsTrigger } from "@/components/ui/tabs";
import { Zap } from "lucide-react";

interface ArtifactDescriptionProps {
  docstring?: string;
  description?: string;
}

export const ArtifactDescription: React.FC<ArtifactDescriptionProps> = ({ docstring, description }) => {
  return (
    <>
      <CardContent className="space-y-4">
        <Tabs
          defaultValue={
            description && !docstring
              ? "description"
              : "docstring"
          }
        >
          <TabsList variant="line">
            <TabsTrigger value="docstring">
              <Zap size={14} className="mr-2" />
              Docstring
            </TabsTrigger>
            <TabsTrigger value="description">
              Description
            </TabsTrigger>
          </TabsList>

          <Card className="border-2">
            <CardContent>
              <TabsContent value="docstring">
                <p className="whitespace-pre-wrap">
                  {docstring ?? "No docstring available"}
                </p>
              </TabsContent>
              <TabsContent value="description">
                <p className="whitespace-pre-wrap">
                  {description ?? "No description available"}
                </p>
              </TabsContent>
            </CardContent>
          </Card>
        </Tabs>
      </CardContent>
    </>
  );
};
