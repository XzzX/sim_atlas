import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _():
    from typing import Any, List, Optional, Dict, Union
    from pydantic import BaseModel, Field

    # -----------------------
    # Metadata & IO
    # -----------------------

    class Annotation(BaseModel):
        label: str

    class Metadata(BaseModel):
        python_import: str
        outputs: list[Annotation]


    # -----------------------
    # Node data variants
    # -----------------------

    class FunctionNodeData(BaseModel):
        metadata: Metadata


    class InputNodeData(BaseModel):
        label: str
        value: Any


    class OutputNodeData(BaseModel):
        label: str
    
    class TernaryNodeData(BaseModel):
        label: str

    class RecursionNodeData(BaseModel):
        label: str

    NodeData = Union[
        FunctionNodeData,
        InputNodeData,
        OutputNodeData,
        TernaryNodeData,
        RecursionNodeData,
    ]


    # -----------------------
    # Node
    # -----------------------

    class Node(BaseModel):
        id: str
        data: NodeData
        type: str


    # -----------------------
    # Edge
    # -----------------------

    class Edge(BaseModel):
        id: str
        source: str
        target: str

        sourceHandle: Optional[str] = None
        targetHandle: Optional[str] = None


    # -----------------------
    # Root workflow model
    # -----------------------

    class WorkflowGraph(BaseModel):
        nodes: List[Node]
        edges: List[Edge]
    return (
        Annotation,
        Any,
        Edge,
        FunctionNodeData,
        InputNodeData,
        Metadata,
        Node,
        OutputNodeData,
        RecursionNodeData,
        TernaryNodeData,
        WorkflowGraph,
    )


