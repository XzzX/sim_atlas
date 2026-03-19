import React from "react";
import { NodeMetadata, NodeType } from "../types/index";
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
import { TabsContent, TabsList, Tabs, TabsTrigger } from "@/components/ui/tabs";

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
    <main className="mx-auto w-full max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8"></main>
  );
};
