
import os

from backend.app.database.neo4j_connection import (
    get_driver,
)


MAX_NODES = 1500
MAX_RELATIONSHIPS = 6000


def database_name():
    return os.getenv("NEO4J_DATABASE", "neo4j")


def search_entities(
    query="",
    limit=30,
    offset=0,
    data_origin=None,
):
    """
    Search graph entities using indexed IDs
    or names. Returns a bounded result page.
    """
    query = str(query or "").strip()
    limit = min(max(int(limit), 1), 100)
    offset = max(int(offset), 0)

    if data_origin not in (
    None,
    "SYNTHETIC",
    "DATACO",
    "BENCHMARK",
):
        raise ValueError(
            "Unsupported data origin"
        )

    cypher = """
    MATCH (e:Entity)
    WHERE
        ($origin IS NULL
         OR e.data_origin = $origin)
        AND (
            $search = ''
            OR toLower(toString(e.node_id))
                CONTAINS toLower($search)
            OR toLower(toString(e.node_name))
                CONTAINS toLower($search)
        )
    RETURN
        e.node_id AS node_id,
        coalesce(
            e.node_name,
            e.node_id
        ) AS node_name,
        e.node_type AS node_type,
        e.region AS region,
        e.data_origin AS data_origin
    ORDER BY node_name, node_id
    SKIP $offset
    LIMIT $limit
    """

    driver = get_driver()

    with driver.session(
        database=database_name()
    ) as session:
        records = session.execute_read(
            lambda tx: [
                dict(record)
                for record in tx.run(
                    cypher,
                    search=query,
                    origin=data_origin,
                    offset=offset,
                    limit=limit,
                )
            ]
        )

    return {
        "query": query,
        "offset": offset,
        "limit": limit,
        "entities": records,
        "returned": len(records),
        "has_more": len(records) == limit,
    }


def get_neighborhood(
    node_id,
    depth=2,
    max_nodes=150,
    max_relationships=500,
    direction="downstream",
):
    """
    Load a directed subgraph around one entity.

    - downstream: follow outgoing CONNECTED
    - upstream: follow incoming CONNECTED
    - both: follow either direction

    Edges are only returned when BOTH endpoints
    belong to the selected node set.
    """
    depth = int(depth)
    max_nodes = int(max_nodes)
    max_relationships = int(max_relationships)

    if not 1 <= depth <= 4:
        raise ValueError("depth must be 1–4")

    if not 1 <= max_nodes <= MAX_NODES:
        raise ValueError(
            f"max_nodes must be 1–{MAX_NODES}"
        )

    if not 1 <= max_relationships <= MAX_RELATIONSHIPS:
        raise ValueError(
            "Invalid max_relationships"
        )

    if direction not in (
        "downstream",
        "upstream",
        "both",
    ):
        raise ValueError("Invalid direction")

    driver = get_driver()

    with driver.session(
        database=database_name()
    ) as session:

        def read_graph(tx):
            source_record = tx.run(
                """
                MATCH (e:Entity {node_id: $node_id})
                RETURN
                    e.node_id AS id,
                    coalesce(
                        e.node_name,
                        e.node_id
                    ) AS label,
                    e.node_type AS type,
                    e.region AS region,
                    e.data_origin AS data_origin
                LIMIT 1
                """,
                node_id=node_id,
            ).single()

            if not source_record:
                return None

            source = dict(source_record)

            discovered = {
                source["id"]: {
                    **source,
                    "hop": 0,
                }
            }

            frontier = [source["id"]]
            truncated = False

            # Query each frontier in batches. Each
            # hop is bounded by the remaining
            # number of requested nodes.
            for hop in range(1, depth + 1):
                if not frontier:
                    break

                remaining = (
                    max_nodes - len(discovered)
                )

                if remaining <= 0:
                    truncated = True
                    break

                if direction == "downstream":
                    pattern = (
                        "(a)-[:CONNECTED]->(b)"
                    )
                elif direction == "upstream":
                    pattern = (
                        "(a)<-[:CONNECTED]-(b)"
                    )
                else:
                    pattern = (
                        "(a)-[:CONNECTED]-(b)"
                    )

                cypher = f"""
                MATCH {pattern}
                WHERE a.node_id IN $frontier
                  AND coalesce(a.data_origin, 'UNSPECIFIED') = $origin
                  AND coalesce(b.data_origin, 'UNSPECIFIED') = $origin
                  AND NOT (b.node_id IN $discovered)
                RETURN DISTINCT
                    b.node_id AS id,
                    coalesce(
                        b.node_name,
                        b.node_id
                    ) AS label,
                    b.node_type AS type,
                    b.region AS region,
                    b.data_origin AS data_origin
                ORDER BY id
                LIMIT $limit
                """

                # Fetch one extra result to detect
                # whether we had to truncate.
                records = list(
                    tx.run(
                        cypher,
                        frontier=frontier,
                        discovered=list(discovered),
                        origin=source["data_origin"] or "UNSPECIFIED",
                        limit=remaining + 1,
                    )
                )

                next_frontier = []

                for record in records:
                    node = dict(record)
                    node_id_value = node.get("id")

                    if not node_id_value:
                        continue

                    if node_id_value in discovered:
                        continue

                    if len(discovered) >= max_nodes:
                        truncated = True
                        break

                    discovered[node_id_value] = {
                        **node,
                        "hop": hop,
                    }

                    next_frontier.append(
                        node_id_value
                    )

                if len(records) > remaining:
                    truncated = True

                frontier = next_frontier

            ids = list(discovered)

            # Return only edges within the
            # selected subgraph.
            edge_records = list(
                tx.run(
                    """
                    MATCH (a:Entity)-[r:CONNECTED]->
                          (b:Entity)
                    WHERE a.node_id IN $ids
                      AND b.node_id IN $ids
                      AND coalesce(a.data_origin, 'UNSPECIFIED') = $origin
                      AND coalesce(b.data_origin, 'UNSPECIFIED') = $origin
                    RETURN
                        a.node_id AS source,
                        b.node_id AS target,
                        coalesce(
                            r.relationship,
                            type(r)
                        ) AS relationship,
                        r.transport_days AS transport_days,
                        elementId(r) AS edge_id
                    ORDER BY source, target, edge_id
                    LIMIT $limit
                    """,
                    ids=ids,
                    origin=source["data_origin"] or "UNSPECIFIED",
                    limit=max_relationships + 1,
                )
            )

            if len(edge_records) > max_relationships:
                truncated = True

            edges = []

            for record in edge_records[
                :max_relationships
            ]:
                edge = dict(record)

                edges.append({
                    "id": edge["edge_id"],
                    "source": edge["source"],
                    "target": edge["target"],
                    "relationship": (
                        edge["relationship"]
                    ),
                    "transport_days": (
                        edge["transport_days"]
                    ),
                })

            nodes = list(discovered.values())

            return {
                "source_node": node_id,
                "direction": direction,
                "depth": depth,
                "nodes": nodes,
                "edges": edges,
                "summary": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "truncated": truncated,
                    "max_nodes": max_nodes,
                    "max_relationships": (
                        max_relationships
                    ),
                },
            }

        return session.execute_read(read_graph)
