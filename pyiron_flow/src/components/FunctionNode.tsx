import {
    BaseNode,
    BaseNodeContent,
    BaseNodeHeader,
    BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";
import { Position, useNodeConnections } from "@xyflow/react";
import { type NodeResponse } from "../interfaces/NodeResponse"

import {
    NodeTooltip,
    NodeTooltipContent,
    NodeTooltipTrigger,
} from "@/components/node-tooltip";
import { annotationMatchesFilter, type FilterState } from "@/interfaces/FilterState";

const InputHandle = (props) => {
    const connections = useNodeConnections({
        handleType: props.type,
        handleId: props.id,
    });

    return (
        <LabeledHandle
            {...props}
            className={!props.has_default_value && connections.length === 0 ? 'bg-warning' : ''}
            isConnectable={connections.length < props.connectionCount}
        />
    );
};

export type FunctionNode = Node<
    {
        initialCount?: number;
    },
    'counter'
>;

const FunctionNode = function ({ data }: { data: NodeResponse }) {

    const filter: FilterState = {
        filterType: 'inputs',
    }

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
                                <InputHandle
                                    id={`${v.label ?? k}`}
                                    title={k}
                                    type="target"
                                    position={Position.Left}
                                    key={k}
                                    connectionCount={1}
                                    has_default_value={v.has_default_value}
                                />
                            ))}
                        </div>
                        <div className="flex-1">
                            {Object.entries(data.outputs).map(([k, v]) => (
                                <LabeledHandle
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

export default FunctionNode;