"""Property-based tests for Data Transformation Agent.

**Validates: Requirements 1.6**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch, MagicMock

from agents.data_transformation.tools import DataTransformationTools


# Strategy for generating brand IDs
brand_ids = st.integers(min_value=1, max_value=10000)

# Strategy for generating MCCID lists
mccid_lists = st.lists(
    st.integers(min_value=1000, max_value=9999),
    min_size=1,
    max_size=10,
    unique=True
)


@pytest.mark.property
class TestForeignKeyIntegrity:
    """Property 1: Foreign Key Referential Integrity
    
    Property: When validating foreign keys, the system must correctly identify
    all orphaned records where foreign key references don't exist in parent tables.
    
    Validates: Requirements 1.6
    """

    @given(
        orphaned_combos=st.integers(min_value=0, max_value=100),
        orphaned_mccids=st.integers(min_value=0, max_value=100),
        orphaned_checks=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_foreign_key_validation_identifies_all_orphans(
        self, orphaned_combos, orphaned_mccids, orphaned_checks
    ):
        """Property: Foreign key validation correctly counts orphaned records.
        
        For any number of orphaned records in each table, the validation
        should correctly identify and report them.
        """
        with patch("agents.data_transformation.tools.AthenaClient") as mock_athena_class:
            mock_athena = MagicMock()
            mock_athena_class.return_value = mock_athena
            
            # Mock query results for orphaned records
            mock_athena.execute_query.side_effect = [
                [{"count": orphaned_combos}],   # combo.brandid orphans
                [{"count": orphaned_mccids}],   # combo.mccid orphans
                [{"count": orphaned_checks}],   # brand_to_check.brandid orphans
            ]
            
            tools = DataTransformationTools()
            result = tools.validate_foreign_keys()
            
            # Property: Validation succeeds
            assert result["success"] is True
            
            # Property: Valid only if no orphans exist
            expected_valid = (orphaned_combos == 0 and orphaned_mccids == 0 and orphaned_checks == 0)
            assert result["valid"] == expected_valid
            
            # Property: Number of issues equals number of non-zero orphan counts
            expected_issue_count = sum([
                1 if orphaned_combos > 0 else 0,
                1 if orphaned_mccids > 0 else 0,
                1 if orphaned_checks > 0 else 0,
            ])
            assert len(result["issues"]) == expected_issue_count
            
            # Property: Each issue mentions the correct count
            if orphaned_combos > 0:
                assert any(str(orphaned_combos) in issue["issue"] for issue in result["issues"])
            if orphaned_mccids > 0:
                assert any(str(orphaned_mccids) in issue["issue"] for issue in result["issues"])
            if orphaned_checks > 0:
                assert any(str(orphaned_checks) in issue["issue"] for issue in result["issues"])


@pytest.mark.property
class TestRegexValidation:
    """Property tests for regex validation."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_regex_validation_always_returns_success(self, pattern):
        """Property: Regex validation always returns success status.
        
        Even if the regex is invalid, the validation should succeed
        (it's the regex that's invalid, not the validation process).
        """
        tools = DataTransformationTools()
        result = tools.validate_regex(pattern)
        
        # Property: Validation process always succeeds
        assert result["success"] is True
        
        # Property: Result includes the pattern
        assert result["pattern"] == pattern
        
        # Property: Result has valid field
        assert "valid" in result


@pytest.mark.property
class TestMCCIDValidation:
    """Property tests for MCCID validation."""

    @given(
        provided_mccids=mccid_lists,
        valid_mccids=mccid_lists,
    )
    @settings(max_examples=100)
    def test_mccid_validation_correctly_identifies_invalid(
        self, provided_mccids, valid_mccids
    ):
        """Property: MCCID validation correctly identifies which MCCIDs are invalid.
        
        For any set of provided MCCIDs and valid MCCIDs, the validation
        should correctly identify which provided MCCIDs are not in the valid set.
        """
        with patch("agents.data_transformation.tools.AthenaClient") as mock_athena_class:
            mock_athena = MagicMock()
            mock_athena_class.return_value = mock_athena
            
            # Mock database response with valid MCCIDs
            mock_athena.execute_query.return_value = [
                {"mccid": mccid} for mccid in valid_mccids
            ]
            
            tools = DataTransformationTools()
            result = tools.validate_mccids(provided_mccids)
            
            # Property: Validation succeeds
            assert result["success"] is True
            
            # Property: Invalid MCCIDs are exactly those not in valid set
            expected_invalid = set(provided_mccids) - set(valid_mccids)
            assert set(result["invalid_mccids"]) == expected_invalid
            
            # Property: Valid only if all provided MCCIDs are in valid set
            expected_valid = len(expected_invalid) == 0
            assert result["valid"] == expected_valid
            
            # Property: Total provided count is correct
            assert result["total_provided"] == len(provided_mccids)


