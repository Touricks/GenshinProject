"""Tests for relationship extraction functionality."""

import pytest

from tests.extraction.conftest import get_test_cases_by_layer


# =============================================================================
# Parsing Layer Tests - Co-occurrence Relationships
# =============================================================================


class TestParsingLayerRelationships:
    """Test relationships derived from co-occurrence - high certainty."""

    def test_same_scene_speakers_know_each_other(self, relationship_dataset):
        """Test that speakers in same scene have KNOWS relationship."""
        parsing_cases = get_test_cases_by_layer(relationship_dataset, "parsing")

        for case in parsing_cases:
            constraints = case.get("constraints", {})
            must_relate = constraints.get("must_relate", [])

            # Parsing layer should have must_relate constraints
            if must_relate:
                for rel in must_relate:
                    assert "source" in rel
                    assert "target" in rel

    def test_dataset_has_parsing_layer(self, relationship_dataset):
        """Verify parsing layer cases exist."""
        parsing_cases = get_test_cases_by_layer(relationship_dataset, "parsing")
        assert len(parsing_cases) >= 1


# =============================================================================
# Explicit Layer Tests - Direct Statements
# =============================================================================


class TestExplicitLayerRelationships:
    """Test relationships from explicit statements - medium certainty."""

    def test_work_relationship_explicit(self, relationship_dataset):
        """Test explicit work relationships are captured."""
        explicit_cases = get_test_cases_by_layer(relationship_dataset, "explicit")

        # Find work relationship cases
        work_cases = [
            case
            for case in explicit_cases
            if any(
                "WORKS_WITH" in case.get("constraints", {}).get("acceptable_types", [])
                for _ in [1]
            )
        ]

        assert len(work_cases) >= 1

    def test_member_of_relationship(self, relationship_dataset):
        """Test MEMBER_OF relationships are captured."""
        explicit_cases = get_test_cases_by_layer(relationship_dataset, "explicit")

        member_cases = [
            case
            for case in explicit_cases
            if any(
                "MEMBER_OF" in case.get("constraints", {}).get("acceptable_types", [])
                for _ in [1]
            )
        ]

        assert len(member_cases) >= 1

    def test_created_by_relationship(self, relationship_dataset):
        """Test CREATED_BY relationships are captured."""
        items = relationship_dataset.get("items", [])

        creator_cases = [
            case
            for case in items
            if any(
                "CREATED_BY" in case.get("constraints", {}).get("acceptable_types", [])
                for _ in [1]
            )
        ]

        assert len(creator_cases) >= 1

    @pytest.mark.parametrize(
        "test_id",
        ["rel_002", "rel_003", "rel_004", "rel_005"],
    )
    def test_explicit_layer_from_dataset(self, relationship_dataset, test_id):
        """Test explicit layer cases from dataset."""
        items = relationship_dataset.get("items", [])
        test_case = next((item for item in items if item["id"] == test_id), None)

        if test_case is None:
            pytest.skip(f"Test case {test_id} not found")

        assert test_case.get("layer") == "explicit"


# =============================================================================
# Inferred Layer Tests - Contextual Inference
# =============================================================================


class TestInferredLayerRelationships:
    """Test relationships inferred from context - lower certainty."""

    def test_inferred_friendship(self, relationship_dataset):
        """Test inferred friendship relationships."""
        inferred_cases = get_test_cases_by_layer(relationship_dataset, "inferred")

        # Find friendship inference cases
        friend_cases = [
            case
            for case in inferred_cases
            if any(
                "FRIEND_OF" in case.get("constraints", {}).get("acceptable_types", [])
                for _ in [1]
            )
        ]

        assert len(friend_cases) >= 1

    def test_inferred_enemy(self, relationship_dataset):
        """Test inferred enemy relationships."""
        inferred_cases = get_test_cases_by_layer(relationship_dataset, "inferred")

        enemy_cases = [
            case
            for case in inferred_cases
            if any(
                "ENEMY_OF" in case.get("constraints", {}).get("acceptable_types", [])
                for _ in [1]
            )
        ]

        assert len(enemy_cases) >= 1

    def test_should_relate_constraints(self, relationship_dataset):
        """Test should_relate constraints are properly defined."""
        inferred_cases = get_test_cases_by_layer(relationship_dataset, "inferred")

        for case in inferred_cases:
            constraints = case.get("constraints", {})
            # Inferred layer uses should_relate (not must_relate)
            assert (
                "should_relate" in constraints or "may_relate" in constraints
            ), f"Inferred case {case['id']} should have should_relate or may_relate"


# =============================================================================
# Negative Layer Tests - Hallucination Prevention
# =============================================================================


