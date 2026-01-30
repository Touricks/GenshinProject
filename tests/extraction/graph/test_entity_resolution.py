"""Tests for entity resolution and deduplication functionality."""

import pytest

from tests.extraction.conftest import get_test_cases_by_category


# =============================================================================
# Alias Unification Tests
# =============================================================================


class TestAliasUnification:
    """Test unification of entity aliases."""

    def test_player_character_aliases(self, resolution_dataset):
        """Test unification of player character aliases."""
        items = resolution_dataset.get("items", [])

        # Find resolve_001 - player character aliases
        player_case = next(
            (item for item in items if item["id"] == "resolve_001"), None
        )

        if player_case is None:
            pytest.skip("Player alias case not found")

        constraints = player_case.get("constraints", {})
        must_unify = constraints.get("must_unify", [])

        # All player aliases should unify
        expected_aliases = {"杜麦尼", "Traveler", "旅行者", "玩家"}
        assert set(must_unify) == expected_aliases

    def test_canonical_name_hint(self, resolution_dataset):
        """Test canonical name hints are provided."""
        items = resolution_dataset.get("items", [])

        for item in items:
            constraints = item.get("constraints", {})
            if "must_unify" in constraints and len(constraints["must_unify"]) > 1:
                # Should have a canonical hint
                assert (
                    "canonical_hint" in constraints
                    or "notes" in constraints
                )

    def test_result_entity_count(self, resolution_dataset):
        """Test result_entity_count constraints."""
        items = resolution_dataset.get("items", [])

        for item in items:
            constraints = item.get("constraints", {})
            if "must_unify" in constraints:
                # Unified entities should result in count of 1
                if "result_entity_count" in constraints:
                    assert constraints["result_entity_count"] == 1

    @pytest.mark.parametrize(
        "test_id",
        ["resolve_001", "resolve_002", "resolve_003", "resolve_004", "resolve_005"],
    )
    def test_alias_unification_from_dataset(self, resolution_dataset, test_id):
        """Test alias unification cases from dataset."""
        items = resolution_dataset.get("items", [])
        test_case = next((item for item in items if item["id"] == test_id), None)

        if test_case is None:
            pytest.skip(f"Test case {test_id} not found")

        assert test_case.get("category") == "alias_unification"


# =============================================================================
# Disambiguation Tests
# =============================================================================


class TestDisambiguation:
    """Test disambiguation of same-name entities."""

    def test_anonymous_disambiguation(self, resolution_dataset):
        """Test disambiguation of ？？？ in different contexts."""
        items = resolution_dataset.get("items", [])

        # Find disambiguation case
        disambig_cases = get_test_cases_by_category(
            resolution_dataset, "disambiguation"
        )

        assert len(disambig_cases) >= 1

        for case in disambig_cases:
            constraints = case.get("constraints", {})
            # Should have must_not_unify for different contexts
            assert "must_not_unify" in constraints

    def test_scene_context_matters(self, resolution_dataset):
        """Test that scene context is used for disambiguation."""
        items = resolution_dataset.get("items", [])

        # Find resolve_006 - ？？？ multi-context
        resolve_006 = next(
            (item for item in items if item["id"] == "resolve_006"), None
        )

        if resolve_006:
            input_data = resolve_006.get("input", {})
            mentions = input_data.get("mentions", [])

            # Each mention should have scene context
            for mention in mentions:
                if isinstance(mention, dict):
                    assert "scene" in mention


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplication:
    """Test deduplication of repeated entity mentions."""

    def test_same_character_deduplication(self, resolution_dataset):
        """Test that same character appearing multiple times is deduplicated."""
        dedup_cases = get_test_cases_by_category(resolution_dataset, "deduplication")

        assert len(dedup_cases) >= 1

        for case in dedup_cases:
            constraints = case.get("constraints", {})
            if "must_unify_all_occurrences" in constraints:
                assert constraints["must_unify_all_occurrences"] is True

    def test_organization_deduplication(self, resolution_dataset):
        """Test organization entity deduplication."""
        items = resolution_dataset.get("items", [])

        # Find resolve_008 - organization dedup
        resolve_008 = next(
            (item for item in items if item["id"] == "resolve_008"), None
        )

        if resolve_008:
            constraints = resolve_008.get("constraints", {})
            must_unify = constraints.get("must_unify", [])

            # 花羽会 and 「花羽会」 should unify
            assert "花羽会" in must_unify
            assert "「花羽会」" in must_unify

    def test_independent_characters_not_unified(self, resolution_dataset):
        """Test that independent characters are not incorrectly unified."""
        items = resolution_dataset.get("items", [])

        # Find resolve_012 - independent characters
        resolve_012 = next(
            (item for item in items if item["id"] == "resolve_012"), None
        )

        if resolve_012:
            constraints = resolve_012.get("constraints", {})
            assert constraints.get("must_not_unify_any") is True
            assert constraints.get("result_entity_count") == 5


# =============================================================================
# Cross-Reference Tests
# =============================================================================


class TestCrossReference:
    """Test cross-reference handling for shared titles."""

    def test_ancient_name_inheritance(self, resolution_dataset):
        """Test that ancient name holders are not unified."""
        cross_ref_cases = get_test_cases_by_category(
            resolution_dataset, "cross_reference"
        )

        assert len(cross_ref_cases) >= 1

        for case in cross_ref_cases:
            constraints = case.get("constraints", {})
            # Different holders should NOT be unified
            assert "must_not_unify" in constraints

    def test_should_link_via_title(self, resolution_dataset):
        """Test that title holders are linked via the title."""
        cross_ref_cases = get_test_cases_by_category(
            resolution_dataset, "cross_reference"
        )

        for case in cross_ref_cases:
            constraints = case.get("constraints", {})
            if "should_link_via" in constraints:
                # Should have a title to link through
                title = constraints["should_link_via"]
                assert title in ["祝福", "超越"]


