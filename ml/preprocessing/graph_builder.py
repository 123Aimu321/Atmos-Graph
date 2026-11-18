
import os
import re
import pandas as pd

# ==========================================
# ATMOGRAPH - GRAPH DATASET GENERATOR
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

INPUT_PATH = os.path.join(
    BASE_DIR,
    "datasets",
    "processed",
    "cleaned_orders.csv"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "datasets",
    "processed"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def make_id(prefix, value):
    """Generate a stable ID from an entity name."""
    value = str(value).strip().upper()
    value = re.sub(r"[^A-Z0-9]+", "_", value)
    value = value.strip("_")
    return f"{prefix}_{value}"


def generate_graph():

    print("\n========== ATMOGRAPH GRAPH BUILDER ==========")

    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"Cleaned dataset not found: {INPUT_PATH}\n"
            "Run clean_data.py first."
        )

    df = pd.read_csv(INPUT_PATH)

    required = [
        "Product Card Id",
        "Product Name",
        "Product Category Id",
        "Category Name",
        "Order Country",
        "Market",
        "Shipping Mode",
        "Days for shipping (real)",
        "Late_delivery_risk",
        "Order Id"
    ]

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    nodes = {}
    edges = []

    # --------------------------------------
    # 1. PRODUCT NODES
    # --------------------------------------

    products = (
        df.groupby("Product Card Id")
        .agg(
            node_name=("Product Name", "first"),
            order_count=("Order Id", "nunique"),
            avg_shipping_days=("Days for shipping (real)", "mean"),
            late_delivery_rate=("Late_delivery_risk", "mean")
        )
        .reset_index()
    )

    for _, row in products.iterrows():

        node_id = make_id("PRODUCT", row["Product Card Id"])

        nodes[node_id] = {
            "node_id": node_id,
            "node_name": str(row["node_name"]),
            "node_type": "PRODUCT",
            "country": "",
            "reliability": "",
            "inventory_level": "",
            "avg_shipping_days": round(row["avg_shipping_days"], 2),
            "late_delivery_rate": round(row["late_delivery_rate"], 4),
            "order_count": int(row["order_count"])
        }

    # --------------------------------------
    # 2. COUNTRY NODES
    # --------------------------------------

    countries = (
        df.groupby("Order Country")
        .agg(
            avg_shipping_days=("Days for shipping (real)", "mean"),
            late_delivery_rate=("Late_delivery_risk", "mean"),
            order_count=("Order Id", "nunique")
        )
        .reset_index()
    )

    for _, row in countries.iterrows():

        country = str(row["Order Country"]).strip()
        node_id = make_id("COUNTRY", country)

        reliability = 1 - row["late_delivery_rate"]

        nodes[node_id] = {
            "node_id": node_id,
            "node_name": country,
            "node_type": "COUNTRY",
            "country": country,
            "reliability": round(reliability, 4),
            "inventory_level": "",
            "avg_shipping_days": round(row["avg_shipping_days"], 2),
            "late_delivery_rate": round(row["late_delivery_rate"], 4),
            "order_count": int(row["order_count"])
        }

    # --------------------------------------
    # 3. CATEGORY NODES
    # --------------------------------------

    categories = (
        df[["Product Category Id", "Category Name"]]
        .drop_duplicates()
    )

    for _, row in categories.iterrows():

        category_id = make_id(
            "CATEGORY",
            row["Product Category Id"]
        )

        nodes[category_id] = {
            "node_id": category_id,
            "node_name": str(row["Category Name"]),
            "node_type": "CATEGORY",
            "country": "",
            "reliability": "",
            "inventory_level": "",
            "avg_shipping_days": "",
            "late_delivery_rate": "",
            "order_count": ""
        }

    # --------------------------------------
    # 4. MARKET NODES
    # --------------------------------------

    markets = df["Market"].dropna().unique()

    for market in markets:

        node_id = make_id("MARKET", market)

        nodes[node_id] = {
            "node_id": node_id,
            "node_name": str(market),
            "node_type": "MARKET",
            "country": "",
            "reliability": "",
            "inventory_level": "",
            "avg_shipping_days": "",
            "late_delivery_rate": "",
            "order_count": ""
        }

    # --------------------------------------
    # 5. SHIPPING MODE NODES
    # --------------------------------------

    shipping_modes = df["Shipping Mode"].dropna().unique()

    for mode in shipping_modes:

        node_id = make_id("SHIPPING", mode)

        nodes[node_id] = {
            "node_id": node_id,
            "node_name": str(mode),
            "node_type": "SHIPPING_MODE",
            "country": "",
            "reliability": "",
            "inventory_level": "",
            "avg_shipping_days": "",
            "late_delivery_rate": "",
            "order_count": ""
        }

    # --------------------------------------
    # 6. PRODUCT -> COUNTRY EDGES
    # --------------------------------------

    product_country = (
        df.groupby(["Product Card Id", "Order Country"])
        .agg(
            lead_time_days=("Days for shipping (real)", "mean"),
            late_delivery_rate=("Late_delivery_risk", "mean"),
            order_count=("Order Id", "nunique")
        )
        .reset_index()
    )

    for _, row in product_country.iterrows():

        source = make_id("PRODUCT", row["Product Card Id"])
        target = make_id("COUNTRY", row["Order Country"])

        edges.append({
            "source_id": source,
            "target_id": target,
            "relationship": "DELIVERED_TO",
            "lead_time_days": round(row["lead_time_days"], 2),
            "late_delivery_rate": round(row["late_delivery_rate"], 4),
            "order_count": int(row["order_count"])
        })

    # --------------------------------------
    # 7. PRODUCT -> CATEGORY EDGES
    # --------------------------------------

    product_categories = (
        df[["Product Card Id", "Product Category Id"]]
        .drop_duplicates()
    )

    for _, row in product_categories.iterrows():

        source = make_id("PRODUCT", row["Product Card Id"])
        target = make_id("CATEGORY", row["Product Category Id"])

        edges.append({
            "source_id": source,
            "target_id": target,
            "relationship": "BELONGS_TO",
            "lead_time_days": "",
            "late_delivery_rate": "",
            "order_count": ""
        })

    # --------------------------------------
    # 8. COUNTRY -> MARKET EDGES
    # --------------------------------------

    country_markets = (
        df[["Order Country", "Market"]]
        .drop_duplicates()
    )

    for _, row in country_markets.iterrows():

        source = make_id("COUNTRY", row["Order Country"])
        target = make_id("MARKET", row["Market"])

        edges.append({
            "source_id": source,
            "target_id": target,
            "relationship": "ASSOCIATED_WITH",
            "lead_time_days": "",
            "late_delivery_rate": "",
            "order_count": ""
        })

    # --------------------------------------
    # 9. COUNTRY -> SHIPPING MODE EDGES
    # --------------------------------------

    country_shipping = (
        df.groupby(["Order Country", "Shipping Mode"])
        .agg(
            lead_time_days=("Days for shipping (real)", "mean"),
            late_delivery_rate=("Late_delivery_risk", "mean"),
            order_count=("Order Id", "nunique")
        )
        .reset_index()
    )

    for _, row in country_shipping.iterrows():

        source = make_id("COUNTRY", row["Order Country"])
        target = make_id("SHIPPING", row["Shipping Mode"])

        edges.append({
            "source_id": source,
            "target_id": target,
            "relationship": "USES_SHIPPING_MODE",
            "lead_time_days": round(row["lead_time_days"], 2),
            "late_delivery_rate": round(row["late_delivery_rate"], 4),
            "order_count": int(row["order_count"])
        })

    # --------------------------------------
    # 10. EXPORT GRAPH DATA
    # --------------------------------------

    nodes_df = pd.DataFrame(list(nodes.values()))

    edges_df = pd.DataFrame(edges)

    nodes_path = os.path.join(
        OUTPUT_DIR,
        "nodes.csv"
    )

    edges_path = os.path.join(
        OUTPUT_DIR,
        "edges.csv"
    )

    nodes_df.to_csv(nodes_path, index=False)
    edges_df.to_csv(edges_path, index=False)

    # --------------------------------------
    # 11. VALIDATION
    # --------------------------------------

    node_ids = set(nodes_df["node_id"])

    invalid_edges = edges_df[
        ~edges_df["source_id"].isin(node_ids)
        | ~edges_df["target_id"].isin(node_ids)
    ]

    print("\n========== GRAPH GENERATION COMPLETE ==========")

    print("Total nodes:", len(nodes_df))
    print("Total edges:", len(edges_df))

    print("\nNode distribution:")
    print(nodes_df["node_type"].value_counts())

    print("\nRelationship distribution:")
    print(edges_df["relationship"].value_counts())

    print("\nInvalid edges:", len(invalid_edges))

    print("\nSaved files:")
    print(nodes_path)
    print(edges_path)

    if len(invalid_edges) > 0:
        raise ValueError(
            "Graph contains invalid edges. Check node IDs."
        )

    print("\nGraph validation successful!")


if __name__ == "__main__":
    generate_graph()
