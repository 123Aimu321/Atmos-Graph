import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Find the root .env file
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    raise RuntimeError("Neo4j environment variables are missing.")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)


def verify_connection():
    driver.verify_connectivity()
    print("Neo4j connection successful!")


def close_connection():
    driver.close()


def get_driver():
    return driver


if __name__ == "__main__":
    try:
        verify_connection()
    finally:
        close_connection()
