import React from "react";
import { Badge } from "@/components/ui/badge";
import { CardContent } from "@/components/ui/card";
import { type Reference } from "@/types/index";

interface ArtifactMiscProps {
  keywords?: string[];
  see_also?: Reference[];
  child_nodes?: Reference[];
  onReferenceClick?: (id: string) => void;
}

export const ArtifactMisc: React.FC<ArtifactMiscProps> = ({
  keywords,
  see_also,
  child_nodes,
  onReferenceClick,
}) => {
  const hasSeeAlso = see_also && see_also.length > 0;
  const hasChildren = child_nodes && child_nodes.length > 0;

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
        {hasSeeAlso && (
          <div className="mb-3">
            <small className="mb-2 block text-muted-foreground">
              <strong>See also</strong>
            </small>
            <div>
              {see_also.map((ref) => (
                <Badge
                  key={ref.id}
                  variant="outline"
                  className="mb-1 mr-1 cursor-pointer"
                  onClick={() => onReferenceClick?.(ref.id)}
                >
                  {ref.label}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {hasChildren && (
          <div className="mb-3">
            <small className="mb-2 block text-muted-foreground">
              <strong>Children</strong>
            </small>
            <div>
              {child_nodes.map((ref) => (
                <Badge
                  key={ref.id}
                  variant="outline"
                  className="mb-1 mr-1 cursor-pointer"
                  onClick={() => onReferenceClick?.(ref.id)}
                >
                  {ref.label}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </>
  );
};
