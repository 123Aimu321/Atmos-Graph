
import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";

import {
  Network,
  Search,
  AlertTriangle,
  RefreshCw,
  PlusCircle,
  RotateCcw,
} from "lucide-react";

import "@xyflow/react/dist/style.css";
import "./GraphExplorer.css";

const API_BASE = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const MAX_VISIBLE_NODES = 300;
const MAX_VISIBLE_EDGES = 1000;

const NODE_WIDTH = 205;
const NODE_HEIGHT = 82;
const NODE_GAP_X = 60;
const NODE_GAP_Y = 22;
const MAX_ROWS = 12;

const TYPE_COLORS = {
  SUPPLIER: "#22c55e",
  MANUFACTURER: "#06b6d4",
  PORT: "#a78bfa",
  WAREHOUSE: "#f59e0b",
  RETAILER: "#94a3b8",
};

async function fetchJSON(path, signal) {
  const response = await fetch(
    `${API_BASE}${path}`,
    { signal }
  );

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;

    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Retain HTTP error.
    }

    throw new Error(detail);
  }

  return response.json();
}

function mergeGraph(
  current,
  incoming,
  maxNodes,
  maxEdges
) {
  if (!current) {
    return {
      nodes: (incoming.nodes || [])
        .slice(0, maxNodes),
      edges: (incoming.edges || [])
        .slice(0, maxEdges),
    };
  }

  const nodeMap = new Map(
    current.nodes.map((node) => [
      node.id,
      node,
    ])
  );

  let addedNodes = 0;

  for (const node of incoming.nodes || []) {
    if (!node?.id || nodeMap.has(node.id)) {
      continue;
    }

    if (nodeMap.size >= maxNodes) {
      break;
    }

    nodeMap.set(node.id, node);
    addedNodes++;
  }

  const edgeMap = new Map(
    current.edges.map((edge) => [
      edge.id,
      edge,
    ])
  );

  let addedEdges = 0;

  for (const edge of incoming.edges || []) {
    if (
      !nodeMap.has(edge.source) ||
      !nodeMap.has(edge.target)
    ) {
      continue;
    }

    const edgeId =
      edge.id ||
      `${edge.source}->${edge.target}`;

    if (edgeMap.has(edgeId)) {
      continue;
    }

    if (edgeMap.size >= maxEdges) {
      break;
    }

    edgeMap.set(edgeId, {
      ...edge,
      id: edgeId,
    });

    addedEdges++;
  }

  return {
    nodes: [...nodeMap.values()],
    edges: [...edgeMap.values()],
    addedNodes,
    addedEdges,
  };
}

function makeLayoutNodes(
  graph,
  rootId,
  selectedId
) {
  if (!graph) return [];

  const nodes = graph.nodes || [];
  const edges = graph.edges || [];

  const outgoing = new Map();

  for (const node of nodes) {
    outgoing.set(node.id, []);
  }

  for (const edge of edges) {
    if (
      outgoing.has(edge.source) &&
      outgoing.has(edge.target)
    ) {
      outgoing.get(edge.source).push(
        edge.target
      );
    }
  }

  // Find visual distances from the root.
  // For separately expanded subgraphs, nodes
  // unreachable through directed paths get
  // placed in an additional explorer column.

  const distances = new Map();

  if (outgoing.has(rootId)) {
    const queue = [rootId];
    distances.set(rootId, 0);

    for (let index = 0; index < queue.length; index++) {
      const source = queue[index];

      for (const target of (
        outgoing.get(source) || []
      )) {
        if (distances.has(target)) {
          continue;
        }

        distances.set(
          target,
          distances.get(source) + 1
        );

        queue.push(target);
      }
    }
  }

  const reachedDistances = [
    ...distances.values(),
  ];

  const fallbackHop =
    reachedDistances.length
      ? Math.max(...reachedDistances) + 1
      : 1;

  const groups = new Map();

  for (const node of nodes) {
    const hop =
      distances.get(node.id) ??
      fallbackHop;

    if (!groups.has(hop)) {
      groups.set(hop, []);
    }

    groups.get(hop).push(node);
  }

  const orderedHops = [
    ...groups.keys(),
  ].sort((a, b) => a - b);

  const result = [];
  let columnOffset = 0;

  for (const hop of orderedHops) {
    const group = [...groups.get(hop)].sort(
      (a, b) => a.id.localeCompare(b.id)
    );

    const columnCount = Math.max(
      1,
      Math.ceil(group.length / MAX_ROWS)
    );

    for (
      let index = 0;
      index < group.length;
      index++
    ) {
      const node = group[index];

      const innerColumn =
        Math.floor(index / MAX_ROWS);

      const row = index % MAX_ROWS;

      result.push({
        id: node.id,
        type: "explorer",
        position: {
          x:
            (columnOffset + innerColumn) *
            (NODE_WIDTH + NODE_GAP_X),
          y:
            row * (NODE_HEIGHT + NODE_GAP_Y),
        },
        data: {
          nodeId: node.id,
          label: node.label || node.id,
          nodeType: node.type || "ENTITY",
          region: node.region,
          hop,
          isRoot: node.id === rootId,
          isSelected:
            node.id === selectedId,
        },
        draggable: false,
        connectable: false,
      });
    }

    columnOffset += columnCount + 1;
  }

  return result;
}

