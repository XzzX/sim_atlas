import React from "react";
import { Badge } from "@/components/ui/badge";
import { CardContent } from "@/components/ui/card";

interface ArtifactMiscProps {
  keywords?: string[];
}

export const ArtifactMisc: React.FC<ArtifactMiscProps> = ({ keywords }) => {
  return (
    <>
      <CardContent>
        {keywords && keywords.length > 0 && (
          <div className="mb-3">
            <small className="mb-2 block text-muted-foreground">
              <strong>Keywords</strong>
            </small>
            <div>
              {keywords.map((keyword, idx) => (
                <Badge key={idx} variant="secondary" className="mb-1 mr-1">
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </>
  );
};
