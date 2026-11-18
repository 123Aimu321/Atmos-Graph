
import os
import pandas as pd

# ==========================================
# ATMOGRAPH - DATA CLEANING
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

RAW_PATH = os.path.join(
    BASE_DIR,
    "datasets",
    "raw",
    "DataCoSupplyChainDataset.csv"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "datasets",
    "processed"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_dataset():

    print("\n===== ATMOGRAPH DATA CLEANING =====")

    # Load original dataset
    df = pd.read_csv(
        RAW_PATH,
        encoding="latin1"
    )

    print("Original shape:", df.shape)

    # Remove columns that are not useful
    # or contain personal information
    columns_to_remove = [
        "Customer Email",
        "Customer Password",
        "Customer Fname",
        "Customer Lname",
        "Customer Street",
        "Customer Zipcode",
        "Order Zipcode",
        "Product Description",
        "Product Image"
    ]

    df = df.drop(
        columns=columns_to_remove,
        errors="ignore"
    )

    # Convert date columns
    date_columns = [
        "order date (DateOrders)",
        "shipping date (DateOrders)"
    ]

    for col in date_columns:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )

    # Remove rows with invalid essential values
    required_columns = [
        "Order Id",
        "Product Card Id",
        "Order Country",
        "Shipping Mode",
        "Days for shipping (real)",
        "Late_delivery_risk"
    ]

    df = df.dropna(
        subset=required_columns
    )

    # Fill optional numerical missing values
    numerical_columns = df.select_dtypes(
        include="number"
    ).columns

    df[numerical_columns] = (
        df[numerical_columns].fillna(0)
    )

    # Remove duplicates
    df = df.drop_duplicates()

    # Create useful derived features
    df["delivery_delay"] = (
        df["Days for shipping (real)"]
        - df["Days for shipment (scheduled)"]
    ).clip(lower=0)

    df["order_year"] = (
        df["order date (DateOrders)"].dt.year
    )

    df["order_month"] = (
        df["order date (DateOrders)"].dt.month
    )

    # Export cleaned dataset
    output_path = os.path.join(
        OUTPUT_DIR,
        "cleaned_orders.csv"
    )

    df.to_csv(
        output_path,
        index=False
    )

    # Summary
    print("\n===== CLEANING COMPLETED =====")

    print("Final shape:", df.shape)

    print("Missing values:", df.isnull().sum().sum())

    print("Duplicate rows:", df.duplicated().sum())

    print("\nDelivery risk distribution:")
    print(
        df["Late_delivery_risk"].value_counts()
    )

    print("\nShipping modes:")
    print(
        df["Shipping Mode"].value_counts()
    )

    print("\nSaved file:")
    print(output_path)


if __name__ == "__main__":
    clean_dataset()
