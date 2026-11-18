
import { useEffect, useMemo } from "react";

import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";
import "./SupplyChainGraph.css";


// =====================================================
// GRAPH CONFIGURATION
// =====================================================

const NODE_WIDTH = 210;
const NODE_HEIGHT = 110;

const COLUMN_GAP = 130;
const ROW_GAP = 38;

const TYPE_ORDER = [
  "SUPPLIER",
  "MANUFACTURER",
  "PORT",
  "WAREHOUSE",
  "RETAILER",
];

const TYPE_COLORS = {
  SUPPLIER: "#22c55e",
  MANUFACTURER: "#06b6d4",
  PORT: "#8b5cf6",
  WAREHOUSE: "#f59e0b",
  RETAILER: "#64748b",
};

const STATUS_COLORS = {
  NORMAL: "#22c55e",
  AFFECTED: "#f59e0b",
  DISRUPTED: "#ef4444",
};


// =====================================================
// CUSTOM ENTITY NODE
// =====================================================

function EntityNode({ data, selected }) {
  const status = data.status || "NORMAL";

  const statusColor =
    STATUS_COLORS[status] ||
    STATUS_COLORS.NORMAL;

  const typeColor =
    TYPE_COLORS[data.type] ||
    "#64748b";

  const delayDays = Number(data.delayDays);

  const hasDelay =
    data.delayDays != null &&
    Number.isFinite(delayDays) &&
    delayDays > 0;

  const isDisruptionSource =
    Boolean(data.isDisruptionSource);

  return (
    <div
      className={[
        "sc-entity-node",
        `sc-status-${status.toLowerCase()}`,
        selected ? "sc-node-selected" : "",
        data.pathHighlighted
          ? "sc-node-path"
          : "",
        hasDelay
          ? "sc-node-has-delay"
          : "",
      ].filter(Boolean).join(" ")}
      style={{
        "--status-color": statusColor,
        "--type-color": typeColor,
        width: NODE_WIDTH,
        minHeight: NODE_HEIGHT,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="sc-handle"
        isConnectable={false}
      />

      <div className="sc-node-top">
        <span className="sc-node-type">
          {data.type || "ENTITY"}
        </span>

        <span
          className="sc-node-status-dot"
          title={`Status: ${status}`}
        />
      </div>

      <strong className="sc-node-name">
        {data.label || data.nodeId}
      </strong>

      <div className="sc-node-bottom">
        <span>
          {data.region || "Unknown region"}
        </span>

        <span>{status}</span>
      </div>

      {hasDelay && (
        <div className="sc-delay-badge">
          <span>
            {isDisruptionSource
              ? "Source delay"
              : "Estimated delay"}
          </span>

          <strong>
            {delayDays.toFixed(1)} days
          </strong>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="sc-handle"
        isConnectable={false}
      />
    </div>
  );
}


// Keep nodeTypes outside the component so
// React Flow does not recreate custom nodes.

const nodeTypes = {
  entity: EntityNode,
};


// =====================================================
// FIT GRAPH WHEN NETWORK CHANGES
// =====================================================

function GraphFitController({ graphVersion }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      fitView({
        padding: 0.15,
        duration: 450,
        maxZoom: 1,
      });
    });

    return () => {
      cancelAnimationFrame(frame);
    };
  }, [graphVersion, fitView]);

  return null;
}


// =====================================================
// GRAPH CANVAS
// =====================================================

