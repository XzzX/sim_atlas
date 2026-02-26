import {
    BaseNode,
    BaseNodeContent,
    BaseNodeHeader,
    BaseNodeHeaderTitle,
} from "@/components/base-node";
import { LabeledHandle } from "@/components/labeled-handle";
import { Position, useNodeConnections, type HandleType } from "@xyflow/react";
import { type NodeResponse } from "../interfaces/NodeResponse"
import { HighlightHandleContext } from "@/HighlightHandleContext";
import { useContext } from "react";
import { type Annotation } from "../interfaces/NodeResponse";

import {
    NodeTooltip,
    NodeTooltipContent,
    NodeTooltipTrigger,
} from "@/components/node-tooltip";
import { annotationMatchesFilter, type FilterState } from "@/interfaces/FilterState";

const InputHandle = ({ title, type, id, annotation, connectionCount, position }: { title: string; type: HandleType; id: string; annotation: Annotation; connectionCount: number; position: Position }) => {
    const handleFilter = useContext(HighlightHandleContext);
    const connections = useNodeConnections({
        handleType: type,
        handleId: id,
    });

    const getClassName = (): string => {
        if (!handleFilter) {
            return !annotation.has_default_value && connections.length === 0 ? 'bg-warning' : '';
        }
        if (handleFilter.filterType === 'outputs') {
            return '';
        }
        return annotationMatchesFilter(annotation, handleFilter) ? 'bg-valid' : '';
    }

    const className = getClassName();

    return (
        <LabeledHandle
            title={title}
            type={type}
            position={position}
            id={id}
            className={className}
            isConnectable={connections.length < connectionCount}
        />
    );
};

const OutputHandle = ({ annotation, ...props }: { annotation: Annotation }) => {
    const handleFilter = useContext(HighlightHandleContext);
    const getClassName = (): string => {
        if (!handleFilter) {
            return '';
        }
        if (handleFilter.filterType === 'inputs') {
            return '';
        }
        return annotationMatchesFilter(annotation, handleFilter) ? 'bg-valid' : '';
    }

    const className = getClassName();

    return (
        <LabeledHandle
            className={className}
            {...props}
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

    console.log(data.inputs, data.outputs);

    return (
        <NodeTooltip>
            <NodeTooltipContent position={Position.Top} className="text-left" style={{ whiteSpace: 'pre-wrap' }}>
                <div>
                    <strong>Inputs:</strong>
                    {data.inputs.length > 0 ? (
                        <ul className="ml-4">
                            {data.inputs.map((value, index) => (
                                <li key={index}>
                                    <strong>{value.label} Hallo</strong>: {JSON.stringify(value, null, 2)}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>No inputs</p>
                    )}
                </div>
                <div>
                    <strong>Outputs:</strong>
                    {data.outputs.length > 0 ? (
                        <ul className="ml-4">
                            {data.outputs.map((value, index) => (
                                <li key={index}>
                                    <strong>{value.label}</strong>: {JSON.stringify(value, null, 2)}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>No outputs</p>
                    )}
                </div>
            </NodeTooltipContent>
            <BaseNode>
                <BaseNodeHeader className="border-b">
                    <BaseNodeHeaderTitle>
                        <NodeTooltipTrigger>
                            {data.python_import?.split('.').pop() ?? ''}
                        </NodeTooltipTrigger>
                    </BaseNodeHeaderTitle>
                </BaseNodeHeader>
                <BaseNodeContent className='pl-0 pr-0 pt-3 pb-3'>
                    <div className="flex flex-row">
                        <div className="flex-1">
                            {data.inputs.map((value, index) => (
                                <InputHandle
                                    id={value.label}
                                    title={value.label}
                                    type="target"
                                    position={Position.Left}
                                    key={index}
                                    connectionCount={1}
                                    annotation={value}
                                />
                            ))}
                        </div>
                        <div className="flex-1">
                            {data.outputs.map((value, index) => (
                                <OutputHandle
                                    id={value.label}
                                    title={value.label}
                                    type="source"
                                    position={Position.Right}
                                    key={index}
                                    annotation={value}
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