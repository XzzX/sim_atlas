import * as PWD from "./interfaces/PythonWorkflowDefinition";

export function convertWorkflow(text: string) {
    try {
        const pwd = PWD.Convert.toPythonWorkflowDefinition(text);
        return PWD.toNodesAndEdges(pwd);
    } catch (error) {
        console.error("Failed to convert workflow:", error);
    }
    return { nodes: [], edges: [] };
}