"""
Test extraction pipelines against evaluation datasets.

Usage:
    python -m scripts.test_extraction
    python -m scripts.test_extraction --verbose
    python -m scripts.test_extraction --dataset entity
"""

import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Set

from ..ingestion.entity_extractor import EntityExtractor
from ..ingestion.relation_extractor import RelationExtractor


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    passed: bool
    score: float
    max_score: float
    details: List[str]


def load_evaluation_dataset(name: str) -> Dict[str, Any]:
    """Load an evaluation dataset by name."""
    eval_dir = Path("evaluation/extraction")
    file_path = eval_dir / f"{name}_eval.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_entity_constraints(
    extracted: Set[str],
    constraints: Dict[str, Any],
    verbose: bool = False
) -> TestResult:
    """Check entity extraction against constraints."""
    details = []
    score = 0
    max_score = 0

    # Must extract (required)
    must_extract = constraints.get("must_extract", [])
    for entity in must_extract:
        max_score += 1
        if entity in extracted:
            score += 1
            if verbose:
                details.append(f"  ✓ Found required: {entity}")
        else:
            details.append(f"  ✗ MISSING required: {entity}")

    # Should extract (optional, no penalty)
    should_extract = constraints.get("should_extract", [])
    for entity in should_extract:
        if entity in extracted:
            score += 0.5
            max_score += 0.5
            if verbose:
                details.append(f"  ✓ Found optional: {entity}")
        else:
            max_score += 0.5
            if verbose:
                details.append(f"  ~ Missing optional: {entity}")

    # Must NOT extract (anti-hallucination)
    must_not_extract = constraints.get("must_not_extract", [])
    for entity in must_not_extract:
        max_score += 1
        if entity not in extracted:
            score += 1
            if verbose:
                details.append(f"  ✓ Correctly excluded: {entity}")
        else:
            details.append(f"  ✗ HALLUCINATED: {entity}")

    # Min count constraint
    min_count = constraints.get("min_entity_count", 0)
    if min_count > 0:
        max_score += 1
        if len(extracted) >= min_count:
            score += 1
            if verbose:
                details.append(f"  ✓ Count {len(extracted)} >= {min_count}")
        else:
            details.append(f"  ✗ Count {len(extracted)} < {min_count}")

    passed = score >= max_score * 0.7  # 70% threshold
    return TestResult(
        test_id="",
        passed=passed,
        score=score,
        max_score=max_score,
        details=details
    )


def check_relationship_constraints(
    relationships: List[tuple],
    constraints: Dict[str, Any],
    verbose: bool = False
) -> TestResult:
    """Check relationship extraction against constraints."""
    details = []
    score = 0
    max_score = 0

    # Convert relationships to set of (source, target) pairs
    rel_pairs = set()
    for rel in relationships:
        rel_pairs.add((rel.source, rel.target))
        rel_pairs.add((rel.target, rel.source))  # Bidirectional check

    # Must relate (required)
    must_relate = constraints.get("must_relate", [])
    for rel in must_relate:
        source = rel.get("source")
        target = rel.get("target")
        max_score += 1

        if (source, target) in rel_pairs or (target, source) in rel_pairs:
            score += 1
            if verbose:
                details.append(f"  ✓ Found: {source} -- {target}")
        else:
            details.append(f"  ✗ MISSING: {source} -- {target}")

    # Should relate (optional)
    should_relate = constraints.get("should_relate", [])
    for rel in should_relate:
        source = rel.get("source")
        target = rel.get("target")
        max_score += 0.5

        if (source, target) in rel_pairs or (target, source) in rel_pairs:
            score += 0.5
            if verbose:
                details.append(f"  ✓ Found optional: {source} -- {target}")
        else:
            if verbose:
                details.append(f"  ~ Missing optional: {source} -- {target}")

    # Must NOT relate (anti-hallucination)
    must_not_relate = constraints.get("must_not_relate", [])
    for rel in must_not_relate:
        source = rel.get("source")
        target = rel.get("target")
        max_score += 1

        if (source, target) not in rel_pairs and (target, source) not in rel_pairs:
            score += 1
            if verbose:
                details.append(f"  ✓ Correctly no relation: {source} -- {target}")
        else:
            details.append(f"  ✗ HALLUCINATED relation: {source} -- {target}")

    passed = max_score == 0 or score >= max_score * 0.6  # 60% threshold for relationships
    return TestResult(
        test_id="",
        passed=passed,
        score=score,
        max_score=max_score,
        details=details
    )


