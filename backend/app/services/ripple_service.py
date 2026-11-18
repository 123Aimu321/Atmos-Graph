
from collections import deque

from backend.app.database.neo4j_connection import get_driver


def analyze_ripple(disrupted_node: str):
    driver = get_driver()

    query = """
    MATCH (n:Entity)
    WHERE n.data_origin = 'SYNTHETIC'
    OPTIONAL MATCH (n)-[r:CONNECTED]->(m:Entity)
    WHERE m.data_origin = 'SYNTHETIC'
    RETURN n.node_id AS node_id,
           n.node_name AS node_name,
           collect(m.node_id) AS neighbors
    """

    with driver.session() as session:
        records = list(session.run(query))

    adjacency = {}
    names = {}

    for record in records:
        node_id = record["node_id"]
        adjacency[node_id] = [
            n for n in record["neighbors"] if n
        ]
        names[node_id] = record["node_name"] or node_id

    if disrupted_node not in adjacency:
        raise ValueError(
            f"Unknown disruption node: {disrupted_node}"
        )

    queue = deque([disrupted_node])
    distances = {disrupted_node: 0}
    parents = {disrupted_node: None}

    while queue:
        current = queue.popleft()

        for neighbor in adjacency[current]:
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                parents[neighbor] = current
                queue.append(neighbor)

    affected_paths = []

    for node_id, distance in distances.items():
        if node_id == disrupted_node:
            continue

        path = []
        current = node_id

        while current is not None:
            path.append(current)
            current = parents[current]

        path.reverse()

        affected_paths.append({
            "node_id": node_id,
            "node_name": names.get(node_id, node_id),
            "hops": distance,
            "path": path,
            "path_names": [
                names.get(item, item) for item in path
            ],
        })

    affected_paths.sort(
        key=lambda item: (item["hops"], item["node_id"])
    )

    return {
        "disrupted_node": disrupted_node,
        "disrupted_name": names[disrupted_node],
        "reachable_downstream": len(affected_paths),
        "max_hops": max(distances.values()),
        "affected_paths": affected_paths,
        "method": "Directed shortest-path reachability",
    }
