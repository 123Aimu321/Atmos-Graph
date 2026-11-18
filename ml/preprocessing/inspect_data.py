
import pandas as pd

DATASET_PATH = (
    "datasets/raw/DataCoSupplyChainDataset.csv"
)

def inspect_dataset():

    df = pd.read_csv(DATASET_PATH, encoding="latin1")

    print("\n========== DATASET INFORMATION ==========")

    print("Shape:", df.shape)

    print("\nColumn Names:")
    print(df.columns.tolist())

    print("\nFirst 5 Rows:")
    print(df.head())

    print("\nMissing Values:")
    print(df.isnull().sum())

    print("\nDataset Information:")
    print(df.info())

    print("\nDuplicate Rows:", df.duplicated().sum())


if __name__ == "__main__":
    inspect_dataset()