function GraphCanvas({
  graph,
  predictions = [],
  delay = null,
  selectedNode = "",
  highlightedPath = [],
  onSelectNode,
}) {

  // -------------------------------------------------
  // CLASSIFICATION PREDICTION LOOKUP
  // -------------------------------------------------

  const predictionMap = useMemo(() => {
    const map = new Map();

    for (const item of predictions || []) {
      if (!item?.node_id) continue;

      map.set(
        item.node_id,
        item.predicted_status || "NORMAL"
      );
    }

    return map;
  }, [predictions]);


  // -------------------------------------------------
  // DELAY REGRESSION LOOKUP
  // -------------------------------------------------

  const delayMap = useMemo(() => {
    const map = new Map();

    for (const item of delay?.results || []) {
      if (!item?.node_id) continue;

      map.set(item.node_id, {
        delayDays: Number(
          item.predicted_delay_days || 0
        ),
        isDownstream: Boolean(
          item.is_downstream
        ),
        isDisruptionSource: Boolean(
          item.is_disruption_source
        ),
      });
    }

    return map;
  }, [delay]);


  // -------------------------------------------------
  // HIGHLIGHTED PATH NODES
  // -------------------------------------------------

  const pathNodeSet = useMemo(() => {
    return new Set(
      Array.isArray(highlightedPath)
        ? highlightedPath
        : []
    );
  }, [highlightedPath]);


  // -------------------------------------------------
  // HIGHLIGHTED PATH EDGES
  // -------------------------------------------------

  const pathEdgeSet = useMemo(() => {
    const edges = new Set();

    if (!Array.isArray(highlightedPath)) {
      return edges;
    }

    for (
      let index = 0;
      index < highlightedPath.length - 1;
      index++
    ) {
      edges.add(
        `${highlightedPath[index]}->${highlightedPath[index + 1]}`
      );
    }

    return edges;
  }, [highlightedPath]);


  // -------------------------------------------------
  // BUILD GRAPH NODES
  // -------------------------------------------------

  const nodes = useMemo(() => {
    const sourceNodes = graph?.nodes || [];

    const groups = {};

    for (const type of TYPE_ORDER) {
      groups[type] = [];
    }

    for (const node of sourceNodes) {
      const type = node.type || "OTHER";

      if (!groups[type]) {
        groups[type] = [];
      }

      groups[type].push(node);
    }

    const types = [
      ...TYPE_ORDER,
      ...Object.keys(groups).filter(
        (type) => !TYPE_ORDER.includes(type)
      ),
    ];

    const maxRows = Math.max(
      1,
      ...types.map(
        (type) => groups[type].length
      )
    );

    const result = [];

    types.forEach((type, columnIndex) => {
      const group = groups[type];

      const groupHeight =
        group.length *
        (NODE_HEIGHT + ROW_GAP);

      const maxHeight =
        maxRows *
        (NODE_HEIGHT + ROW_GAP);

      const verticalOffset =
        (maxHeight - groupHeight) / 2;

      group.forEach((node, rowIndex) => {
        const status =
          predictionMap.get(node.id) ||
          "NORMAL";

        const delayInfo =
          delayMap.get(node.id);

        result.push({
          id: node.id,
          type: "entity",

          position: {
            x:
              columnIndex *
              (NODE_WIDTH + COLUMN_GAP),

            y:
              verticalOffset +
              rowIndex *
                (NODE_HEIGHT + ROW_GAP),
          },

          data: {
            nodeId: node.id,
            label: node.label,
            type: node.type,
            region: node.region,
            status,

            delayDays:
              delayInfo?.delayDays ?? null,

            isDownstream:
              delayInfo?.isDownstream ?? false,

            isDisruptionSource:
              delayInfo?.isDisruptionSource ??
              false,

            pathHighlighted:
              pathNodeSet.has(node.id),
          },

          selected:
            node.id === selectedNode,

          draggable: false,
          connectable: false,
        });
      });
    });

    return result;
  }, [
    graph,
    predictionMap,
    delayMap,
    selectedNode,
    pathNodeSet,
  ]);


  // -------------------------------------------------
  // BUILD GRAPH EDGES
  // -------------------------------------------------

  const edges = useMemo(() => {
    return (graph?.edges || []).map(
      (edge, index) => {

        const sourceStatus =
          predictionMap.get(edge.source) ||
          "NORMAL";

        const targetStatus =
          predictionMap.get(edge.target) ||
          "NORMAL";

        const sourceDelay =
          delayMap.get(edge.source);

        const targetDelay =
          delayMap.get(edge.target);

        const isPath =
          pathEdgeSet.has(
            `${edge.source}->${edge.target}`
          );

        const isAffected =
          sourceStatus !== "NORMAL" &&
          targetStatus !== "NORMAL";

        const isDelayed =
          (sourceDelay?.delayDays || 0) > 0 &&
          (targetDelay?.delayDays || 0) > 0;

        const stroke = isPath
          ? "#38bdf8"
          : isAffected || isDelayed
            ? "#f59e0b"
            : "#475569";

        return {
          id:
            edge.id ||
            `${edge.source}-${edge.target}-${index}`,

          source: edge.source,
          target: edge.target,

          type: "smoothstep",

          animated: isPath,

          style: {
            stroke,

            strokeWidth: isPath
              ? 3
              : isAffected || isDelayed
                ? 2
                : 1.2,

            opacity: isPath
              ? 1
              : isAffected || isDelayed
                ? 0.9
                : 0.35,
          },

          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: stroke,
            width: 15,
            height: 15,
          },

          data: {
            relationship:
              edge.relationship,
            transportDays:
              edge.transport_days,
          },
        };
      }
    );
  }, [
    graph,
    predictionMap,
    delayMap,
    pathEdgeSet,
  ]);


  // -------------------------------------------------
  // GRAPH VERSION
  // -------------------------------------------------

  // Only refit when the network structure changes.
  // Changing predictions or delay estimates
  // should not unexpectedly reset zoom.

  const graphVersion = useMemo(() => {
    const nodeIds = (graph?.nodes || [])
      .map((node) => node.id)
      .join("|");

    const edgeIds = (graph?.edges || [])
      .map(
        (edge) =>
          `${edge.source}->${edge.target}`
      )
      .join("|");

    return `${nodeIds}::${edgeIds}`;
  }, [graph]);


  // -------------------------------------------------
  // RENDER REACT FLOW
  // -------------------------------------------------

  return (
    <div className="sc-graph-container">

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}

        onNodeClick={(_, node) => {
          onSelectNode?.(node.id);
        }}

        fitView

        fitViewOptions={{
          padding: 0.15,
          maxZoom: 1,
        }}

        minZoom={0.2}
        maxZoom={2}

        nodesDraggable={false}
        nodesConnectable={false}

        elementsSelectable

        colorMode="dark"

        proOptions={{
          hideAttribution: true,
        }}
      >

        <GraphFitController
          graphVersion={graphVersion}
        />

        <Background
          color="#253449"
          gap={22}
          size={1}
        />

        <Controls
          position="bottom-left"
          showInteractive={false}
        />

        <MiniMap
          position="bottom-right"
          pannable
          zoomable

          nodeColor={(node) => {
            const status =
              node.data?.status ||
              "NORMAL";

            return (
              STATUS_COLORS[status] ||
              "#64748b"
            );
          }}

          maskColor="rgba(5, 10, 20, 0.75)"
        />

      </ReactFlow>

    </div>
  );
}


// =====================================================
// EXPORTED COMPONENT
// =====================================================

export default function SupplyChainGraph(props) {
  return (
    <ReactFlowProvider>
      <GraphCanvas {...props} />
    </ReactFlowProvider>
  );
}
