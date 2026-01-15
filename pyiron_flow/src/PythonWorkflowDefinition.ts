import * as xyflow from '@xyflow/react';
import * as node_store from './NodeStore';


// To parse this data:
//
//   import { Convert, PythonWorkflowDefinition } from "./file";
//
//   const pythonWorkflowDefinition = Convert.toPythonWorkflowDefinition(json);
//
// These functions will throw an error if the JSON doesn't
// match the expected interface, even if the JSON is valid.

/**
 * The main workflow model.
 */
export interface PythonWorkflowDefinition {
    edges: PythonWorkflowDefinitionEdge[];
    nodes: Node[];
    version: string;
    [property: string]: any;
}

/**
 * Model for edges connecting nodes.
 */
export interface PythonWorkflowDefinitionEdge {
    source: number;
    sourcePort?: null | string;
    target: number;
    targetPort?: null | string;
    [property: string]: any;
}

/**
 * Model for input nodes.
 *
 * Model for output nodes.
 *
 * Model for function execution nodes.
 * The 'name' attribute is computed automatically from 'value'.
 */
export interface Node {
    id: number;
    name?: string;
    type: Type;
    value?: any;
    [property: string]: any;
}

export enum Type {
    Function = "function",
    Input = "input",
    Output = "output",
}

// Converts JSON strings to/from your types
// and asserts the results of JSON.parse at runtime
export class Convert {
    public static toPythonWorkflowDefinition(json: string): PythonWorkflowDefinition {
        return cast(JSON.parse(json), r("PythonWorkflowDefinition"));
    }

    public static pythonWorkflowDefinitionToJson(value: PythonWorkflowDefinition): string {
        return JSON.stringify(uncast(value, r("PythonWorkflowDefinition")), null, 2);
    }
}

function invalidValue(typ: any, val: any, key: any, parent: any = ''): never {
    const prettyTyp = prettyTypeName(typ);
    const parentText = parent ? ` on ${parent}` : '';
    const keyText = key ? ` for key "${key}"` : '';
    throw Error(`Invalid value${keyText}${parentText}. Expected ${prettyTyp} but got ${JSON.stringify(val)}`);
}

function prettyTypeName(typ: any): string {
    if (Array.isArray(typ)) {
        if (typ.length === 2 && typ[0] === undefined) {
            return `an optional ${prettyTypeName(typ[1])}`;
        } else {
            return `one of [${typ.map(a => { return prettyTypeName(a); }).join(", ")}]`;
        }
    } else if (typeof typ === "object" && typ.literal !== undefined) {
        return typ.literal;
    } else {
        return typeof typ;
    }
}

function jsonToJSProps(typ: any): any {
    if (typ.jsonToJS === undefined) {
        const map: any = {};
        typ.props.forEach((p: any) => map[p.json] = { key: p.js, typ: p.typ });
        typ.jsonToJS = map;
    }
    return typ.jsonToJS;
}

function jsToJSONProps(typ: any): any {
    if (typ.jsToJSON === undefined) {
        const map: any = {};
        typ.props.forEach((p: any) => map[p.js] = { key: p.json, typ: p.typ });
        typ.jsToJSON = map;
    }
    return typ.jsToJSON;
}