# =============================================================================
# Location Hierarchy Tests
# =============================================================================


class TestLocationHierarchy:
    """Test location hierarchy handling."""

    def test_parent_child_locations(self, resolution_dataset):
        """Test that parent-child locations are not unified."""
        hierarchy_cases = get_test_cases_by_category(
            resolution_dataset, "location_hierarchy"
        )

        if not hierarchy_cases:
            pytest.skip("No location hierarchy cases")

        for case in hierarchy_cases:
            constraints = case.get("constraints", {})
            # Parent and child should NOT unify
            assert "must_not_unify" in constraints
            # Should establish hierarchy relationship
            assert "should_have_hierarchy" in constraints

    def test_hierarchy_structure(self, resolution_dataset):
        """Test hierarchy constraint structure."""
        hierarchy_cases = get_test_cases_by_category(
            resolution_dataset, "location_hierarchy"
        )

        for case in hierarchy_cases:
            constraints = case.get("constraints", {})
            hierarchy = constraints.get("should_have_hierarchy", {})

            if hierarchy:
                assert "parent" in hierarchy
                assert "child" in hierarchy


# =============================================================================
# Incremental Resolution Tests
# =============================================================================


class TestIncrementalResolution:
    """Test incremental entity resolution."""

    def test_link_to_existing_entities(self, resolution_dataset):
        """Test linking new mentions to existing entities."""
        incremental_cases = get_test_cases_by_category(
            resolution_dataset, "incremental"
        )

        if not incremental_cases:
            pytest.skip("No incremental cases")

        for case in incremental_cases:
            constraints = case.get("constraints", {})
            # Should link to existing, not create duplicates
            # Also accepts should_resolve_provisional for provisional entity updates
            assert (
                "must_link_to_existing" in constraints
                or "must_not_create_duplicate" in constraints
                or "should_resolve_provisional" in constraints
            )

    def test_provisional_entity_resolution(self, resolution_dataset):
        """Test resolution of provisional entities like ？？？."""
        items = resolution_dataset.get("items", [])

        # Find resolve_014 - provisional to formal name
        resolve_014 = next(
            (item for item in items if item["id"] == "resolve_014"), None
        )

        if resolve_014:
            constraints = resolve_014.get("constraints", {})
            should_resolve = constraints.get("should_resolve_provisional", {})

            assert should_resolve.get("from") == "？？？"
            assert should_resolve.get("to") == "伊涅芙"


# =============================================================================
# Constraint Layer Tests
# =============================================================================


@pytest.mark.integration
class TestResolutionConstraints:
    """Integration tests for resolution constraints."""

    def test_chapter_level_constraints(self, resolution_dataset):
        """Test chapter-level resolution constraints."""
        constraint_cases = get_test_cases_by_category(
            resolution_dataset, "constraint"
        )

        assert len(constraint_cases) >= 1

    def test_no_duplicate_constraint(self, resolution_dataset):
        """Test no duplicate entities constraint."""
        constraint_cases = get_test_cases_by_category(
            resolution_dataset, "constraint"
        )

        for case in constraint_cases:
            constraints = case.get("constraints", {})
            # Should enforce no duplicates
            has_no_dup = (
                "no_duplicate_characters" in constraints
                or "no_duplicate_organizations" in constraints
            )
            assert has_no_dup

    def test_max_anonymous_constraint(self, resolution_dataset):
        """Test maximum anonymous entities constraint."""
        constraint_cases = get_test_cases_by_category(
            resolution_dataset, "constraint"
        )

        for case in constraint_cases:
            constraints = case.get("constraints", {})
            if "max_anonymous_entities" in constraints:
                # Should limit anonymous entities
                assert constraints["max_anonymous_entities"] <= 5


# =============================================================================
# Dataset Validation Tests
# =============================================================================


class TestResolutionDataset:
    """Validate resolution dataset structure."""

    def test_dataset_structure(self, resolution_dataset):
        """Test dataset has required structure."""
        assert "version" in resolution_dataset
        assert "items" in resolution_dataset
        assert "philosophy" in resolution_dataset
        assert "test_types" in resolution_dataset

    def test_test_types_defined(self, resolution_dataset):
        """Test that test types are properly defined."""
        test_types = resolution_dataset.get("test_types", {})

        expected_types = {"must_unify", "must_not_unify", "should_unify"}
        actual_types = set(test_types.keys())

        assert expected_types <= actual_types

    def test_all_cases_have_constraints(self, resolution_dataset):
        """Test all cases have constraints defined."""
        items = resolution_dataset.get("items", [])

        for item in items:
            assert "constraints" in item, f"Case {item['id']} missing constraints"
            constraints = item["constraints"]
            # Should have at least one constraint type
            constraint_types = {
                "must_unify",
                "must_not_unify",
                "should_unify",
                "must_unify_all_occurrences",
                "must_not_unify_any",
                "must_link_to_existing",
                "no_duplicate_characters",
            }
            has_constraint = any(ct in constraints for ct in constraint_types)
            assert has_constraint or "notes" in constraints