const ExplorerNode = memo(
  function ExplorerNode({ data }) {
    const color =
      TYPE_COLORS[data.nodeType] ||
      "#64748b";

    return (
      <div
        className={[
          "gx-node",
          data.isSelected
            ? "gx-node-selected"
            : "",
          data.isRoot
            ? "gx-node-root"
            : "",
        ].join(" ")}
        style={{
          "--gx-color": color,
          width: NODE_WIDTH,
          minHeight: NODE_HEIGHT,
        }}
      >
        <Handle
          type="target"
          position={Position.Left}
          isConnectable={false}
        />

        <span className="gx-node-type">
          {data.nodeType}
        </span>

        <strong title={data.label}>
          {data.label}
        </strong>

        <small>
          {data.nodeId} · Hop {data.hop}
        </small>

        <Handle
          type="source"
          position={Position.Right}
          isConnectable={false}
        />
      </div>
    );
  }
);

const nodeTypes = {
  explorer: ExplorerNode,
};

function ExplorerCanvas({
  graph,
  rootId,
  selectedId,
  onSelectNode,
}) {
  const nodes = useMemo(
    () => makeLayoutNodes(
      graph,
      rootId,
      selectedId
    ),
    [graph, rootId, selectedId]
  );

  const edges = useMemo(
    () => (graph?.edges || []).map(
      (edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "straight",
        style: {
          stroke: "#64748b",
          strokeWidth: 1,
          opacity: 0.3,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#64748b",
        },
      })
    ),
    [graph]
  );

  return (
    <div className="gx-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) =>
          onSelectNode(node.id)
        }
        nodesDraggable={false}
        nodesConnectable={false}
        onlyRenderVisibleElements
        minZoom={0.1}
        maxZoom={1.8}
        colorMode="dark"
        fitView
        fitViewOptions={{
          padding: 0.08,
          minZoom: 0.35,
          maxZoom: 1,
        }}
      >
        <Background
          color="#26364d"
          gap={24}
        />

        <Controls
          showInteractive={false}
        />

        <MiniMap
          pannable
          zoomable
          nodeColor={(node) =>
            TYPE_COLORS[node.data?.nodeType] ||
            "#64748b"
          }
          maskColor="rgba(0,0,0,0.65)"
        />
      </ReactFlow>
    </div>
  );
}

