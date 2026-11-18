
from backend.app.database.neo4j_connection import (
    get_driver,
    NEO4J_DATABASE,
)


def fetch_supply_chain_graph():
    driver = get_driver()

    node_query = """
    MATCH (n:Entity)
    WHERE n.data_origin = 'SYNTHETIC'
    RETURN properties(n) AS node
    ORDER BY n.node_id
    """

    edge_query = """
    MATCH (a:Entity)-[r:CONNECTED]->(b:Entity)
    WHERE a.data_origin = 'SYNTHETIC'
      AND b.data_origin = 'SYNTHETIC'
      AND r.data_origin = 'SYNTHETIC'
    RETURN
        a.node_id AS source,
        b.node_id AS target,
        properties(r) AS properties
    ORDER BY source, target
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        node_records = list(session.run(node_query))
        edge_records = list(session.run(edge_query))

    nodes = []

    for record in node_records:
        node = record["node"]

        nodes.append({
            "id": node["node_id"],
            "label": node.get("node_name", node["node_id"]),
            "type": node.get("node_type", "UNKNOWN"),
            "region": node.get("region", ""),
            "data_origin": node.get("data_origin", ""),
        })

    edges = []

    for index, record in enumerate(edge_records):
        props = record["properties"]

        edges.append({
            "id": f"edge-{index}",
            "source": record["source"],
            "target": record["target"],
            "relationship": props.get(
                "relationship", "CONNECTED"
            ),
            "transport_days": props.get("transport_days"),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
        "data_origin": "SYNTHETIC",
    }
