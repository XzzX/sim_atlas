import {
    BaseNode,
    BaseNodeContent,
    BaseNodeFooter,
    BaseNodeHeader,
    BaseNodeHeaderTitle,
} from "@/components/base-node";
import { Button } from "@/components/ui/button";
import { InfoIcon } from 'lucide-react'
import { LabeledHandle } from "@/components/labeled-handle";
import { type NodeProps, Position, Handle, ReactFlowProvider } from "@xyflow/react";
import { type NodeResponse } from "./NodeResponse"

import {
    NodeTooltip,
    NodeTooltipContent,
    NodeTooltipTrigger,
} from "@/components/node-tooltip";

const WorkflowNode = function ({ data }: { data: NodeResponse }) {

    return (
        <NodeTooltip>
            <NodeTooltipContent position={Position.Top} className="text-left" style={{ whiteSpace: 'pre-wrap' }}>
                {data.docstring !== '' ? data.docstring : 'No description available.'}
            </NodeTooltipContent>
            <BaseNode>
                <BaseNodeHeader className="border-b">
                    <BaseNodeHeaderTitle>
                        <NodeTooltipTrigger>
                            {data.python_import ?? ''}
                        </NodeTooltipTrigger>
                    </BaseNodeHeaderTitle>
                </BaseNodeHeader>
                <BaseNodeContent className='pl-0 pr-0 pt-3 pb-3'>
                    <div className="flex flex-row">
                        <div className="flex-1">
                            {Object.entries(data.inputs).map(([k, v]) => (
                                <LabeledHandle
                                    id={`${v.label ?? k}`}
                                    title={k}
                                    type="target"
                                    position={Position.Left}
                                    key={k}
                                />
                            ))}
                        </div>
                        <div className="flex-1">
                            {Object.entries(data.outputs).map(([k, v]) => (
                                <LabeledHandle
                                    className='items-right flex-end'
                                    id={`${v.label ?? k}`}
                                    title={k}
                                    type="source"
                                    position={Position.Right}
                                    key={k}
                                />
                            ))}
                        </div>
                    </div>
                </BaseNodeContent>
            </BaseNode>
        </NodeTooltip >
    );
};

export default WorkflowNode;