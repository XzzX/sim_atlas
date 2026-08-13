import * as React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MutableRefObject } from "react";
import type { Edge } from "@xyflow/react";
import {
  Ban,
  BrainCircuit,
  ChevronDown,
  CircleStop,
  GitCommitHorizontal,
  HelpCircle,
  History,
  Info,
  MessageSquare,
  PauseCircle,
  Plus,
  Search,
  ArrowRight,
  RotateCcw,
  ShieldAlert,
  Square,
  Trash2,
  SendHorizontal,
  Settings,
  Loader2,
  Bot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { simAtlasAPI } from "../services/api";
import { AgentSettingsDialog } from "../dialogs/AgentSettingsDialog";
import {
  clearAgentSettings,
  loadAgentSettings,
  saveAgentSettings,
  type AgentSettings,
} from "../lib/agentSettings";
import type {
  AgentSSEEvent,
  CapabilitiesResponse,
  GraphEdgeContext,
  GraphNodeContext,
  FunctionResponse,
  WorkflowResponse,
} from "../interfaces/BackendSchema";
import type { WorkflowNode } from "../nodes/nodes";
import type { NodeData } from "../nodes/FunctionNode";
import type { InputDataElement } from "../nodes/InputNode";
import type { Dispatch, SetStateAction } from "react";

// ---- types ----------------------------------------------------------------

type StepItem =
  | { kind: "reasoning"; content: string }
  | {
      kind: "tool";
      name: string;
      args: Record<string, unknown>;
      content?: string;
    }
  | { kind: "validation"; errors: string[] }
  | { kind: "clarification"; question: string; options: string[] }
  | {
      kind: "graph_snapshot";
      nodes: GraphNodeContext[];
      edges: GraphEdgeContext[];
    };

interface ConversationTurn {
  role: "user" | "assistant";
  text?: string;
  steps: StepItem[];
  error?: string;
  truncated?: boolean;
  cancelled?: boolean;
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

// Markdown bodies must wrap into the panel rather than widen it. Long prose
// breaks mid-word; code fences and GFM tables get their own horizontal scroll
// so they never force the conversation itself to scroll sideways.
const PROSE_CLASS =
  "prose prose-sm dark:prose-invert max-w-none min-w-0 break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_table]:block [&_table]:max-w-full [&_table]:overflow-x-auto";

// Passed to AbortController.abort() so the catch block can tell a deliberate
// stop from an unmount teardown (which aborts with no reason).
const STOP_REASON = "sim-atlas:user-stop";
const RESUME_QUERY = "Please continue where you left off.";
const CANCELLED_BODY =
  "You stopped this run. The graph shows the work completed so far.";
// Replaces the empty assistant message a cancelled run would otherwise replay.
const CANCELLED_HISTORY_NOTE =
  "(The user stopped this run before it finished. The work completed so far is reflected in the current graph.)";

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

function prettyToolContent(content: string): string {
  try {
    const parsed = JSON.parse(content) as unknown;
    return JSON.stringify(parsed, null, 2);
  } catch {
    return content;
  }
}

function ToolStepDetail({
  step,
}: {
  step: Extract<StepItem, { kind: "tool" }>;
}) {
  const [showFullResult, setShowFullResult] = useState(false);
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
  const prettyResult =
    step.content !== undefined ? prettyToolContent(step.content) : undefined;
  const compactResult =
    prettyResult !== undefined && prettyResult.length > 500
      ? `${prettyResult.slice(0, 500)}...`
      : prettyResult;
  const displayResult = showFullResult ? prettyResult : compactResult;
  if (displayResult !== undefined) entries.push(["Result", displayResult]);

  return (
    <div className="px-3 py-2 space-y-0.5 min-w-0">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-2 text-xs min-w-0">
          <span className="text-muted-foreground/60 shrink-0 min-w-[44px]">
            {k}
          </span>
          <span className="text-foreground/80 flex-1 min-w-0 break-all whitespace-pre-wrap">
            {v}
          </span>
        </div>
      ))}
      {prettyResult !== undefined && prettyResult.length > 500 && (
        <div className="pt-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={() => {
              setShowFullResult((prev) => !prev);
            }}
          >
            {showFullResult ? "Show compact JSON" : "Show full JSON"}
          </Button>
        </div>
      )}
    </div>
  );
}

// The three ways an assistant turn can end. "paused" and "cancelled" share the
// amber styling — both are incomplete but resumable; icon and title separate them.
const OUTCOME_STYLES = {
  summary: {
    icon: MessageSquare,
    title: "Summary",
    box: "border-border bg-muted/30",
    head: "text-muted-foreground",
    body: "border-border",
  },
  paused: {
    icon: PauseCircle,
    title: "Paused — turn limit reached",
    box: "border-amber-500/50 bg-amber-500/10",
    head: "text-amber-600 dark:text-amber-400",
    body: "border-amber-500/30 text-amber-700 dark:text-amber-300",
  },
  cancelled: {
    icon: CircleStop,
    title: "Stopped — you cancelled this run",
    box: "border-amber-500/50 bg-amber-500/10",
    head: "text-amber-600 dark:text-amber-400",
    body: "border-amber-500/30 text-amber-700 dark:text-amber-300",
  },
} as const;

