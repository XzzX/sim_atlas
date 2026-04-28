import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MutableRefObject } from "react";
import type { Edge } from "@xyflow/react";
import {
  BrainCircuit,
  ChevronDown,
  GitCommitHorizontal,
  HelpCircle,
  Info,
  MessageSquare,
  Plus,
  Search,
  ArrowRight,
  RotateCcw,
  ShieldAlert,
  Trash2,
  SendHorizontal,
  Loader2,
  Bot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { simAtlasAPI } from "../services/api";
import type {
  AgentSSEEvent,
  GraphEdgeContext,
  GraphNodeContext,
  NodeResponse,
} from "../interfaces/BackendSchema";
import type { WorkflowNode } from "../nodes/nodes";
import type { NodeData } from "../nodes/FunctionNode";
import type { InputDataElement } from "../nodes/InputNode";
import type { OutputDataElement } from "../nodes/OutputNode";
import type { Dispatch, SetStateAction } from "react";

// ---- types ----------------------------------------------------------------

type StepItem =
  | { kind: "reasoning"; content: string }
  | {
      kind: "tool";
      name: string;
      args: Record<string, unknown>;
      summary?: string;
    }
  | { kind: "validation"; errors: string[] }
  | { kind: "clarification"; question: string; options: string[] };

interface ConversationTurn {
  role: "user" | "assistant";
  text?: string;
  steps: StepItem[];
  error?: string;
}

// ---- helpers ---------------------------------------------------------------

const TOOL_LABELS: Record<string, string> = {
  search_nodes: "Searching nodes",
  find_compatible_nodes: "Finding compatible nodes",
  get_node_details: "Getting node details",
  add_function_node: "Adding function node",
  add_input_node: "Adding input",
  add_output_node: "Adding output",
  add_edge: "Connecting nodes",
  remove_node: "Removing node",
};

function ToolIcon({ name }: { name: string }) {
  const cls = "w-3.5 h-3.5 shrink-0";
  if (name === "search_nodes" || name === "find_compatible_nodes")
    return <Search className={cls} />;
  if (name === "get_node_details") return <Info className={cls} />;
  if (name === "add_function_node") return <Plus className={cls} />;
  if (name === "add_input_node" || name === "add_output_node")
    return <ArrowRight className={cls} />;
  if (name === "add_edge") return <GitCommitHorizontal className={cls} />;
  if (name === "remove_node") return <Trash2 className={cls} />;
  return null;
}

function str(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v) ?? "";
}

function ToolStepDetail({
  step,
}: {
  step: Extract<StepItem, { kind: "tool" }>;
}) {
  const entries: [string, string][] = [];
  const s = step.args;
  if (step.name === "search_nodes" && s.query != null)
    entries.push(["Query", str(s.query)]);
  if (step.name === "search_nodes") {
    if (s.datatypes != null) entries.push(["Types", str(s.datatypes)]);
    if (s.units != null) entries.push(["Units", str(s.units)]);
    if (s.quantities != null) entries.push(["Quantities", str(s.quantities)]);
    if (s.keywords != null) entries.push(["Keywords", str(s.keywords)]);
    if (s.port_type != null) entries.push(["Port", str(s.port_type)]);
  }
  if (step.name === "find_compatible_nodes") {
    if (s.query != null) entries.push(["Query", str(s.query)]);
    if (s.datatype != null) entries.push(["Type", str(s.datatype)]);
    if (s.unit != null) entries.push(["Unit", str(s.unit)]);
    if (s.quantity != null) entries.push(["Quantity", str(s.quantity)]);
    if (s.port_type != null) entries.push(["Port", str(s.port_type)]);
  }
  if (step.name === "get_node_details" && s.atlas_node_id != null)
    entries.push(["ID", `${str(s.atlas_node_id).slice(0, 16)}…`]);
  if (step.name === "add_function_node") {
    if (s.label != null) entries.push(["Label", str(s.label)]);
    if (s.atlas_node_id != null)
      entries.push(["ID", `${str(s.atlas_node_id).slice(0, 16)}…`]);
  }
  if (
    (step.name === "add_input_node" || step.name === "add_output_node") &&
    s.label != null
  )
    entries.push(["Label", str(s.label)]);
  if (step.name === "add_edge") {
    entries.push([
      "From",
      `${str(s.source_graph_id ?? "?")}/${str(s.source_handle ?? "?")}`,
    ]);
    entries.push([
      "To",
      `${str(s.target_graph_id ?? "?")}/${str(s.target_handle ?? "?")}`,
    ]);
  }
  if (step.name === "remove_node" && s.graph_id != null)
    entries.push(["Node", str(s.graph_id)]);
  if (step.summary !== undefined) entries.push(["Result", step.summary]);

  return (
    <div className="px-3 py-2 space-y-0.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-2 text-xs">
          <span className="text-muted-foreground/60 shrink-0 min-w-[44px]">
            {k}
          </span>
          <span className="text-foreground/80 break-all whitespace-pre-wrap">
            {v}
          </span>
        </div>
      ))}
    </div>
  );
}

