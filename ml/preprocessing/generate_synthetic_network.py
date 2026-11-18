from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "datasets" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

nodes = []
edges = []


def add_node(node_id, node_type, node_name, region):
    nodes.append({
        "node_id": node_id,
        "node_type": node_type,
        "node_name": node_name,
        "region": region,
        "data_origin": "SYNTHETIC"
    })


def add_edge(source, target, relationship, transport_days):
    edges.append({
        "source_id": source,
        "target_id": target,
        "relationship": relationship,
        "transport_days": transport_days,
        "data_origin": "SYNTHETIC"
    })


# 1. Suppliers
suppliers = [
    ("SUP_001", "Supplier Alpha", "India"),
    ("SUP_002", "Supplier Beta", "China"),
    ("SUP_003", "Supplier Gamma", "Germany"),
    ("SUP_004", "Supplier Delta", "Japan"),
    ("SUP_005", "Supplier Epsilon", "Vietnam"),
]

# 2. Manufacturers
manufacturers = [
    ("MFG_001", "Manufacturer One", "India"),
    ("MFG_002", "Manufacturer Two", "China"),
    ("MFG_003", "Manufacturer Three", "Germany"),
    ("MFG_004", "Manufacturer Four", "Vietnam"),
]

# 3. Ports
ports = [
    ("PORT_001", "Mumbai Port", "India"),
    ("PORT_002", "Shanghai Port", "China"),
    ("PORT_003", "Hamburg Port", "Germany"),
]

# 4. Warehouses
warehouses = [
    ("WH_001", "Bengaluru Warehouse", "India"),
    ("WH_002", "Delhi Warehouse", "India"),
    ("WH_003", "Singapore Warehouse", "Singapore"),
    ("WH_004", "Frankfurt Warehouse", "Germany"),
    ("WH_005", "Ho Chi Minh Warehouse", "Vietnam"),
]

# 5. Retailers
retailers = [
    ("RET_001", "Retailer North", "India"),
    ("RET_002", "Retailer South", "India"),
    ("RET_003", "Retailer East", "India"),
    ("RET_004", "Retailer West", "India"),
    ("RET_005", "Retailer Central", "Singapore"),
    ("RET_006", "Retailer Europe", "Germany"),
    ("RET_007", "Retailer Japan", "Japan"),
    ("RET_008", "Retailer Vietnam", "Vietnam"),
]

# Create all nodes
for group, node_type in [
    (suppliers, "SUPPLIER"),
    (manufacturers, "MANUFACTURER"),
    (ports, "PORT"),
    (warehouses, "WAREHOUSE"),
    (retailers, "RETAILER"),
]:
    for node_id, name, region in group:
        add_node(node_id, node_type, name, region)


# Supplier -> Manufacturer
for i, (supplier_id, _, _) in enumerate(suppliers):
    for offset in (0, 1):
        manufacturer = manufacturers[(i + offset) % len(manufacturers)]
        add_edge(
            supplier_id,
            manufacturer[0],
            "SUPPLIES",
            2 + ((i + offset) % 5)
        )

# Manufacturer -> Port
for i, (manufacturer_id, _, _) in enumerate(manufacturers):
    for offset in (0, 1):
        port = ports[(i + offset) % len(ports)]
        add_edge(
            manufacturer_id,
            port[0],
            "SHIPS_THROUGH",
            3 + ((i + offset) % 4)
        )

# Port -> Warehouse
for i, (port_id, _, _) in enumerate(ports):
    for offset in range(3):
        warehouse = warehouses[(i + offset) % len(warehouses)]
        add_edge(
            port_id,
            warehouse[0],
            "DISTRIBUTES_TO",
            1 + ((i + offset) % 3)
        )

# Warehouse -> Retailer
for i, (warehouse_id, _, _) in enumerate(warehouses):
    for offset in range(3):
        retailer = retailers[(i * 2 + offset) % len(retailers)]
        add_edge(
            warehouse_id,
            retailer[0],
            "DELIVERS_TO",
            1 + ((i + offset) % 4)
        )


nodes_df = pd.DataFrame(nodes)
edges_df = pd.DataFrame(edges)

nodes_path = OUTPUT_DIR / "synthetic_supply_chain_nodes.csv"
edges_path = OUTPUT_DIR / "synthetic_supply_chain_edges.csv"

nodes_df.to_csv(nodes_path, index=False)
edges_df.to_csv(edges_path, index=False)

print("Synthetic supply-chain network generated.")
print(f"Nodes: {len(nodes_df)}")
print(f"Relationships: {len(edges_df)}")
print(f"Node file: {nodes_path}")
print(f"Edge file: {edges_path}")
print("\nNode types:")
print(nodes_df["node_type"].value_counts().to_string())
print("\nRelationship types:")
print(edges_df["relationship"].value_counts().to_string())
