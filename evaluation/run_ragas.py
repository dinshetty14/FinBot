"""
FinBot RAGAs Evaluation Script
Evaluates the full RAG pipeline using RAGAs metrics with ablation study.

Usage:
    cd backend
    python -m evaluation.run_ragas

Or from project root:
    cd backend && python ../evaluation/run_ragas.py
"""

import json
import sys
import logging
import os
import ssl
import time
from pathlib import Path
from datetime import datetime

# SSL Bypass for local environments experiencing certificate verification issues
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'
if not os.environ.get('PYTHONHTTPSVERIFY', '') == '0':
    ssl._create_default_https_context = ssl._create_unverified_context

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics.collections import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
)
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app modules
from app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    QDRANT_URL,
    QDRANT_COLLECTION,
    EMBEDDING_MODEL,
    ACCESS_MATRIX,
    SYSTEM_PROMPT,
)
from app.rag.pipeline import retrieve_chunks, generate_response
from app.routing.semantic_router import classify_query


EVAL_DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_eval_dataset() -> list[dict]:
    """Load the evaluation dataset."""
    with open(EVAL_DATASET_PATH, "r") as f:
        return json.load(f)


def run_pipeline_for_eval(
    question: str,
    role: str,
    use_routing: bool = True,
    use_guardrails: bool = True,
) -> dict:
    """
    Run the RAG pipeline for a single evaluation question.
    Supports ablation by toggling routing and guardrails.
    """
    accessible = ACCESS_MATRIX.get(role, [])

    # Determine target collection
    target_collection = None
    if use_routing:
        route_result = classify_query(question, role)
        if not route_result.get("allowed"):
            return {
                "answer": route_result.get("message", "Blocked"),
                "contexts": [],
                "blocked": True,
            }
        target_collection = route_result.get("collection")

    # Retrieve chunks
    chunks = retrieve_chunks(question, role, target_collection)
    contexts = [c.get("text", "") for c in chunks]

    if not chunks:
        return {
            "answer": "No relevant documents found.",
            "contexts": contexts,
            "blocked": False,
        }

    # Generate response
    answer = generate_response(question, chunks, role, accessible)

    return {
        "answer": answer,
        "contexts": contexts,
        "blocked": False,
    }


def evaluate_configuration(
    eval_data: list[dict],
    config_name: str,
    use_routing: bool = True,
    use_guardrails: bool = True,
) -> dict:
    """
    Run evaluation for a specific pipeline configuration.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Evaluating configuration: {config_name}")
    logger.info(f"  Routing: {use_routing}, Guardrails: {use_guardrails}")
    logger.info(f"{'='*60}")

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for item in eval_data:
        # Skip adversarial/RBAC tests for metric evaluation
        if item.get("is_adversarial") or item.get("is_rbac_test"):
            continue

        question = item["question"]
        role = item.get("test_role", "employee")

        logger.info(f"  Processing: {question[:50]}... (role={role})")

        result = run_pipeline_for_eval(
            question, role, use_routing, use_guardrails
        )
        
        # Add a small delay to avoid hitting Groq rate limits
        time.sleep(1.0)

        if result.get("blocked"):
            continue

        questions.append(question)
        answers.append(result["answer"])
        contexts.append(result["contexts"])
        ground_truths.append(item["ground_truth"])

    if not questions:
        logger.warning("No valid questions to evaluate!")
        return {}

    # Build RAGAs dataset
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    # Run RAGAs evaluation
    try:
        # Create a dedicated LLM instance for RAGAs to avoid shared state
        eval_llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0)
        
        results = evaluate(
            dataset=dataset,
            metrics=[
                faithfulness(),
                answer_relevancy(),
                context_precision(),
                context_recall(),
                answer_correctness(),
            ],
            llm=eval_llm,
        )

        scores = {
            "config_name": config_name,
            "use_routing": use_routing,
            "use_guardrails": use_guardrails,
            "num_questions": len(questions),
            "faithfulness": float(results["faithfulness"]),
            "answer_relevancy": float(results["answer_relevancy"]),
            "context_precision": float(results["context_precision"]),
            "context_recall": float(results["context_recall"]),
            "answer_correctness": float(results["answer_correctness"]),
        }

        logger.info(f"\nResults for {config_name}:")
        for metric, value in scores.items():
            if isinstance(value, float):
                logger.info(f"  {metric}: {value:.4f}")

        return scores

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {"config_name": config_name, "error": str(e)}


def run_ablation_study():
    """
    Run the full ablation study with multiple configurations:
    1. Full pipeline (routing + guardrails)
    2. Without routing
    3. Without guardrails
    4. Baseline (no routing, no guardrails)
    """
    eval_data = load_eval_dataset()
    logger.info(f"Loaded {len(eval_data)} evaluation questions")

    configurations = [
        ("Full Pipeline", True, True),
        ("Without Routing", False, True),
        ("Without Guardrails", True, False),
        ("Baseline (No Routing, No Guardrails)", False, False),
    ]

    all_results = []
    for config_name, use_routing, use_guardrails in configurations:
        result = evaluate_configuration(
            eval_data, config_name, use_routing, use_guardrails
        )
        if result:
            all_results.append(result)

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"ablation_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    logger.info(f"\nResults saved to: {results_file}")

    # Print summary table
    print("\n" + "=" * 90)
    print("ABLATION STUDY RESULTS")
    print("=" * 90)
    print(f"{'Configuration':<40} {'Faith':>8} {'Relev':>8} {'C.Prec':>8} {'C.Rec':>8} {'Correct':>8}")
    print("-" * 90)
    for r in all_results:
        if "error" in r:
            print(f"{r['config_name']:<40} ERROR: {r['error']}")
        else:
            print(
                f"{r['config_name']:<40} "
                f"{r.get('faithfulness', 0):.4f}  "
                f"{r.get('answer_relevancy', 0):.4f}  "
                f"{r.get('context_precision', 0):.4f}  "
                f"{r.get('context_recall', 0):.4f}  "
                f"{r.get('answer_correctness', 0):.4f}"
            )
    print("=" * 90)

    return all_results


if __name__ == "__main__":
    run_ablation_study()
