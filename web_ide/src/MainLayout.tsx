import * as React from "react";
import { useRef, useState, useCallback, useEffect } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ReactFlowEditor } from "./ReactFlowEditor";
import type { OnNodesChange, OnEdgesChange, Edge } from "@xyflow/react";
import "./index.css";
import type { WorkflowNode } from "./nodes/nodes";
import { AgentPanel } from "./components/AgentPanel";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { simAtlasAPI } from "./services/api";

const MIN_PANEL_WIDTH = 240;
const MAX_PANEL_WIDTH = 720;
const DEFAULT_PANEL_WIDTH = 384;

interface MainLayoutProps {
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange<WorkflowNode>;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
}) => {
  const layoutRef = useRef<() => void>(() => {
    /* filled by ReactFlowEditor */
  });
  const [panelWidth, setPanelWidth] = useState(DEFAULT_PANEL_WIDTH);
  const [collapsed, setCollapsed] = useState(false);
  const [agentEnabled, setAgentEnabled] = useState<boolean | null>(null);
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    simAtlasAPI
      .getCapabilities()
      .then((caps) => setAgentEnabled(caps.agent_enabled))
      .catch(() => setAgentEnabled(false));
  }, []);

  const onHandleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (collapsed) return;
      e.preventDefault();
      dragState.current = { startX: e.clientX, startWidth: panelWidth };

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragState.current) return;
        const delta = dragState.current.startX - ev.clientX;
        const next = Math.min(
          MAX_PANEL_WIDTH,
          Math.max(MIN_PANEL_WIDTH, dragState.current.startWidth + delta),
        );
        setPanelWidth(next);
      };

      const onMouseUp = () => {
        dragState.current = null;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      };

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [collapsed, panelWidth],
  );

  return (
    <div
      className="simflow"
      style={{ height: "100vh", display: "flex", flexDirection: "column" }}
    >
      {/* Main Content + Sidebar Container */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Main Content */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <ReactFlowEditor
            nodes={nodes}
            setNodes={setNodes}
            onNodesChange={onNodesChange}
            edges={edges}
            setEdges={setEdges}
            onEdgesChange={onEdgesChange}
            layoutRef={layoutRef}
          />
        </div>

        {agentEnabled === true && (
          <>
            {/* Resize handle */}
            <div
              onMouseDown={onHandleMouseDown}
              style={{
                width: "8px",
                flexShrink: 0,
                position: "relative",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: collapsed ? "default" : "col-resize",
                zIndex: 10,
              }}
              className="group bg-border/0 hover:bg-border/40 transition-colors"
            >
              {/* Collapse / expand toggle */}
              <button
                type="button"
                aria-label={collapsed ? "Expand panel" : "Collapse panel"}
                onClick={() => {
                  setCollapsed((c) => !c);
                }}
                style={{
                  position: "absolute",
                  top: "50%",
                  transform: "translateY(-50%)",
                  left: "-10px",
                  width: "20px",
                  height: "48px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "4px 0 0 4px",
                  zIndex: 20,
                }}
                className="bg-background border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
              >
                {collapsed ? (
                  <ChevronLeft className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
              </button>
            </div>

            {/* Agent Panel */}
            <div
              style={{
                width: collapsed ? 0 : `${panelWidth}px`,
                flexShrink: 0,
                overflow: "hidden",
                display: "flex",
                transition: collapsed ? "width 0.2s ease" : undefined,
              }}
            >
              <AgentPanel
                nodes={nodes}
                edges={edges}
                setNodes={setNodes}
                setEdges={setEdges}
                layoutRef={layoutRef}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};