function transform(val: any, typ: any, getProps: any, key: any = '', parent: any = ''): any {
    function transformPrimitive(typ: string, val: any): any {
        if (typeof typ === typeof val) return val;
        return invalidValue(typ, val, key, parent);
    }

    function transformUnion(typs: any[], val: any): any {
        // val must validate against one typ in typs
        const l = typs.length;
        for (let i = 0; i < l; i++) {
            const typ = typs[i];
            try {
                return transform(val, typ, getProps);
            } catch (_) { }
        }
        return invalidValue(typs, val, key, parent);
    }

    function transformEnum(cases: string[], val: any): any {
        if (cases.indexOf(val) !== -1) return val;
        return invalidValue(cases.map(a => { return l(a); }), val, key, parent);
    }

    function transformArray(typ: any, val: any): any {
        // val must be an array with no invalid elements
        if (!Array.isArray(val)) return invalidValue(l("array"), val, key, parent);
        return val.map(el => transform(el, typ, getProps));
    }

    function transformDate(val: any): any {
        if (val === null) {
            return null;
        }
        const d = new Date(val);
        if (isNaN(d.valueOf())) {
            return invalidValue(l("Date"), val, key, parent);
        }
        return d;
    }

    function transformObject(props: { [k: string]: any }, additional: any, val: any): any {
        if (val === null || typeof val !== "object" || Array.isArray(val)) {
            return invalidValue(l(ref || "object"), val, key, parent);
        }
        const result: any = {};
        Object.getOwnPropertyNames(props).forEach(key => {
            const prop = props[key];
            const v = Object.prototype.hasOwnProperty.call(val, key) ? val[key] : undefined;
            result[prop.key] = transform(v, prop.typ, getProps, key, ref);
        });
        Object.getOwnPropertyNames(val).forEach(key => {
            if (!Object.prototype.hasOwnProperty.call(props, key)) {
                result[key] = transform(val[key], additional, getProps, key, ref);
            }
        });
        return result;
    }

    if (typ === "any") return val;
    if (typ === null) {
        if (val === null) return val;
        return invalidValue(typ, val, key, parent);
    }
    if (typ === false) return invalidValue(typ, val, key, parent);
    let ref: any = undefined;
    while (typeof typ === "object" && typ.ref !== undefined) {
        ref = typ.ref;
        typ = typeMap[typ.ref];
    }
    if (Array.isArray(typ)) return transformEnum(typ, val);
    if (typeof typ === "object") {
        return typ.hasOwnProperty("unionMembers") ? transformUnion(typ.unionMembers, val)
            : typ.hasOwnProperty("arrayItems") ? transformArray(typ.arrayItems, val)
                : typ.hasOwnProperty("props") ? transformObject(getProps(typ), typ.additional, val)
                    : invalidValue(typ, val, key, parent);
    }
    // Numbers can be parsed by Date but shouldn't be.
    if (typ === Date && typeof val !== "number") return transformDate(val);
    return transformPrimitive(typ, val);
}

function cast<T>(val: any, typ: any): T {
    return transform(val, typ, jsonToJSProps);
}

function uncast<T>(val: T, typ: any): any {
    return transform(val, typ, jsToJSONProps);
}

function l(typ: any) {
    return { literal: typ };
}

function a(typ: any) {
    return { arrayItems: typ };
}

function u(...typs: any[]) {
    return { unionMembers: typs };
}

function o(props: any[], additional: any) {
    return { props, additional };
}

function m(additional: any) {
    return { props: [], additional };
}

function r(name: string) {
    return { ref: name };
}

const typeMap: any = {
    "PythonWorkflowDefinition": o([
        { json: "edges", js: "edges", typ: a(r("PythonWorkflowDefinitionEdge")) },
        { json: "nodes", js: "nodes", typ: a(r("Node")) },
        { json: "version", js: "version", typ: "" },
    ], "any"),
    "PythonWorkflowDefinitionEdge": o([
        { json: "source", js: "source", typ: 0 },
        { json: "sourcePort", js: "sourcePort", typ: u(undefined, u(null, "")) },
        { json: "target", js: "target", typ: 0 },
        { json: "targetPort", js: "targetPort", typ: u(undefined, u(null, "")) },
    ], "any"),
    "Node": o([
        { json: "id", js: "id", typ: 0 },
        { json: "name", js: "name", typ: u(undefined, "") },
        { json: "type", js: "type", typ: r("Type") },
        { json: "value", js: "value", typ: u(undefined, "any") },
    ], "any"),
    "Type": [
        "function",
        "input",
        "output",
    ],
};

export function toNodesAndEdges(workflow: PythonWorkflowDefinition): { nodes: xyflow.Node[]; edges: xyflow.Edge[] } {
    var filtered_nodes = workflow.nodes.filter(n => n.type === 'function');

    const nodes: xyflow.Node[] = filtered_nodes.map(n => ({
        id: n.id.toString(),
        data: node_store.nodes.find(node => node.python_import === n.value)!,
        position: { x: Math.random() * 400, y: Math.random() * 400 }, // Placeholder positions
        type: 'WorkflowNode',
    }));

    var filtered_edges = workflow.edges.filter(e =>
        filtered_nodes.find(n => n.id === e.source) !== undefined &&
        filtered_nodes.find(n => n.id === e.target) !== undefined
    );
    const edges: xyflow.Edge[] = filtered_edges.map(e => ({
        id: `e${e.source}.${e.sourcePort ?? ''}-${e.target}.${e.targetPort ?? ''}`,
        source: e.source.toString(),
        target: e.target.toString(),
        sourceHandle: e.sourcePort ? `${e.sourcePort}` : undefined,
        targetHandle: e.targetPort ? `${e.targetPort}` : undefined,
        markerEnd: {
            type: 'arrowclosed',
            width: 20,
            height: 20,
        },
    }));

    console.log("Converted nodes and edges:", { nodes, edges });

    return { nodes, edges };
}