function GraphExplorerContent() {
  const [query, setQuery] =
    useState("");

  const [results, setResults] =
    useState([]);

  const [origin, setOrigin] =
    useState("BENCHMARK");

  const [rootId, setRootId] =
    useState("BENCH_000001");

  const [selectedId, setSelectedId] =
    useState("BENCH_000001");

  const [direction, setDirection] =
    useState("downstream");

  const [initialDepth, setInitialDepth] =
    useState(2);

  const [graph, setGraph] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [expanding, setExpanding] =
    useState(false);

  const [searching, setSearching] =
    useState(false);

  const [error, setError] =
    useState("");

  const [notice, setNotice] =
    useState("");

  const [reloadKey, setReloadKey] =
    useState(0);

  const [expandedIds, setExpandedIds] =
    useState(new Set());

  const expansionController = useRef(null);
  const graphVersion = useRef(0);
  const graphRef = useRef(null);
  const expansionBusy = useRef(false);

  const replaceGraph = useCallback(
    (nextGraph) => {
      graphRef.current = nextGraph;
      setGraph(nextGraph);
    },
    []
  );

  const cancelExpansion = useCallback(
    () => {
      expansionController.current?.abort();
      expansionController.current = null;
      expansionBusy.current = false;
      setExpanding(false);
    },
    []
  );

  // Search entities without loading
  // the entire Neo4j network.
  useEffect(() => {
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      setSearching(true);

      try {
        const params = new URLSearchParams({
          q: query,
          limit: "30",
        });

        if (origin !== "ALL") {
          params.set("origin", origin);
        }

        const data = await fetchJSON(
          `/api/explorer/entities?${params}`,
          controller.signal
        );

        if (!controller.signal.aborted) {
          setResults(data.entities || []);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setSearching(false);
        }
      }
    }, 350);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, origin]);

  // Load a new starting neighborhood.
  useEffect(() => {
    const controller = new AbortController();
    const version = ++graphVersion.current;

    cancelExpansion();
    setLoading(true);
    setError("");
    setNotice("");
    setExpandedIds(new Set());
    replaceGraph(null);

    async function loadRoot() {
      const params = new URLSearchParams({
        depth: String(initialDepth),
        direction,
        max_nodes: String(MAX_VISIBLE_NODES),
        max_relationships: String(MAX_VISIBLE_EDGES),
      });

      try {
        const incoming = await fetchJSON(
          `/api/explorer/neighborhood/${encodeURIComponent(
            rootId
          )}?${params}`,
          controller.signal
        );

        if (
          version !== graphVersion.current ||
          controller.signal.aborted
        ) {
          return;
        }

        const merged = mergeGraph(
          null,
          incoming,
          MAX_VISIBLE_NODES,
          MAX_VISIBLE_EDGES
        );

        replaceGraph(merged);
        setSelectedId(rootId);

        if (incoming.summary?.truncated) {
          setNotice(
            "The initial neighborhood was limited " +
            "by the API's node or edge cap."
          );
        }
      } catch (err) {
        if (
          version === graphVersion.current &&
          !controller.signal.aborted
        ) {
          setError(err.message);
        }
      } finally {
        if (
          version === graphVersion.current &&
          !controller.signal.aborted
        ) {
          setLoading(false);
        }
      }
    }

    loadRoot();

    return () => {
      controller.abort();
      cancelExpansion();
    };
  }, [
    rootId,
    initialDepth,
    direction,
    reloadKey,
    replaceGraph,
    cancelExpansion,
  ]);

  async function expandSelected() {
    if (
      !selectedId ||
      !graphRef.current ||
      loading ||
      expansionBusy.current
    ) {
      return;
    }

    const currentGraph = graphRef.current;

    const remainingNodes =
      MAX_VISIBLE_NODES -
      currentGraph.nodes.length;

    const remainingEdges =
      MAX_VISIBLE_EDGES -
      currentGraph.edges.length;

    if (remainingNodes <= 0 ||
        remainingEdges <= 0) {
      setNotice(
        "The visualization limit has been reached. " +
        "Reset the explorer or select another root."
      );
      return;
    }

    const version = graphVersion.current;
    const controller = new AbortController();

    expansionController.current = controller;
    expansionBusy.current = true;

    setExpanding(true);
    setError("");
    setNotice("");

    const params = new URLSearchParams({
      depth: "1",
      direction,
      max_nodes: String(
        Math.min(300, remainingNodes + 1)
      ),
      max_relationships: String(
        Math.min(1000, remainingEdges)
      ),
    });

    try {
      const incoming = await fetchJSON(
        `/api/explorer/neighborhood/${encodeURIComponent(
          selectedId
        )}?${params}`,
        controller.signal
      );

      if (
        controller.signal.aborted ||
        version !== graphVersion.current
      ) {
        return;
      }

      const merged = mergeGraph(
        graphRef.current,
        incoming,
        MAX_VISIBLE_NODES,
        MAX_VISIBLE_EDGES
      );

      replaceGraph(merged);

      setExpandedIds((current) => {
        const next = new Set(current);
        next.add(selectedId);
        return next;
      });

      const addedNodes = merged.addedNodes || 0;
      const addedEdges = merged.addedEdges || 0;

      setNotice(
        `Expansion completed: ${addedNodes} new nodes, ` +
        `${addedEdges} new edges.`
      );

      if (incoming.summary?.truncated) {
        setNotice(
          `Expansion was limited. Added ` +
          `${addedNodes} nodes and ${addedEdges} edges.`
        );
      }
    } catch (err) {
      if (
        !controller.signal.aborted &&
        version === graphVersion.current
      ) {
        setError(err.message);
      }
    } finally {
      if (version === graphVersion.current) {
        expansionBusy.current = false;
        expansionController.current = null;
        setExpanding(false);
      }
    }
  }

  function chooseRoot(nodeId) {
    if (!nodeId) return;

    // Changing root triggers a bounded fetch.
    // Re-selecting the same root explicitly
    // reloads its neighborhood.
    setRootId(nodeId);
    setSelectedId(nodeId);

    if (nodeId === rootId) {
      setReloadKey((value) => value + 1);
    }
  }

  function resetExplorer() {
    setReloadKey((value) => value + 1);
  }

  const displayedNodeCount =
    graph?.nodes?.length || 0;

  const displayedEdgeCount =
    graph?.edges?.length || 0;

  const selectedEntity =
    graph?.nodes?.find(
      (node) => node.id === selectedId
    );

  const canExpand =
    Boolean(selectedEntity) &&
    !loading &&
    !expanding &&
    displayedNodeCount < MAX_VISIBLE_NODES &&
    displayedEdgeCount < MAX_VISIBLE_EDGES;

  return (
    <section className="gx-panel">
      <div className="gx-heading">
        <div>
          <h2>
            <Network size={20} />
            Progressive Graph Explorer
          </h2>

          <p>
            Explore the 5,000-node benchmark
            network without loading every entity
            into the browser.
          </p>
        </div>
      </div>

      <div className="gx-search">
        <Search size={18} />

        <input
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          placeholder="Search entity name or ID..."
        />

        {searching && (
          <RefreshCw
            size={16}
            className="gx-spin"
          />
        )}
      </div>

      <div className="gx-results">
        {results.slice(0, 12).map((entity) => (
          <button
            type="button"
            key={entity.node_id}
            className={
              rootId === entity.node_id
                ? "gx-result selected"
                : "gx-result"
            }
            onClick={() =>
              chooseRoot(entity.node_id)
            }
          >
            <strong>
              {entity.node_name ||
                entity.node_id}
            </strong>

            <span>
              {entity.node_type || "ENTITY"}
            </span>
          </button>
        ))}
      </div>

      <div className="gx-options">
        <label>
          Network
          <select
            value={origin}
            onChange={(event) =>
              setOrigin(event.target.value)
            }
          >
            <option value="BENCHMARK">
              Benchmark
            </option>
            <option value="SYNTHETIC">
              Synthetic
            </option>
            <option value="DATACO">
              DataCo
            </option>
            <option value="ALL">
              All
            </option>
          </select>
        </label>

        <label>
          Direction
          <select
            value={direction}
            onChange={(event) =>
              setDirection(event.target.value)
            }
          >
            <option value="downstream">
              Downstream
            </option>
            <option value="upstream">
              Upstream
            </option>
            <option value="both">
              Both directions
            </option>
          </select>
        </label>

        <label>
          Initial hops
          <select
            value={initialDepth}
            onChange={(event) =>
              setInitialDepth(
                Number(event.target.value)
              )
            }
          >
            {[1, 2, 3, 4].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="gx-summary">
        <span>
          Root: <strong>{rootId}</strong>
        </span>

        <span>
          Nodes:{" "}
          <strong>
            {displayedNodeCount}/{MAX_VISIBLE_NODES}
          </strong>
        </span>

        <span>
          Edges:{" "}
          <strong>
            {displayedEdgeCount}/{MAX_VISIBLE_EDGES}
          </strong>
        </span>

        <span>
          Expanded:{" "}
          <strong>{expandedIds.size}</strong>
        </span>
      </div>

      <div className="gx-expand-toolbar">
        <div>
          <span className="gx-selected-label">
            Selected entity
          </span>

          <strong>
            {selectedEntity?.label ||
              selectedId ||
              "None"}
          </strong>

          <small>
            {selectedEntity?.type || ""}
            {" · "}
            {selectedId}
          </small>
        </div>

        <div className="gx-expand-actions">
          <button
            type="button"
            className="gx-expand-button"
            disabled={!canExpand}
            onClick={expandSelected}
          >
            <PlusCircle size={16} />

            {expanding
              ? "Expanding..."
              : "Expand Selected Node"}
          </button>

          <button
            type="button"
            className="gx-reset-button"
            onClick={resetExplorer}
            disabled={loading}
          >
            <RotateCcw size={16} />
            Reset Graph
          </button>
        </div>
      </div>

      {error && (
        <div className="gx-error">
          <AlertTriangle size={17} />
          {error}
        </div>
      )}

      {notice && (
        <div className="gx-notice">
          {notice}
        </div>
      )}

      {loading && (
        <p className="gx-loading">
          Loading starting neighborhood...
        </p>
      )}

      {graph && (
        <ExplorerCanvas
          graph={graph}
          rootId={rootId}
          selectedId={selectedId}
          onSelectNode={setSelectedId}
        />
      )}

      <p className="gx-disclaimer">
        Expand a selected node to reveal its
        immediate neighbors. Benchmark entities
        are for visualization testing only;
        they are not part of the trained
        GraphSAGE prediction network.
      </p>
    </section>
  );
}

export default function GraphExplorer() {
  return (
    <ReactFlowProvider>
      <GraphExplorerContent />
    </ReactFlowProvider>
  );
}
