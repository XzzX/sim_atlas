import {
    BaseNode,
    BaseNodeContent,
    BaseNodeFooter,
    BaseNodeHeader,
    BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";
import { Rocket } from "lucide-react";
import { memo } from "react";
import { type NodeProps, Position, Handle, ReactFlowProvider } from "@xyflow/react";
import { type NodeResponse } from "./NodeResponse"

const WorkflowNode = function ({ data }: { data: NodeResponse }) {
    return (
        <BaseNode>
            <BaseNodeHeader>
                <BaseNodeHeaderTitle>
                    {data.python_import ?? <code>source_code_hash: {data.source_code_hash}</code>}
                </BaseNodeHeaderTitle>
            </BaseNodeHeader>
            <BaseNodeContent>
                <div className="flex flex-row">
                    <div className="flex-1">
                        {Object.entries(data.inputs).map(([k, v]) => (
                            <LabeledHandle
                                id={`target-${k}`}
                                title={k}
                                type="target"
                                position={Position.Left}
                                key={k}
                            />
                        ))}
                    </div>
                    <div className="flex-1 align-right">
                        {Object.entries(data.outputs).map(([k, v]) => (
                            <LabeledHandle
                                id={`source-${k}`}
                                title={k}
                                type="source"
                                position={Position.Right}
                                key={k}
                            />
                        ))}
                    </div>
                </div></BaseNodeContent>
        </BaseNode>
    );
};

export default WorkflowNode;