@pytest.mark.property
class TestMetadataApplication:
    """Property tests for applying metadata to combos."""

    @given(
        brandid=brand_ids,
        mccid_filter=st.integers(min_value=5000, max_value=6000),
    )
    @settings(max_examples=50)
    def test_metadata_application_only_matches_correct_mccids(
        self, brandid, mccid_filter
    ):
        """Property: Metadata application only matches combos with specified MCCIDs.
        
        When applying metadata with a specific MCCID list, only combos
        with those MCCIDs should be matched.
        """
        with patch("agents.data_transformation.tools.AthenaClient") as mock_athena_class:
            mock_athena = MagicMock()
            mock_athena_class.return_value = mock_athena
            
            # Create test combos with various MCCIDs
            # Note: current_brandid is the key name returned by the query
            test_combos = [
                {"ccid": 1, "mid": "M1", "narrative": "TEST BRAND 1", "mccid": mccid_filter, "current_brandid": 100},
                {"ccid": 2, "mid": "M2", "narrative": "TEST BRAND 2", "mccid": mccid_filter + 1, "current_brandid": 100},
                {"ccid": 3, "mid": "M3", "narrative": "TEST BRAND 3", "mccid": mccid_filter, "current_brandid": 100},
                {"ccid": 4, "mid": "M4", "narrative": "OTHER BRAND", "mccid": mccid_filter, "current_brandid": 200},
            ]
            
            mock_athena.execute_query.return_value = test_combos
            
            tools = DataTransformationTools()
            result = tools.apply_metadata_to_combos(
                brandid=brandid,
                regex_pattern="TEST BRAND",
                mccid_list=[mccid_filter]
            )
            
            # Property: Application succeeds
            assert result["success"] is True
            
            # Property: All matched combos have the specified MCCID
            for combo in result["matched_combos"]:
                assert combo["mccid"] == mccid_filter
            
            # Property: All matched combos match the regex
            for combo in result["matched_combos"]:
                assert "TEST BRAND" in combo["narrative"]
            
            # Property: Expected match count is 2 (combos 1 and 3)
            assert result["total_matched"] == 2


@pytest.mark.property
class TestDataPreparation:
    """Property tests for data preparation."""

    @given(
        brandid=brand_ids,
        combo_count=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_prepare_brand_data_combo_count_matches(self, brandid, combo_count):
        """Property: Prepared brand data combo count matches actual combos.
        
        The combo_count field should always equal the length of the combos list.
        """
        with patch("agents.data_transformation.tools.AthenaClient") as mock_athena_class:
            mock_athena = MagicMock()
            mock_athena_class.return_value = mock_athena
            
            # Mock brand data
            mock_athena.execute_query.side_effect = [
                [{"brandid": brandid, "brandname": "Test", "sector": "Retail"}],
                # Generate combo_count combos
                [
                    {
                        "ccid": i,
                        "mid": f"MID{i}",
                        "narrative": f"NARRATIVE {i}",
                        "mccid": 5812,
                        "mcc_desc": "Eating Places",
                        "mcc_sector": "Food"
                    }
                    for i in range(combo_count)
                ],
            ]
            
            tools = DataTransformationTools()
            result = tools.prepare_brand_data(brandid)
            
            # Property: Preparation succeeds
            assert result["success"] is True
            
            # Property: Combo count matches actual number of combos
            assert result["combo_count"] == len(result["combos"])
            assert result["combo_count"] == combo_count
            
            # Property: Brand ID is preserved
            assert result["brandid"] == brandid
