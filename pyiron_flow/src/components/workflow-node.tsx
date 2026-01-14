import { Button } from "@/components/ui/button";
import {
    BaseNode,
    BaseNodeContent,
    BaseNodeFooter,
    BaseNodeHeader,
    BaseNodeHeaderTitle,
} from "@/components/base-node";
import { BaseHandle } from "@/components/base-handle";
import { Rocket } from "lucide-react";
import { memo } from "react";
import { type NodeProps, Position } from "reactflow";

const WorkflowNode = memo(() => {
    return (
        <BaseNode>
            <BaseNodeContent>
                <BaseHandle id="target-1" type="target" position={Position.Left} />
                <div>A node with two handles</div>
                <BaseHandle id="source-1" type="source" position={Position.Right} />
            </BaseNodeContent>
        </BaseNode>
    );
});

export default WorkflowNode;