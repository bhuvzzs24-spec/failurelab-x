"use client";
import { useExperiments, useGraph, useRuns } from "@/hooks/data";
import type { Graph, Service } from "@/types/domain";
import dagre from "@dagrejs/dagre";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowUpRight,
  Box,
  CreditCard,
  GitBranch,
  Layers,
  Search,
  Server,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useProject } from "./providers";
import { asObject, asText } from "@/lib/utils";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { EmptyState, ErrorState, Loading } from "./ui/states";

type ServiceData = { service: Service; focused: boolean; compact?: boolean };
type ServiceNode = Node<ServiceData, "service">;
const icons = { gateway: Layers, order: Server, payment: CreditCard, inventory: Box };
function ServiceCard({ data, selected }: NodeProps<ServiceNode>) {
  const Icon = icons[data.service.name];
  return (
    <div
      className={`service-node ${data.compact ? "node-compact" : ""} ${selected ? "node-selected" : ""} ${data.focused ? "node-target" : ""}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="node-top">
        <span className={`node-icon node-${data.service.name}`}>
          <Icon size={18} />
        </span>
        <span className="node-kind">HTTP SERVICE</span>
        <span
          className="node-registration"
          title="Explicitly registered; live health is not observed"
        />
      </div>
      <strong>{data.service.name}</strong>
      <span className="node-version">{data.service.version}</span>
      <div className="node-bottom">
        <span>
          {(data.service.operations ?? []).length} operation
          {(data.service.operations ?? []).length === 1 ? "" : "s"}
        </span>
        <span>{data.focused ? "Configured fault target" : "Registered"}</span>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { service: ServiceCard };
export function graphLayout(
  graph: Graph,
  target = "",
  compact = false,
): { nodes: ServiceNode[]; edges: Edge[] } {
  const layout = new dagre.graphlib.Graph();
  layout.setDefaultEdgeLabel(() => ({}));
  layout.setGraph({
    rankdir: "LR",
    nodesep: compact ? 22 : 38,
    ranksep: 96,
    marginx: 30,
    marginy: 30,
  });
  graph.nodes.forEach((service) =>
    layout.setNode(service.id, { width: 240, height: compact ? 112 : 164 }),
  );
  graph.edges.forEach((edge) => layout.setEdge(edge.source_id, edge.target_id));
  dagre.layout(layout);
  return {
    nodes: graph.nodes.map((service) => {
      const position = layout.node(service.id);
      return {
        id: service.id,
        type: "service",
        ariaLabel: `Inspect ${service.name} service`,
        position: { x: position.x - 120, y: position.y - (compact ? 56 : 82) },
        data: { service, focused: service.name === target, compact },
      };
    }),
    edges: graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source_id,
      target: edge.target_id,
      label: edge.operation || edge.kind,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed, color: "#777ba0" },
      style: {
        stroke:
          graph.nodes.find((node) => node.id === edge.target_id)?.name === target
            ? "#a399ff"
            : "#525975",
        strokeWidth: 1.5,
      },
      labelStyle: { fill: "#b6bdd0", fontSize: 10 },
      labelBgStyle: { fill: "#131926" },
      labelBgPadding: [7, 4],
    })),
  };
}
function Canvas({
  graph,
  target,
  compact,
  onSelect,
}: {
  graph: Graph;
  target: string;
  compact: boolean;
  onSelect: (service: Service) => void;
}) {
  const initial = useMemo(() => graphLayout(graph, target, compact), [graph, target, compact]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
  const [flow, setFlow] = useState<ReactFlowInstance<ServiceNode, Edge> | null>(null);
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: ServiceNode) => onSelect(node.data.service),
    [onSelect],
  );
  return (
    <div
      className={`graph-canvas ${compact ? "graph-compact" : ""}`}
      aria-label="Registered service dependency graph"
      data-testid="service-graph"
      onKeyDownCapture={(event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const element = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node");
        const node = nodes.find((node) => node.id === element?.dataset.id);
        if (node) {
          event.preventDefault();
          onSelect(node.data.service);
        }
      }}
    >
      {!compact && (
        <Button
          variant="secondary"
          size="sm"
          className="graph-layout-action"
          aria-label="Reset graph layout"
          disabled={!flow}
          onClick={() => {
            setNodes(initial.nodes);
            setEdges(initial.edges);
            requestAnimationFrame(() => {
              void flow?.fitView({ padding: 0.2 });
            });
          }}
        >
          <RotateCcw size={13} />
          Auto layout
        </Button>
      )}
      <ReactFlow
        onInit={setFlow}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: compact ? 0.7 : 1 }}
        minZoom={0.25}
        maxZoom={1.8}
        colorMode="dark"
        proOptions={{ hideAttribution: false }}
        nodesConnectable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#343b50" />
        <Controls showInteractive={false} />
        {!compact && (
          <MiniMap pannable zoomable nodeColor="#635b9d" maskColor="rgba(10,14,23,.7)" />
        )}
      </ReactFlow>
    </div>
  );
}
export function SystemGraph({ compact = false }: { compact?: boolean }) {
  const { projectId } = useProject();
  const query = useGraph(projectId);
  const definitions = useExperiments(projectId);
  const runs = useRuns(projectId);
  const [search, setSearch] = useState("");
  const [experimentId, setExperimentId] = useState("");
  const [selected, setSelected] = useState<Service | null>(null);
  const experiment = definitions.data?.find((definition) => definition.id === experimentId);
  const graph = useMemo(() => {
    const data = query.data;
    if (!data) return null;
    const nodes = data.nodes.filter((node) =>
      node.name.toLowerCase().includes(search.toLowerCase()),
    );
    const ids = new Set(nodes.map((node) => node.id));
    return {
      ...data,
      nodes,
      edges: data.edges.filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id)),
    };
  }, [query.data, search]);
  if (query.isPending) return <Loading label="Loading service graph" />;
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
    );
  if (!query.data.nodes.length)
    return (
      <EmptyState
        title="No registered services"
        description="Register the sandbox services to build an explicit dependency graph."
        href="/settings"
        action="Register services"
      />
    );
  return (
    <>
      <div className="graph-toolbar">
        <div className="inline-legend">
          <span className="legend-dot violet" />
          Explicit registration
          <span className="legend-divider" />
          <span>{query.data.nodes.length} services</span>
          <span>{query.data.edges.length} dependencies</span>
        </div>
        {compact ? (
          <Link className="text-link" href="/graph">
            Explore graph <ArrowUpRight size={13} />
          </Link>
        ) : (
          <div className="graph-filters">
            <label className="search-field">
              <Search size={14} />
              <input
                aria-label="Filter services"
                placeholder="Filter services…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <select
              aria-label="Highlight experiment boundary"
              value={experimentId}
              onChange={(event) => setExperimentId(event.target.value)}
            >
              <option value="">All dependencies</option>
              {definitions.data?.map((definition) => (
                <option key={definition.id} value={definition.id}>
                  {definition.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      {graph && graph.nodes.length > 0 ? (
        <Canvas
          key={`${JSON.stringify(graph)}:${experimentId}`}
          graph={graph}
          target={experiment?.config.fault.target ?? ""}
          compact={compact}
          onSelect={setSelected}
        />
      ) : (
        <EmptyState
          title="No matching services"
          description="Change the service filter to restore the graph."
        />
      )}
      <div className="graph-footer">
        <span>
          <ShieldCheck size={12} />
          Registered dependencies · health not inferred
        </span>
        <span>
          {experiment
            ? "Highlighted: configured fault boundary, not a proven causal path"
            : "Drag to arrange · scroll to zoom"}
        </span>
      </div>
      <Dialog
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent className="detail-sheet">
          <DialogTitle>{selected?.name} service</DialogTitle>
          <DialogDescription>
            Explicit registration metadata. No live health assertion is made.
          </DialogDescription>
          {selected && (
            <>
              <dl className="detail-list">
                <div>
                  <dt>Version</dt>
                  <dd>{selected.version}</dd>
                </div>
                <div>
                  <dt>Service ID</dt>
                  <dd className="mono">{selected.id}</dd>
                </div>
                <div>
                  <dt>Resources</dt>
                  <dd>{(selected.resources ?? []).join(", ") || "None registered"}</dd>
                </div>
              </dl>
              <h3>Registered operations</h3>
              {(selected.operations ?? []).map((operation, i) => (
                <div className="operation" key={i}>
                  <code>{operation.method}</code>
                  <code>{operation.path}</code>
                </div>
              ))}
              <h3>Related experiments</h3>
              {definitions.data
                ?.filter(
                  (definition) =>
                    definition.config.fault.target === selected.name || selected.name === "gateway",
                )
                .map((definition) => (
                  <Link
                    className="list-link"
                    key={definition.id}
                    href={`/experiments?experiment=${definition.id}`}
                  >
                    {definition.name}
                    <ArrowUpRight size={14} />
                  </Link>
                ))}
              <h3>Recent boundary evidence</h3>
              <div className="graph-inspection-evidence">
                {runs.data?.items
                  .filter(
                    (run) =>
                      asObject(run.config.fault).target === selected.name ||
                      selected.name === "gateway",
                  )
                  .slice(0, 4)
                  .map((run) => (
                    <Link key={run.id} href={`/evidence?run=${run.id}`}>
                      <span>
                        {asText(asObject(run.config.fault).kind)} · {run.status}
                      </span>
                      <ArrowUpRight size={14} />
                    </Link>
                  ))}
                {runs.error && (
                  <p className="inline-error">Recent executions could not be loaded.</p>
                )}
                {runs.data &&
                  !runs.data.items.some(
                    (run) =>
                      asObject(run.config.fault).target === selected.name ||
                      selected.name === "gateway",
                  ) && (
                    <p className="microcopy">
                      No matching boundary executions in the most recent page.
                    </p>
                  )}
              </div>
              <Button asChild variant="secondary">
                <Link href="/findings">
                  <GitBranch size={14} />
                  Inspect recorded findings
                </Link>
              </Button>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