function buildAgentNodes(nodes: WorkflowNode[]): GraphNodeContext[] {
  return nodes.map((n) => {
    if (n.type === "FunctionNode") {
      const d = n.data as NodeData;
      return {
        graph_id: n.id,
        node_kind: "function" as const,
        atlas_node_id: d.metadata.id,
        name: d.label,
        inputs: d.metadata.inputs,
        outputs: d.metadata.outputs,
      };
    }
    if (n.type === "InputNode") {
      const d = n.data as InputDataElement;
      return {
        graph_id: n.id,
        node_kind: "input" as const,
        atlas_node_id: null,
        name: d.label,
        inputs: [],
        outputs: [{ label: "output" }],
      };
    }
    // OutputNode
    const d = n.data as OutputDataElement;
    return {
      graph_id: n.id,
      node_kind: "output" as const,
      atlas_node_id: null,
      name: d.label,
      inputs: [{ label: "input" }],
      outputs: [],
    };
  });
}

function buildAgentEdges(edges: Edge[]): GraphEdgeContext[] {
  return edges.map((e) => ({
    source_graph_id: e.source,
    source_handle: e.sourceHandle ?? "",
    target_graph_id: e.target,
    target_handle: e.targetHandle ?? "",
  }));
}

async function convertAgentGraph(
  agentNodes: GraphNodeContext[],
  agentEdges: GraphEdgeContext[],
): Promise<{ nodes: WorkflowNode[]; edges: Edge[] }> {
  const nodes: WorkflowNode[] = await Promise.all(
    agentNodes.map(async (n) => {
      const pos = { x: 0, y: 0 };
      if (n.atlas_node_id != null) {
        let metadata: NodeResponse | undefined;
        try {
          metadata = await simAtlasAPI.getNode(n.atlas_node_id);
        } catch {
          // fall back to minimal shape so the graph still renders
          metadata = {
            id: n.atlas_node_id,
            name: n.name,
            author_name: "",
            author_email: "",
            creator_name: "",
            creator_email: "",
            creation_timestamp: "",
            node_type: "function",
            category: "",
            keywords: [],
            homepage_url: "",
            documentation_url: "",
            source_url: "",
            python_import: "",
            source_code: "",
            docstring: "",
            ai_docstring: n.short_description ?? "",
            inputs: n.inputs,
            outputs: n.outputs,
          };
        }
        const fn: WorkflowNode = {
          id: n.graph_id,
          type: "FunctionNode",
          position: pos,
          data: { label: n.name, metadata },
        };
        return fn;
      }
      // Input or Output — use node_kind as discriminator
      if (n.node_kind === "input") {
        const inp: WorkflowNode = {
          id: n.graph_id,
          type: "InputNode",
          position: pos,
          data: { label: n.name, value: "" },
        };
        return inp;
      }
      const out: WorkflowNode = {
        id: n.graph_id,
        type: "OutputNode",
        position: pos,
        data: { label: n.name },
      };
      return out;
    }),
  );

  const edges: Edge[] = agentEdges.map((e, i) => ({
    id: `agent-edge-${i}`,
    source: e.source_graph_id,
    sourceHandle: e.source_handle || null,
    target: e.target_graph_id,
    targetHandle: e.target_handle || null,
  }));

  return { nodes, edges };
}

// ---- component ------------------------------------------------------------