def test_entity_extraction(verbose: bool = False) -> Dict[str, Any]:
    """Run entity extraction tests."""
    print("\n" + "=" * 60)
    print("ENTITY EXTRACTION TESTS")
    print("=" * 60)

    dataset = load_evaluation_dataset("entity")
    extractor = EntityExtractor()

    results = []
    passed = 0
    failed = 0

    for item in dataset["items"]:
        test_id = item["id"]
        description = item.get("description", "")
        constraints = item.get("constraints", {})

        # Skip full chapter tests for now
        if item.get("input", {}).get("full_chapter"):
            continue

        text = item.get("input", {}).get("text", "")
        if not text:
            continue

        # Run extraction
        extracted = extractor.extract_characters(text)

        # Check constraints
        result = check_entity_constraints(extracted, constraints, verbose)
        result.test_id = test_id

        results.append(result)

        if result.passed:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"\n{status} [{test_id}] {description}")
        print(f"    Score: {result.score:.1f}/{result.max_score:.1f}")
        print(f"    Extracted: {sorted(extracted)}")

        for detail in result.details:
            print(detail)

    # Summary
    total = passed + failed
    print("\n" + "-" * 60)
    print(f"ENTITY EXTRACTION SUMMARY: {passed}/{total} passed ({100*passed/total:.1f}%)")

    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": passed / total if total > 0 else 0
    }


def test_relationship_extraction(verbose: bool = False) -> Dict[str, Any]:
    """Run relationship extraction tests."""
    print("\n" + "=" * 60)
    print("RELATIONSHIP EXTRACTION TESTS")
    print("=" * 60)

    dataset = load_evaluation_dataset("relationship")
    extractor = EntityExtractor()
    rel_extractor = RelationExtractor()

    results = []
    passed = 0
    failed = 0

    for item in dataset["items"]:
        test_id = item["id"]
        description = item.get("description", "")
        constraints = item.get("constraints", {})

        # Skip full chapter and incremental tests
        if item.get("input", {}).get("full_chapter"):
            continue
        if item.get("input", {}).get("precondition"):
            continue

        text = item.get("input", {}).get("text", "")
        if not text:
            continue

        # Run extraction
        relationships = rel_extractor.extract_cooccurrence_relations(text)

        # Check constraints
        result = check_relationship_constraints(relationships, constraints, verbose)
        result.test_id = test_id

        results.append(result)

        if result.passed:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"\n{status} [{test_id}] {description}")
        print(f"    Score: {result.score:.1f}/{result.max_score:.1f}")
        print(f"    Relationships: {len(relationships)}")

        for detail in result.details:
            print(detail)

    # Summary
    total = passed + failed
    print("\n" + "-" * 60)
    print(f"RELATIONSHIP EXTRACTION SUMMARY: {passed}/{total} passed ({100*passed/total:.1f}%)")

    return {
        "passed": passed,
        "failed": failed,
        "total": total,
        "pass_rate": passed / total if total > 0 else 0
    }


def main():
    """Run all extraction tests."""
    parser = argparse.ArgumentParser(description="Test extraction pipelines")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--dataset", choices=["entity", "relationship", "all"],
                       default="all", help="Which dataset to test")
    args = parser.parse_args()

    print("=" * 60)
    print("EXTRACTION TESTKIT RUNNER")
    print("=" * 60)

    results = {}

    if args.dataset in ["entity", "all"]:
        results["entity"] = test_entity_extraction(args.verbose)

    if args.dataset in ["relationship", "all"]:
        results["relationship"] = test_relationship_extraction(args.verbose)

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    for name, data in results.items():
        print(f"  {name.capitalize()}: {data['passed']}/{data['total']} ({100*data['pass_rate']:.1f}%)")

    total_passed = sum(r["passed"] for r in results.values())
    total_tests = sum(r["total"] for r in results.values())
    overall_rate = total_passed / total_tests if total_tests > 0 else 0

    print(f"\n  OVERALL: {total_passed}/{total_tests} ({100*overall_rate:.1f}%)")

    # Exit code
    if overall_rate >= 0.7:
        print("\n✓ Tests PASSED (≥70% threshold)")
        return 0
    else:
        print("\n✗ Tests FAILED (<70% threshold)")
        return 1


if __name__ == "__main__":
    exit(main())