@app.cell
def _(Any, Node, WorkflowGraph):
    from collections.abc import Callable
    import importlib
    import sys
    import logging

    class InputNode:
        def __init__(self, id: str, value: Any):
            self.id = id
            self.value = value

        def __call__(self):
            logging.info(f'InputNode {self.id} returning value: {self.value}')
            return {'result': self.value}

    class OutputNode:
        def __init__(self, id: str):
            self.id = id
            self.incoming_edges: list[tuple[Callable[[], Any], str, str]] = []

        def __call__(self):
            output = {'result': source_node()[source_port] if source_port else next(iter(source_node().values())) for source_node, source_port, target_port in self.incoming_edges}
            logging.info(f'OutputNode {self.id} returning value: {output}')
            return output

    class FunctionNode:
        def __init__(self, id: str, func: str, output_labels: list[str]):
            self.id = id
        
            self.outputs: dict[str, Any] | None = None
            self.output_labels = output_labels
        
            module_path, _, func_name = func.rpartition('.')
            if module_path == "__main__":
                module = sys.modules["__main__"]
            else:
                module = importlib.import_module(module_path)
            self.func = getattr(module, func_name)

            self.incoming_edges : list[tuple[Callable[[], Any], str, str]] = []

        def __call__(self) -> dict[str, Any]:
            if self.outputs:
                return self.outputs

            inputs = {target_port: source_node()[source_port] if source_port else next(iter(source_node().values())) for source_node, source_port, target_port in self.incoming_edges}
            import inspect
            sig = inspect.signature(self.func)
            pos_only = [inputs[k] for k, v in sig.parameters.items() if v.kind in (v.POSITIONAL_ONLY, v.POSITIONAL_OR_KEYWORD)]
            kw_only = {k: inputs[k] for k, v in sig.parameters.items() if v.kind == v.KEYWORD_ONLY}
            logging.debug(f'FunctionNode {self.id} calling {self.func} with pos_only={pos_only}, kw_only={kw_only}')
            outputs = self.func(*pos_only, **kw_only)

            if len(self.output_labels) > 1:
                self.outputs = {k: v for k, v in zip(self.output_labels, outputs)}
            else:
                self.outputs = {self.output_labels[0]: outputs}
            
            logging.info(f'FunctionNode {self.id} returning outputs: {self.outputs}')
            return self.outputs

    class TernaryNode:
        def __init__(self, id: str):
            self.id = id
            self.outputs: dict[str, Any] | None = None
        
            self.incoming_edges : list[tuple[Callable[[], Any], str, str]] = []

        def __call__(self):
            if self.outputs:
                return self.outputs

            source_node, source_port, _ = next(edge for edge in self.incoming_edges if edge[2]=='if')
            condition = source_node()[source_port] if source_port else next(iter(source_node().values()))

            if condition:
                source_node, source_port, _ = next(edge for edge in self.incoming_edges if edge[2]=='then')
                self.outputs = {'result': source_node()[source_port] if source_port else next(iter(source_node().values()))}
            else:
                source_node, source_port, _ = next(edge for edge in self.incoming_edges if edge[2]=='else')
                self.outputs = {'result': source_node()[source_port] if source_port else next(iter(source_node().values()))}

            logging.info(f'TernaryNode {self.id} returning outputs: {self.outputs}')
            return self.outputs

    class RecursionNode:
        def __init__(self, id: str, gui_graph: WorkflowGraph):
            self.outputs: dict[str, Any] | None = None
            self.id = id
            self.gui_graph = gui_graph

        def __call__(self) -> dict[str, Any]:
            if self.outputs:
                return self.outputs
            
            wf_nodes = {node.id: node for node in map(lambda n: convert_node(n, self.gui_graph), self.gui_graph.nodes)}
            for id, node in wf_nodes.items():
                node.incoming_edges = list(map(lambda e: (wf_nodes[e.source], e.sourceHandle, e.targetHandle), filter(lambda e: e.target == node.id, self.gui_graph.edges)))

            inputs = {target_port: source_node()[source_port] if source_port else next(iter(source_node().values())) for source_node, source_port, target_port in self.incoming_edges}
            for input_name, input_value in inputs.items():
                wf_nodes[input_name].value = input_value

            self.outputs = {output_node.id: next(iter(output_node().values())) for output_node in wf_nodes.values() if isinstance(output_node, OutputNode)}

            logging.info(f'RecursionNode {self.id} returning outputs: {self.outputs}')
            return self.outputs
        
    def convert_node(node: Node, current_graph: WorkflowGraph):
        match (node.type):
            case "InputNode":
                return InputNode(node.id, node.data.value)
            case "OutputNode":
                return OutputNode(node.id)
            case "FunctionNode":
                return FunctionNode(node.id, node.data.metadata.python_import, [o.label for o in node.data.metadata.outputs])
            case "TernaryNode":
                return TernaryNode(node.id)
            case "RecursionNode":
                return RecursionNode(node.id, current_graph)
            case _:
                return None
    return FunctionNode, InputNode, TernaryNode, convert_node, logging


@app.cell
def _(WorkflowGraph, convert_node, logging):
    def test_pwd():
        import json

        with open('wf.json', 'r') as fin:
            gui_wf = json.loads(fin.read())
        gui_graph = WorkflowGraph.model_validate(gui_wf)
    
        logging.getLogger().setLevel(logging.DEBUG)
    
        wf_nodes = {node.id: node for node in map(lambda n: convert_node(n, gui_graph), gui_graph.nodes)}
        for id, node in wf_nodes.items():
            node.incoming_edges = list(map(lambda e: (wf_nodes[e.source], e.sourceHandle, e.targetHandle), filter(lambda e: e.target == node.id, gui_graph.edges)))
        return wf_nodes["21"]()
    test_pwd()
    return


@app.cell
def _(InputNode, TernaryNode):
    def test_ternary():
        inp0 = InputNode('inp0', False)
        inp1 = InputNode('inp1', 10)
        inp2 = InputNode('inp2', 15)
        ternary = TernaryNode('ternary')
        ternary.incoming_edges = [
            (inp0, None, 'if'),
            (inp1, None, 'then'),
            (inp2, None, 'else'),
        ]
        return ternary()
    test_ternary()
    return