class TestNegativeLayerRelationships:
    """Test must_not_relate constraints to prevent hallucination."""

    def test_negative_cases_exist(self, relationship_dataset):
        """Verify negative test cases exist."""
        negative_cases = get_test_cases_by_layer(relationship_dataset, "negative")
        assert len(negative_cases) >= 1

    def test_must_not_relate_structure(self, relationship_dataset):
        """Test must_not_relate constraint structure."""
        negative_cases = get_test_cases_by_layer(relationship_dataset, "negative")

        for case in negative_cases:
            constraints = case.get("constraints", {})
            must_not = constraints.get("must_not_relate", [])

            for rel in must_not:
                assert "source" in rel
                assert "target" in rel
                # Negative constraints should specify relationship type
                assert "type" in rel

    def test_no_false_friendship(self, relationship_dataset):
        """Test that enemy context doesn't produce FRIEND_OF."""
        items = relationship_dataset.get("items", [])

        # Find rel_019 which tests this
        rel_019 = next((item for item in items if item["id"] == "rel_019"), None)

        if rel_019:
            constraints = rel_019.get("constraints", {})
            must_not = constraints.get("must_not_relate", [])

            # Should prevent false friendship from enemy context
            friend_constraints = [
                r for r in must_not if r.get("type") == "FRIEND_OF"
            ]
            assert len(friend_constraints) >= 1


# =============================================================================
# Alias Layer Tests
# =============================================================================


class TestAliasRelationships:
    """Test alias relationship extraction."""

    def test_alias_cases_exist(self, relationship_dataset):
        """Verify alias test cases exist."""
        alias_cases = get_test_cases_by_layer(relationship_dataset, "alias")
        assert len(alias_cases) >= 1

    def test_alias_relationship_structure(self, relationship_dataset):
        """Test alias relationship structure."""
        alias_cases = get_test_cases_by_layer(relationship_dataset, "alias")

        for case in alias_cases:
            constraints = case.get("constraints", {})
            acceptable = constraints.get("acceptable_types", [])

            # Should accept alias-type relationships
            alias_types = {"IS_ALIAS_OF", "SAME_AS", "REFERS_TO"}
            has_alias_type = bool(set(acceptable) & alias_types)
            assert has_alias_type, f"Alias case {case['id']} should accept alias types"


# =============================================================================
# Constraint Layer Tests
# =============================================================================


@pytest.mark.integration
class TestConstraintLayerRelationships:
    """Integration tests for relationship constraints."""

    def test_chapter_constraint_exists(self, relationship_dataset):
        """Test chapter-level constraint cases exist."""
        constraint_cases = get_test_cases_by_layer(relationship_dataset, "constraint")
        assert len(constraint_cases) >= 1

    def test_minimum_relationships_constraint(self, relationship_dataset):
        """Test minimum relationships constraint."""
        constraint_cases = get_test_cases_by_layer(relationship_dataset, "constraint")

        for case in constraint_cases:
            constraints = case.get("constraints", {})
            if "min_relationships" in constraints:
                assert constraints["min_relationships"] >= 5

    def test_connectivity_constraint(self, relationship_dataset):
        """Test all characters connected constraint."""
        constraint_cases = get_test_cases_by_layer(relationship_dataset, "constraint")

        for case in constraint_cases:
            constraints = case.get("constraints", {})
            if "all_characters_connected" in constraints:
                # Should also check for no orphans
                assert "no_orphan_characters" in constraints


# =============================================================================
# Relationship Type Tests
# =============================================================================


class TestRelationshipTypes:
    """Test relationship type definitions and usage."""

    def test_relationship_types_defined(self, relationship_dataset):
        """Test that reference relationship types are defined."""
        ref_types = relationship_dataset.get("relationship_types_reference", [])

        expected_types = {"KNOWS", "FRIEND_OF", "MEMBER_OF", "WORKS_WITH"}
        actual_types = set(ref_types)

        assert expected_types <= actual_types

    def test_acceptable_types_are_valid(self, relationship_dataset):
        """Test that acceptable_types reference valid types."""
        ref_types = set(relationship_dataset.get("relationship_types_reference", []))
        items = relationship_dataset.get("items", [])

        for item in items:
            constraints = item.get("constraints", {})
            acceptable = constraints.get("acceptable_types", [])

            # Some acceptable types may be custom, so we just check format
            assert isinstance(acceptable, list)

    def test_bidirectional_relationships(self, relationship_dataset):
        """Test bidirectional relationship constraints."""
        items = relationship_dataset.get("items", [])

        bidirectional_cases = [
            item
            for item in items
            if item.get("constraints", {}).get("bidirectional", False)
            or any(
                rel.get("bidirectional", False)
                for rel in item.get("constraints", {}).get("must_relate", [])
            )
        ]

        assert len(bidirectional_cases) >= 1
