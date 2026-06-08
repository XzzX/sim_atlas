import React from "react";
import { type ArtifactResponse } from "../../types/index";
import { Calendar, BookAIcon, FilePlusCornerIcon } from "lucide-react";
import { CardFooter } from "@/components/ui/card";

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

interface ArtifactFooterProps {
  node: ArtifactResponse;
}

export const ArtifactFooter: React.FC<ArtifactFooterProps> = ({ node }) => {
  return (
    <CardFooter className="grid grid-cols-3 gap-2 bg-chart-1">
      <div className="flex items-center">
        <BookAIcon size={12} className="mr-1" />
        <span>
          {node.author_name} ({node.author_email})
        </span>
      </div>
      <div className="flex items-center justify-center">
        <FilePlusCornerIcon size={12} className="mr-1" />
        <span>
          {node.creator_name} ({node.creator_email})
        </span>
      </div>
      <div className="flex items-center justify-end">
        <Calendar size={12} className="mr-1" />
        {formatDate(node.creation_timestamp)}
      </div>
    </CardFooter>
  );
};
