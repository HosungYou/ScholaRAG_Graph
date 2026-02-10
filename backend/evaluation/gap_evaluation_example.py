"""
Gap Detection Evaluation Example

This script demonstrates how to use the gap evaluation system to assess
the quality of gap detection against ground truth annotations.

Usage:
    python gap_evaluation_example.py
"""

import asyncio
import json
from pathlib import Path

from backend.evaluation.benchmark import evaluate_gap_detection_with_data
from backend.graph.gap_detector import GapDetector


async def example_gap_evaluation():
    """
    Example workflow for gap detection evaluation.

    Steps:
    1. Load ground truth gaps from annotation file
    2. Run gap detection on a project (simulated here)
    3. Compare detected gaps against ground truth
    4. Generate evaluation report
    """

    # Step 1: Load ground truth
    ground_truth_path = Path(__file__).parent / "gap_evaluation_data" / "ai_education_gaps.json"

    with open(ground_truth_path, "r", encoding="utf-8") as f:
        ground_truth_data = json.load(f)

    ground_truth_gaps = ground_truth_data["ground_truth_gaps"]
    print(f"Loaded {len(ground_truth_gaps)} ground truth gaps")

    # Step 2: Simulate detected gaps (in practice, these come from GapDetector.analyze_graph())
    # This would normally be:
    # detector = GapDetector(llm_provider=llm)
    # analysis = await detector.analyze_graph(concepts, relationships)
    # detected_gaps_raw = analysis["gaps"]

    # For this example, we'll create mock detected gaps
    detected_gaps = [
        {
            "id": "detected-gap-1",
            "cluster_a_id": 0,
            "cluster_b_id": 1,
            "gap_strength": 0.05,
            "cluster_a_names": ["ai chatbot", "conversational agent"],
            "cluster_b_names": ["low-resource languages", "language diversity"],
        },
        {
            "id": "detected-gap-2",
            "cluster_a_id": 0,
            "cluster_b_id": 2,
            "gap_strength": 0.08,
            "cluster_a_names": ["ai assisted learning", "adaptive learning"],
            "cluster_b_names": ["longitudinal study", "retention"],
        },
        {
            "id": "detected-gap-3",
            "cluster_a_id": 1,
            "cluster_b_id": 2,
            "gap_strength": 0.12,
            "cluster_a_names": ["personalized learning", "recommendation"],
            "cluster_b_names": ["cognitive load", "working memory"],
        },
        {
            "id": "detected-gap-4",
            "cluster_a_id": 2,
            "cluster_b_id": 3,
            "gap_strength": 0.15,
            "cluster_a_names": ["neural networks", "deep learning"],  # False positive
            "cluster_b_names": ["computer vision", "image processing"],
        },
    ]

    print(f"Running evaluation with {len(detected_gaps)} detected gaps")

    # Step 3: Evaluate
    result = await evaluate_gap_detection_with_data(
        ground_truth_gaps=ground_truth_gaps,
        detected_gaps=detected_gaps,
        concept_match_threshold=0.3,
        output_dir="evaluation_results/gap_detection",
    )

    # Step 4: Display results
    print("\n" + "=" * 60)
    print(result["summary"])
    print("=" * 60)
    print(f"\nResults saved to: {result['results_file']}")
    print(f"Summary saved to: {result['summary_file']}")

    # Additional analysis
    gap_result = result["result"]
    print(f"\nPrecision: {gap_result.gap_precision:.2%}")
    print(f"Recall: {gap_result.gap_recall:.2%}")
    print(f"F1 Score: {gap_result.gap_f1:.2%}")

    if gap_result.matched_gaps:
        print(f"\nMatched {len(gap_result.matched_gaps)} gaps:")
        for gt_gap, det_gap in gap_result.matched_gaps:
            print(f"  - {gt_gap['gap_id']}: {gt_gap['description'][:50]}...")

    if gap_result.unmatched_ground_truth:
        print(f"\nMissed {len(gap_result.unmatched_ground_truth)} ground truth gaps:")
        for gap in gap_result.unmatched_ground_truth:
            print(f"  - {gap['gap_id']}: {gap['description'][:50]}...")

    if gap_result.unmatched_detected:
        print(f"\nFalse positives: {len(gap_result.unmatched_detected)} detected gaps without ground truth match")


async def real_world_example():
    """
    Real-world example showing how to integrate with actual gap detection.

    This would be called from a router or service that has access to the database.
    """
    # Pseudocode for real implementation:

    # 1. Load project data from database
    # async with database.get_session() as session:
    #     concepts = await session.execute(select(Entity).where(Entity.project_id == project_id))
    #     relationships = await session.execute(select(Relationship).where(...))

    # 2. Run gap detection
    # from backend.llm.provider import get_llm_provider
    # llm = get_llm_provider()
    # detector = GapDetector(llm_provider=llm)
    # analysis = await detector.analyze_graph(concepts, relationships)

    # 3. Convert to evaluation format
    # concepts_by_id = {c.id: {"name": c.name} for c in concepts}
    # detected_gaps_for_eval = [
    #     {
    #         "id": gap.id,
    #         "cluster_a_id": gap.cluster_a_id,
    #         "cluster_b_id": gap.cluster_b_id,
    #         "gap_strength": gap.gap_strength,
    #         "cluster_a_names": [concepts_by_id[cid]["name"] for cid in gap.concept_a_ids],
    #         "cluster_b_names": [concepts_by_id[cid]["name"] for cid in gap.concept_b_ids],
    #     }
    #     for gap in analysis["gaps"]
    # ]

    # 4. Load ground truth and evaluate
    # ground_truth_path = "path/to/ground_truth.json"
    # with open(ground_truth_path) as f:
    #     gt_data = json.load(f)
    #
    # result = await evaluate_gap_detection_with_data(
    #     ground_truth_gaps=gt_data["ground_truth_gaps"],
    #     detected_gaps=detected_gaps_for_eval,
    # )

    print("See example_gap_evaluation() for a working demonstration")


if __name__ == "__main__":
    asyncio.run(example_gap_evaluation())
