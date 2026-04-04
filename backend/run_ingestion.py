"""
FinBot Ingestion CLI Script
Run this to ingest all documents from the data/ directory into Qdrant.

Usage:
    cd backend
    python run_ingestion.py [--recreate]
"""

import sys
import logging
import argparse

# Ensure the app package is importable
sys.path.insert(0, ".")

from app.ingestion.ingest import run_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="FinBot Document Ingestion")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the Qdrant collection before ingesting",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Override the data directory path",
    )
    args = parser.parse_args()

    result = run_ingestion(data_dir=args.data_dir, recreate=args.recreate)
    print(f"\nIngestion Summary: {result['documents']} documents, {result['chunks']} chunks")


if __name__ == "__main__":
    main()