function TurnOutcomeCard({
  outcome,
  text,
  expanded,
  onToggle,
  onResume,
  resumeDisabled,
}: {
  outcome: keyof typeof OUTCOME_STYLES;
  text?: string;
  expanded: boolean;
  onToggle: () => void;
  onResume?: () => void;
  resumeDisabled?: boolean;
}) {
  const style = OUTCOME_STYLES[outcome];
  const Icon = style.icon;
  return (
    <div className={`rounded-md border ${style.box}`}>
      <button
        type="button"
        onClick={onToggle}
        className={`flex w-full items-center gap-1.5 px-3 py-1.5 text-xs hover:text-foreground transition-colors ${style.head}`}
      >
        <Icon className="w-3.5 h-3.5 shrink-0" />
        <span className="font-medium min-w-0 truncate">{style.title}</span>
        <ChevronDown
          className={`w-3 h-3 ml-auto shrink-0 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>
      {expanded && (
        <div
          className={`px-3 pb-3 border-t pt-2 [&_*]:text-xs ${style.body} ${PROSE_CLASS}`}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {text ?? CANCELLED_BODY}
          </ReactMarkdown>
        </div>
      )}
      {onResume && (
        <div className="px-3 pb-3">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs border-amber-500/50 hover:bg-amber-500/10"
            disabled={resumeDisabled}
            onClick={onResume}
          >
            Resume
          </Button>
        </div>
      )}
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
    const d = n.data;
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
        let metadata: FunctionResponse | WorkflowResponse | undefined;
        try {
          metadata = await simAtlasAPI.getArtifact(n.atlas_node_id);
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
            artifact_type: "function",
            category: "",
            keywords: [],
            homepage_url: "",
            documentation_url: "",
            source_url: "",
            python_import: "",
            source_code: "",
            docstring: "",
            brief_description: n.short_description ?? "",
            description: n.short_description ?? "",
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
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [isRunning, setIsRunning] = useState(false);
  const [inputText, setInputText] = useState("");
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(
    null,
  );
  const [settings, setSettings] = useState<AgentSettings | null>(
    loadAgentSettings,
  );
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const finalMessageRef = useRef<string>("");
  const graphGenRef = useRef(0);

  const handleNewConversation = () => {
    setMessages([]);
    setHistory([]);
    setExpandedSteps(new Set());
    setSessionId(crypto.randomUUID());
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

  const handleRestoreSnapshot = useCallback(
    (snapshotNodes: GraphNodeContext[], snapshotEdges: GraphEdgeContext[]) => {
      // Same generation guard as graph_update: a restore must not be undone by
      // a conversion that was already in flight when it was requested.
      const myGen = ++graphGenRef.current;
      void convertAgentGraph(snapshotNodes, snapshotEdges).then(
        ({ nodes: newNodes, edges: newEdges }) => {
          if (graphGenRef.current !== myGen) return;
          setNodes(newNodes);
          setEdges(newEdges);
          setTimeout(() => {
            layoutRef.current();
          }, 80);
        },
      );
    },
    [setNodes, setEdges, layoutRef],
  );

  // Stop the backend run when the panel goes away. Aborting with no reason
  // marks this as a teardown rather than a user stop, so no card is rendered.
  useEffect(() => () => abortRef.current?.abort(), []);

  // auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    simAtlasAPI
      .getCapabilities()
      .then(setCapabilities)
      .catch(() => {
        setCapabilities({
          embeddings_enabled: false,
          llm_providers: [],
          llm_default_provider: null,
          llm_reasoning_efforts: [],
        });
      });
  }, []);

  const sendQuery = useCallback(
    async (query: string) => {
      if (!query || isRunning) return;

      setInputText("");
      setIsRunning(true);
      finalMessageRef.current = "";

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
        session_id: sessionId,
        user_id: "default",
        // Omitted entirely when unset, so the server falls back to its own config.
        ...(settings ?? {}),
      };

      const updateAssistant = (
        updater: (t: ConversationTurn) => ConversationTurn,
      ) => {
        setMessages((prev) =>
          prev.map((m, i) => (i === assistantIndex ? updater(m) : m)),
        );
      };

      let stopped = false;
      try {
        await simAtlasAPI.agentStream(
          request,
          (event: AgentSSEEvent) => {
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
                // find last tool step with this name and no content yet
                for (let i = steps.length - 1; i >= 0; i--) {
                  const s = steps[i];
                  if (
                    s.kind === "tool" &&
                    s.name === event.name &&
                    s.content === undefined
                  ) {
                    steps[i] = { ...s, content: event.content };
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
              updateAssistant((t) => ({
                ...t,
                steps: [
                  ...t.steps,
                  {
                    kind: "graph_snapshot" as const,
                    nodes: event.nodes,
                    edges: event.edges,
                  },
                ],
              }));
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
            } else if (event.type === "truncated") {
              updateAssistant((t) => ({ ...t, truncated: true }));
            }
          },
          ctrl.signal,
        );
      } catch (err: unknown) {
        // Aborting with a custom reason rejects with that raw value rather than
        // a DOMException, so the signal — not the error — is what we inspect.
        if (ctrl.signal.aborted) {
          stopped = ctrl.signal.reason === STOP_REASON;
          if (stopped) updateAssistant((t) => ({ ...t, cancelled: true }));
        } else if (err instanceof Error) {
          updateAssistant((t) => ({
            ...t,
            error: err.message,
          }));
        }
      } finally {
        setIsRunning(false);
        abortRef.current = null;
        // Never record an empty assistant message: some OpenAI-compatible
        // gateways reject it when the history is replayed on the next request.
        const assistantContent =
          finalMessageRef.current ||
          (stopped ? CANCELLED_HISTORY_NOTE : "(no response)");
        setHistory((prev) => [
          ...prev,
          { role: "user", content: query },
          { role: "assistant", content: assistantContent },
        ]);
      }
    },
    [
      isRunning,
      messages.length,
      nodes,
      edges,
      history,
      sessionId,
      settings,
      setNodes,
      setEdges,
      layoutRef,
    ],
  );

  const handleSend = useCallback(() => {
    void sendQuery(inputText.trim());
  }, [inputText, sendQuery]);

  const handleStop = useCallback(() => {
    // Discard any conversion still in flight so it cannot repaint the canvas
    // after the user has stopped.
    graphGenRef.current += 1;
    abortRef.current?.abort(STOP_REASON);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // The agent only ever runs on the user's own key, so stored settings are the
  // one prerequisite.
  const canRun = settings !== null;
  // ...and a key is only usable if the operator allowlisted somewhere to send it.
  const canConfigure = (capabilities?.llm_providers.length ?? 0) > 0;

  return (
    // w-full is load-bearing: the panel is mounted as a flex item, which would
    // otherwise size itself to its content instead of the available width.
    <div className="flex flex-col h-full w-full min-w-0 bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0 min-w-0">
        <Bot className="w-4 h-4 text-muted-foreground shrink-0" />
        <span className="font-semibold text-sm truncate">Agent</span>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto w-7 h-7 shrink-0"
          onClick={handleNewConversation}
          disabled={isRunning}
          aria-label="New conversation"
          title="New conversation"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="w-7 h-7 shrink-0"
          onClick={() => {
            setIsSettingsOpen(true);
          }}
          aria-label="Agent settings"
          title="Agent settings"
        >
          <Settings className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 min-h-0 min-w-0"
      >
        {messages.length === 0 && (
          <p className="text-xs text-muted-foreground text-center mt-8">
            Describe the workflow you want to build.
          </p>
        )}

        {messages.map((turn, i) => (
          <div
            key={i}
            className={
              turn.role === "user" ? "flex justify-end min-w-0" : "min-w-0"
            }
          >
            {turn.role === "user" ? (
              <div className="bg-primary text-primary-foreground text-sm rounded-2xl rounded-br-sm px-3 py-2 max-w-[85%] min-w-0 whitespace-pre-wrap break-words">
                {turn.text}
              </div>
            ) : (
              <div className="space-y-2 min-w-0">
                {/* Tool steps */}
                {turn.steps.map((step, j) => {
                  if (step.kind === "clarification") {
                    return (
                      <div
                        key={j}
                        className="rounded-md border border-primary/40 bg-primary/5 p-3 space-y-2"
                      >
                        <div className="flex items-start gap-1.5 text-xs font-medium text-primary">
                          <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                          <span className="min-w-0 break-words">
                            {step.question}
                          </span>
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
                          <span className="font-medium min-w-0 truncate">
                            Fixing graph errors
                          </span>
                          <ChevronDown
                            className={`w-3 h-3 ml-auto shrink-0 transition-transform ${
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
                  if (step.kind === "graph_snapshot") {
                    return (
                      <div
                        key={j}
                        className="flex items-center gap-1.5 px-1 py-0.5"
                      >
                        <History className="w-3 h-3 text-muted-foreground/40 shrink-0" />
                        <span className="text-xs text-muted-foreground/50 flex-1 min-w-0 truncate">
                          {step.nodes.length} node
                          {step.nodes.length !== 1 ? "s" : ""},{" "}
                          {step.edges.length} edge
                          {step.edges.length !== 1 ? "s" : ""}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 shrink-0 text-xs px-2 py-0 text-muted-foreground hover:text-foreground"
                          disabled={isRunning}
                          onClick={() =>
                            handleRestoreSnapshot(step.nodes, step.edges)
                          }
                        >
                          Restore
                        </Button>
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
                          <span className="font-medium min-w-0 truncate">
                            Thinking
                          </span>
                          <ChevronDown
                            className={`w-3 h-3 ml-auto shrink-0 transition-transform ${
                              rExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </button>
                        {rExpanded && (
                          <div
                            className={`px-3 pb-3 border-t border-border pt-2 text-muted-foreground/80 [&_*]:text-xs ${PROSE_CLASS}`}
                          >
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
                        <span className="font-medium min-w-0 truncate">
                          {TOOL_LABELS[step.name] ?? step.name}
                        </span>
                        {step.content !== undefined ? (
                          <ChevronDown
                            className={`w-3 h-3 ml-auto shrink-0 transition-transform ${
                              expanded ? "rotate-180" : ""
                            }`}
                          />
                        ) : turn.cancelled === true ||
                          turn.error !== undefined ? (
                          // The run ended before this tool reported back — the
                          // spinner would otherwise never stop.
                          <Ban className="w-3 h-3 ml-auto shrink-0 opacity-50" />
                        ) : (
                          <Loader2 className="w-3 h-3 animate-spin ml-auto shrink-0" />
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
                  <div className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1 min-w-0 break-words">
                    {turn.error}
                  </div>
                )}

                {/* How the turn ended — Stopped, Paused (turn limit) or Summary.
                    Cancelled wins over the others: if the user stopped between
                    the final message and the stream closing, "stopped" is the
                    honest label and the text stays available under the chevron. */}
                {(() => {
                  const oKey = `outcome-${i}`;
                  const expanded = expandedSteps.has(oKey);
                  const onToggle = () => {
                    toggleStep(oKey);
                  };
                  if (turn.cancelled === true) {
                    return (
                      <TurnOutcomeCard
                        outcome="cancelled"
                        text={turn.text}
                        expanded={expanded}
                        onToggle={onToggle}
                        resumeDisabled={isRunning}
                        onResume={() => void sendQuery(RESUME_QUERY)}
                      />
                    );
                  }
                  if (turn.text !== undefined) {
                    return turn.truncated === true ? (
                      <TurnOutcomeCard
                        outcome="paused"
                        text={turn.text}
                        expanded={expanded}
                        onToggle={onToggle}
                        resumeDisabled={isRunning}
                        onResume={() => void sendQuery(RESUME_QUERY)}
                      />
                    ) : (
                      <TurnOutcomeCard
                        outcome="summary"
                        text={turn.text}
                        expanded={expanded}
                        onToggle={onToggle}
                      />
                    );
                  }
                  if (isRunning && i === messages.length - 1 && !turn.error) {
                    return (
                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                    );
                  }
                  return null;
                })()}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input — replaced by a call to action while no credentials are available */}
      {canRun ? (
        <div className="border-t border-border p-3 flex gap-2 shrink-0 min-w-0">
          <textarea
            className="flex-1 min-w-0 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
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
            className="shrink-0"
            variant={isRunning ? "secondary" : "default"}
            onClick={isRunning ? handleStop : handleSend}
            disabled={isRunning ? false : !inputText.trim()}
            aria-label={isRunning ? "Stop agent" : "Send"}
            title={isRunning ? "Stop agent" : "Send"}
          >
            {isRunning ? (
              <Square className="w-3.5 h-3.5 fill-current" />
            ) : (
              <SendHorizontal className="w-4 h-4" />
            )}
          </Button>
        </div>
      ) : (
        <div className="border-t border-border p-3 space-y-2 shrink-0">
          <p className="text-xs text-muted-foreground">
            {capabilities === null
              ? "Checking agent availability…"
              : canConfigure
                ? "Pick a provider and model and add your LLM API key to use the agent."
                : "This server has no LLM provider configured, so the agent cannot run."}
          </p>
          {canConfigure && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => {
                setIsSettingsOpen(true);
              }}
            >
              Configure
            </Button>
          )}
        </div>
      )}

      {isSettingsOpen && (
        <AgentSettingsDialog
          onClose={() => {
            setIsSettingsOpen(false);
          }}
          providers={capabilities?.llm_providers ?? []}
          defaultProvider={capabilities?.llm_default_provider ?? null}
          reasoningEfforts={capabilities?.llm_reasoning_efforts ?? []}
          settings={settings}
          onSave={(next) => {
            saveAgentSettings(next);
            setSettings(next);
          }}
          onClear={() => {
            clearAgentSettings();
            setSettings(null);
          }}
        />
      )}
    </div>
  );
};
