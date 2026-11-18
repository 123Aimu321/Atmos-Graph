
import { useState } from "react";
import {
  ArrowRight,
  GitBranch,
  MapPin,
  Route,
} from "lucide-react";

export default function RipplePathExplorer({
  ripple,
  onHighlightPath,
  onClearPath,
}) {
  const [activeNode, setActiveNode] = useState(null);

  if (!ripple) {
    return (
      <div className="ripple-empty">
        Run a disruption simulation to explore
        downstream supply-chain paths.
      </div>
    );
  }

  const paths = ripple.affected_paths || [];

  function selectPath(item) {
    setActiveNode(item.node_id);
    onHighlightPath(item.path);
  }

  function clearPath() {
    setActiveNode(null);
    onClearPath();
  }

  return (
    <div className="ripple-explorer">
      <div className="ripple-header">
        <div>
          <h2>Ripple Path Explorer</h2>
          <p>
            Trace downstream exposure from{" "}
            <strong>{ripple.disrupted_name}</strong>
          </p>
        </div>

        <button
          className="ripple-clear"
          onClick={clearPath}
        >
          Clear Highlight
        </button>
      </div>

      <div className="ripple-stats">
        <div>
          <GitBranch size={18} />
          <strong>{ripple.reachable_downstream}</strong>
          <span>Reachable entities</span>
        </div>

        <div>
          <Route size={18} />
          <strong>{ripple.max_hops}</strong>
          <span>Maximum hops</span>
        </div>
      </div>

      <div className="ripple-path-list">
        {paths.map((item) => (
          <button
            key={item.node_id}
            className={
              "ripple-path-item " +
              (activeNode === item.node_id
                ? "ripple-path-active"
                : "")
            }
            onClick={() => selectPath(item)}
          >
            <div className="ripple-path-title">
              <span>
                <MapPin size={15} />
                {item.node_name}
              </span>

              <span className="ripple-hop-badge">
                {item.hops} {item.hops === 1 ? "hop" : "hops"}
              </span>
            </div>

            <div className="ripple-breadcrumb">
              {item.path_names.map((name, index) => (
                <span key={`${item.node_id}-${index}`}>
                  {index > 0 && <ArrowRight size={13} />}
                  {name}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