interface AgentPanelProps {
  nodes: WorkflowNode[];
  edges: Edge[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  layoutRef: MutableRefObject<() => void>;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({
  nodes,
  edges,
  setNodes,
  setEdges,
  layoutRef,
}) => {
  const [messages, setMessages] = useState<ConversationTurn[]>([]);
  const [history, setHistory] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [isRunning, setIsRunning] = useState(false);
  const [inputText, setInputText] = useState("");
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const finalMessageRef = useRef<string>("");
  const graphGenRef = useRef(0);

  const handleNewConversation = () => {
    setMessages([]);
    setHistory([]);
    setExpandedSteps(new Set());
  };

  const toggleStep = (key: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendQuery = useCallback(
    async (query: string) => {
      if (!query || isRunning) return;

      setInputText("");
      setIsRunning(true);
      finalMessageRef.current = "";
      graphGenRef.current = 0;

      // push user turn
      setMessages((prev) => [
        ...prev,
        { role: "user", text: query, steps: [] },
      ]);

      // create placeholder assistant turn
      const assistantIndex = messages.length + 1;
      setMessages((prev) => [...prev, { role: "assistant", steps: [] }]);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const request = {
        query,
        nodes: buildAgentNodes(nodes),
        edges: buildAgentEdges(edges),
        history,
      };

      const updateAssistant = (
        updater: (t: ConversationTurn) => ConversationTurn,
      ) => {
        setMessages((prev) =>
          prev.map((m, i) => (i === assistantIndex ? updater(m) : m)),
        );
      };

      try {
        await simAtlasAPI.agentStream(
          request,
          (event: AgentSSEEvent) => {
            console.log("Received event:", event);
            if (event.type === "reasoning") {
              updateAssistant((t) => ({
                ...t,
                steps: [
                  ...t.steps,
                  { kind: "reasoning", content: event.content },
                ],
              }));
            } else if (event.type === "tool_call") {
              updateAssistant((t) => ({
                ...t,
                steps: [
                  ...t.steps,
                  { kind: "tool", name: event.name, args: event.args },
                ],
              }));
            } else if (event.type === "tool_result") {
              updateAssistant((t) => {
                const steps = [...t.steps];
                // find last tool step with this name and no summary yet
                for (let i = steps.length - 1; i >= 0; i--) {
                  const s = steps[i];
                  if (
                    s.kind === "tool" &&
                    s.name === event.name &&
                    s.summary === undefined
                  ) {
                    steps[i] = { ...s, summary: event.summary };
                    break;
                  }
                }
                return { ...t, steps };
              });
            } else if (event.type === "clarification") {
              updateAssistant((t) => ({
                ...t,
                steps: [
                  ...t.steps,
                  {
                    kind: "clarification",
                    question: event.question,
                    options: event.options,
                  },
                ],
              }));
            } else if (event.type === "message") {
              finalMessageRef.current = event.content;
              updateAssistant((t) => ({ ...t, text: event.content }));
            } else if (event.type === "graph_update") {
              const myGen = ++graphGenRef.current;
              void convertAgentGraph(event.nodes, event.edges).then(
                ({ nodes: newNodes, edges: newEdges }) => {
                  if (graphGenRef.current !== myGen) return;
                  setNodes(newNodes);
                  setEdges(newEdges);
                  setTimeout(() => {
                    layoutRef.current();
                  }, 80);
                },
              );
            } else if (event.type === "validation") {
              updateAssistant((t) => ({
                ...t,
                steps: [
                  ...t.steps,
                  { kind: "validation", errors: event.errors },
                ],
              }));
            } else if (event.type === "error") {
              updateAssistant((t) => ({ ...t, error: event.message }));
            }
          },
          ctrl.signal,
        );
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          updateAssistant((t) => ({
            ...t,
            error: err.message,
          }));
        }
      } finally {
        setIsRunning(false);
        abortRef.current = null;
        setHistory((prev) => [
          ...prev,
          { role: "user", content: query },
          { role: "assistant", content: finalMessageRef.current },
        ]);
      }
    },
    [
      isRunning,
      messages.length,
      nodes,
      edges,
      history,
      setNodes,
      setEdges,
      layoutRef,
    ],
  );

  const handleSend = useCallback(() => {
    void sendQuery(inputText.trim());
  }, [inputText, sendQuery]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0">
        <Bot className="w-4 h-4 text-muted-foreground" />
        <span className="font-semibold text-sm">Agent</span>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto w-7 h-7"
          onClick={handleNewConversation}
          disabled={isRunning}
          aria-label="New conversation"
          title="New conversation"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
      >
        {messages.length === 0 && (
          <p className="text-xs text-muted-foreground text-center mt-8">
            Describe the workflow you want to build.
          </p>
        )}

        {messages.map((turn, i) => (
          <div
            key={i}
            className={turn.role === "user" ? "flex justify-end" : ""}
          >
            {turn.role === "user" ? (
              <div className="bg-primary text-primary-foreground text-sm rounded-2xl rounded-br-sm px-3 py-2 max-w-[85%]">
                {turn.text}
              </div>
            ) : (
              <div className="space-y-2">
                {/* Tool steps */}
                {turn.steps.map((step, j) => {
                  if (step.kind === "clarification") {
                    return (
                      <div
                        key={j}
                        className="rounded-md border border-primary/40 bg-primary/5 p-3 space-y-2"
                      >
                        <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                          <HelpCircle className="w-3.5 h-3.5 shrink-0" />
                          {step.question}
                        </div>
                        {step.options.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {step.options.map((opt) => (
                              <Button
                                key={opt}
                                variant="outline"
                                size="sm"
                                className="h-6 text-xs px-2"
                                disabled={isRunning}
                                onClick={() => void sendQuery(opt)}
                              >
                                {opt}
                              </Button>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  }
                  if (step.kind === "validation") {
                    const vKey = `v-${i}-${j}`;
                    const vExpanded = expandedSteps.has(vKey);
                    return (
                      <div
                        key={j}
                        className="rounded-md border border-orange-500/40 bg-orange-500/10"
                      >
                        <button
                          type="button"
                          onClick={() => toggleStep(vKey)}
                          className="flex w-full items-center gap-1.5 px-3 py-1.5 text-xs text-orange-600 dark:text-orange-400 hover:text-foreground transition-colors"
                        >
                          <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                          <span className="font-medium">
                            Fixing graph errors
                          </span>
                          <ChevronDown
                            className={`w-3 h-3 ml-auto transition-transform ${
                              vExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {vExpanded && (
                          <ul className="px-3 pb-3 border-t border-orange-500/30 pt-2 space-y-1">
                            {step.errors.map((err, k) => (
                              <li
                                key={k}
                                className="text-xs text-orange-700 dark:text-orange-300 break-all"
                              >
                                {err}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    );
                  }
                  if (step.kind === "reasoning") {
                    const rKey = `r-${i}-${j}`;
                    const rExpanded = expandedSteps.has(rKey);
                    return (
                      <div
                        key={j}
                        className="rounded-md border border-border bg-muted/30"
                      >
                        <button
                          type="button"
                          onClick={() => toggleStep(rKey)}
                          className="flex w-full items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                        >
                          <BrainCircuit className="w-3.5 h-3.5 shrink-0" />
                          <span className="font-medium">Thinking</span>
                          <ChevronDown
                            className={`w-3 h-3 ml-auto transition-transform ${
                              rExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {rExpanded && (
                          <div className="px-3 pb-3 border-t border-border pt-2 prose prose-sm dark:prose-invert max-w-none text-muted-foreground/80 [&_*]:text-xs">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {step.content}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    );
                  }
                  const key = `${i}-${j}`;
                  const expanded = expandedSteps.has(key);
                  return (
                    <div
                      key={j}
                      className="rounded-md border border-border bg-muted/30"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          toggleStep(key);
                        }}
                        className="flex w-full items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ToolIcon name={step.name} />
                        <span className="font-medium">
                          {TOOL_LABELS[step.name] ?? step.name}
                        </span>
                        {step.summary !== undefined ? (
                          <ChevronDown
                            className={`w-3 h-3 ml-auto transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        ) : (
                          <Loader2 className="w-3 h-3 animate-spin ml-auto" />
                        )}
                      </button>
                      {expanded && (
                        <div className="border-t border-border">
                          <ToolStepDetail step={step} />
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Error */}
                {turn.error && (
                  <div className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">
                    {turn.error}
                  </div>
                )}

                {/* Final message */}
                {turn.text
                  ? (() => {
                      const sKey = `summary-${i}`;
                      const sExpanded = expandedSteps.has(sKey);
                      return (
                        <div className="rounded-md border border-border bg-muted/30">
                          <button
                            type="button"
                            onClick={() => toggleStep(sKey)}
                            className="flex w-full items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                            <span className="font-medium">Summary</span>
                            <ChevronDown
                              className={`w-3 h-3 ml-auto transition-transform ${
                                sExpanded ? "rotate-180" : ""
                              }`}
                            />
                          </button>
                          {sExpanded && (
                            <div className="px-3 pb-3 border-t border-border pt-2 prose prose-sm dark:prose-invert max-w-none [&_*]:text-xs">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {turn.text}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      );
                    })()
                  : isRunning &&
                    i === messages.length - 1 &&
                    !turn.error && (
                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                    )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-border p-3 flex gap-2 shrink-0">
        <textarea
          className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
          rows={2}
          placeholder="Describe a workflow…"
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
          }}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={isRunning || !inputText.trim()}
          aria-label="Send"
        >
          {isRunning ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <SendHorizontal className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  );
};