@app.cell
def _(FunctionNode, InputNode):
    def test_operator():
        inp0 = InputNode('inp0', 5)
        inp1 = InputNode('inp1', 2)
        inp2 = InputNode('inp2', 2)
        pow = FunctionNode('pow', 'operator.pow', ['result'])
        pow.incoming_edges = [
            (inp1, None, 'a'),
            (inp2, None, 'b'),
        ]
        return pow()
    test_operator()
    return


@app.cell
def _(
    Annotation,
    Edge,
    FunctionNodeData,
    InputNodeData,
    Metadata,
    Node,
    OutputNodeData,
    RecursionNodeData,
    TernaryNodeData,
    WorkflowGraph,
    convert_node,
):
    def test_recursion():
        wf = WorkflowGraph(nodes=[], edges=[])
    
        wf.nodes.append(Node(id='iterations', data=InputNodeData(label='iterations', value=5), type='InputNode'))
        wf.nodes.append(Node(id='bound', data=InputNodeData(label='bound', value=0), type='InputNode'))
        wf.nodes.append(Node(id='value', data=InputNodeData(label='value', value=2), type='InputNode'))
        wf.nodes.append(Node(id='factor', data=InputNodeData(label='factor', value=2), type='InputNode'))
        wf.nodes.append(Node(id='const_1', data=InputNodeData(label='const_1', value=1), type='InputNode'))
    
        wf.nodes.append(Node(id='cond', data=FunctionNodeData(metadata=Metadata(python_import='operator.lt', outputs=[Annotation(label='result')])), type='FunctionNode'))
        wf.edges.append(Edge(id='e0', source='iterations', target='cond', sourceHandle=None, targetHandle='a'))
        wf.edges.append(Edge(id='e1', source='bound', target='cond', sourceHandle=None, targetHandle='b'))
    
        wf.nodes.append(Node(id='minus_1', data=FunctionNodeData(metadata=Metadata(python_import='operator.sub', outputs=[Annotation(label='result')])), type='FunctionNode'))
        wf.edges.append(Edge(id='e2', source='iterations', target='minus_1', sourceHandle=None, targetHandle='a'))
        wf.edges.append(Edge(id='e3', source='const_1', target='minus_1', sourceHandle=None, targetHandle='b'))
    
        wf.nodes.append(Node(id='factorial_step', data=FunctionNodeData(metadata=Metadata(python_import='operator.mul', outputs=[Annotation(label='result')])), type='FunctionNode'))
        wf.edges.append(Edge(id='e9', source='value', target='factorial_step', sourceHandle=None, targetHandle='a'))
        wf.edges.append(Edge(id='e10', source='factor', target='factorial_step', sourceHandle=None, targetHandle='b'))
    
        wf.nodes.append(Node(id='recursion', data=RecursionNodeData(label='recursion'), type='RecursionNode'))
        wf.edges.append(Edge(id='e7', source='minus_1', target='recursion', sourceHandle='result', targetHandle='iterations'))
        wf.edges.append(Edge(id='e8', source='factorial_step', target='recursion', sourceHandle=None, targetHandle='value'))
    
        wf.nodes.append(Node(id='ternary', data=TernaryNodeData(label='ternary'), type='TernaryNode'))
        wf.edges.append(Edge(id='e4', source='cond', target='ternary', sourceHandle='result', targetHandle='if'))
        wf.edges.append(Edge(id='e5', source='value', target='ternary', sourceHandle=None, targetHandle='then'))
        wf.edges.append(Edge(id='e6', source='recursion', target='ternary', sourceHandle='out', targetHandle='else'))
    
        wf.nodes.append(Node(id='out', data=OutputNodeData(label='out'), type='OutputNode'))
        wf.edges.append(Edge(id='e11', source='ternary', target='out', sourceHandle=None, targetHandle=None))
    
        wf_nodes = {node.id: node for node in map(lambda n: convert_node(n, wf), wf.nodes)}
        for id, node in wf_nodes.items():
            node.incoming_edges = list(map(lambda e: (wf_nodes[e.source], e.sourceHandle, e.targetHandle), filter(lambda e: e.target == node.id, wf.edges)))
        return wf_nodes["out"]()
    test_recursion()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
