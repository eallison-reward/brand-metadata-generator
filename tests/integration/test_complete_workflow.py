"""Integration tests for complete brand metadata generation workflow.

This module tests the end-to-end workflow from data ingestion through
metadata generation, validation, and storage.

Note: These are simplified integration tests that verify the workflow
components work together correctly. Full end-to-end testing with AWS
services would require actual AWS infrastructure.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agents.data_transformation.tools import DataTransformationTools
from agents.evaluator import tools as evaluator_tools
from agents.metadata_production import tools as mp_tools


@pytest.fixture
def sample_brand_combos():
    """Sample combo data for a simple brand."""
    return [
        {
            "ccid": 1,
            "bankid": 1,
            "mid": "MID001",
            "narrative": "STARBUCKS #12345",
            "mccid": 5812,
            "mcc_desc": "Eating Places",
            "mcc_sector": "Food"
        },
        {
            "ccid": 2,
            "bankid": 1,
            "mid": "MID002",
            "narrative": "STARBUCKS COFFEE",
            "mccid": 5812,
            "mcc_desc": "Eating Places",
            "mcc_sector": "Food"
        },
        {
            "ccid": 3,
            "bankid": 2,
            "mid": "MID003",
            "narrative": "STARBUCKS STORE",
            "mccid": 5812,
            "mcc_desc": "Eating Places",
            "mcc_sector": "Food"
        }
    ]


@pytest.fixture
def wallet_brand_combos():
    """Sample combo data for a brand with wallet complications."""
    return [
        {
            "ccid": 10,
            "bankid": 1,
            "mid": "MID010",
            "narrative": "SHELL STATION 123",
            "mccid": 5541,
            "mcc_desc": "Service Stations",
            "mcc_sector": "Fuel"
        },
        {
            "ccid": 11,
            "bankid": 1,
            "mid": "MID011",
            "narrative": "PAYPAL *SHELL",
            "mccid": 7399,
            "mcc_desc": "Business Services",
            "mcc_sector": "Services"
        },
        {
            "ccid": 12,
            "bankid": 2,
            "mid": "MID012",
            "narrative": "SQ *SHELL FUEL",
            "mccid": 7299,
            "mcc_desc": "Miscellaneous Services",
            "mcc_sector": "Services"
        }
    ]


class TestSimpleBrandWorkflow:
    """Test workflow for a simple brand without complications."""

    def test_narrative_analysis_and_metadata_generation(self, sample_brand_combos):
        """Test analyzing narratives and generating metadata for a simple brand.
        
        This test verifies the core workflow:
        1. Analyze narrative patterns
        2. Detect payment wallets (should be none)
        3. Assess MCCID consistency
        4. Calculate confidence score
        5. Generate regex pattern
        6. Generate MCCID list
        7. Validate pattern coverage
        """
        brandid = 123
        narratives = [combo["narrative"] for combo in sample_brand_combos]
        mccids = [combo["mccid"] for combo in sample_brand_combos]
        
        # Step 1: Analyze narratives
        analysis = evaluator_tools.analyze_narratives(brandid, sample_brand_combos)
        
        assert "brandid" in analysis
        assert analysis["consistency_level"] in ["high", "medium", "low"]
        assert "STARBUCKS" in str(analysis["common_patterns"])
        
        # Step 2: Detect payment wallets
        wallet_detection = evaluator_tools.detect_payment_wallets(narratives)
        
        assert wallet_detection["wallet_detected"] is False
        assert wallet_detection["affected_percentage"] == 0.0
        
        # Step 3: Assess MCCID consistency
        mcc_table = [
            {"mccid": 5812, "sector": "Food & Beverage", "mcc_desc": "Eating Places"}
        ]
        mccid_assessment = evaluator_tools.assess_mccid_consistency(
            brandid, mccids, "Food & Beverage", mcc_table
        )
        
        assert mccid_assessment["consistent"] is True
        assert mccid_assessment["consistency_percentage"] == 1.0
        
        # Step 4: Calculate confidence score
        confidence_score = evaluator_tools.calculate_confidence_score({
            "narrative_analysis": analysis,
            "wallet_detection": wallet_detection,
            "mccid_consistency": mccid_assessment
        })
        
        assert confidence_score >= 0.7
        
        # Step 5: Generate regex pattern
        regex_pattern = mp_tools.generate_regex(brandid, narratives)
        
        assert regex_pattern  # Should have a pattern
        assert "STARBUCKS" in regex_pattern.upper()
        
        # Step 6: Generate MCCID list
        mccid_list_result = mp_tools.generate_mccid_list(brandid, mccids)
        
        assert isinstance(mccid_list_result, list)
        assert 5812 in mccid_list_result
        assert len(mccid_list_result) == 1
        
        # Step 7: Validate pattern coverage
        coverage = mp_tools.validate_pattern_coverage(
            regex_pattern,
            narratives
        )
        
        assert coverage["valid"] is True
        assert coverage["narratives_matched"] >= 0.8


class TestWalletBrandWorkflow:
    """Test workflow for a brand with payment wallet complications."""

    def test_wallet_detection_and_filtering(self, wallet_brand_combos):
        """Test wallet detection and proper filtering in metadata generation.
        
        This test verifies:
        1. Wallet detection in narratives
        2. Wallet text filtering
        3. Wallet MCCID filtering
        4. Proper metadata generation despite wallet complications
        """
        brandid = 456
        narratives = [combo["narrative"] for combo in wallet_brand_combos]
        mccids = [combo["mccid"] for combo in wallet_brand_combos]
        
        # Step 1: Detect payment wallets
        wallet_detection = evaluator_tools.detect_payment_wallets(narratives)
        
        assert wallet_detection["wallet_detected"] is True
        assert wallet_detection["affected_percentage"] > 0.5
        assert len(wallet_detection["affected_indices"]) == 2
        
        # Step 2: Filter wallet text
        wallet_indicators = wallet_detection.get("wallet_types", [])
        filtered_narratives = mp_tools.filter_wallet_text(narratives, wallet_indicators)
        
        for narrative in filtered_narratives:
            assert "PAYPAL" not in narrative.upper()
            assert "SQ *" not in narrative.upper()
        
        # Step 3: Generate regex without wallet text
        regex_pattern = mp_tools.generate_regex(brandid, filtered_narratives)
        
        assert regex_pattern  # Should have a pattern
        assert "SHELL" in regex_pattern.upper()
        
        # Step 4: Filter wallet MCCIDs
        mccid_list = mp_tools.generate_mccid_list(brandid, mccids)
        
        assert isinstance(mccid_list, list)
        assert 5541 in mccid_list  # Fuel station MCCID kept
        assert 7399 not in mccid_list  # Wallet MCCID filtered
        assert 7299 not in mccid_list  # Wallet MCCID filtered


class TestDataTransformationWorkflow:
    """Test data transformation and validation workflow."""

    @patch("agents.data_transformation.tools.AthenaClient")
    @patch("agents.data_transformation.tools.S3Client")
    def test_data_preparation_and_storage(
        self,
        mock_s3_client,
        mock_athena_client
    ):
        """Test data preparation, validation, and storage workflow.
        
        This test verifies:
        1. Brand data preparation from Athena
        2. Regex validation
        3. MCCID validation
        4. S3 storage
        """
        # Setup mocks
        mock_athena = mock_athena_client.return_value
        mock_s3 = mock_s3_client.return_value
        
        # Mock brand and combo queries
        mock_athena.execute_query.side_effect = [
            # Brand query
            [{
                "brandid": 123,
                "brandname": "Starbucks",
                "sector": "Food & Beverage"
            }],
            # Combo query
            [
                {
                    "ccid": 1,
                    "bankid": 1,
                    "mid": "MID001",
                    "narrative": "STARBUCKS #12345",
                    "mccid": 5812,
                    "mcc_desc": "Eating Places",
                    "mcc_sector": "Food"
                }
            ],
            # MCCID validation
            [{"mccid": 5812}]
        ]
        
        mock_s3.write_metadata.return_value = "metadata/brand_123.json"
        
        # Initialize tools
        dt_tools = DataTransformationTools()
        
        # Step 1: Prepare brand data
        brand_data = dt_tools.prepare_brand_data(123)
        
        assert brand_data["success"] is True
        assert brand_data["brandid"] == 123
        assert brand_data["brandname"] == "Starbucks"
        assert brand_data["combo_count"] == 1
        
        # Step 2: Validate regex
        regex_validation = dt_tools.validate_regex("^STARBUCKS.*")
        
        assert regex_validation["success"] is True
        assert regex_validation["valid"] is True
        
        # Step 3: Validate MCCIDs
        mccid_validation = dt_tools.validate_mccids([5812])
        
        assert mccid_validation["success"] is True
        assert mccid_validation["valid"] is True
        
        # Step 4: Store metadata
        metadata = {
            "brandid": 123,
            "brandname": "Starbucks",
            "regex": "^STARBUCKS.*",
            "mccid_list": [5812]
        }
        
        storage_result = dt_tools.write_to_s3(123, metadata)
        
        assert storage_result["success"] is True
        assert "s3_key" in storage_result


class TestWorkflowErrorHandling:
    """Test error handling in the workflow."""

    @patch("agents.data_transformation.tools.AthenaClient")
    def test_brand_not_found_handling(self, mock_athena_client):
        """Test handling when brand doesn't exist in database."""
        mock_athena = mock_athena_client.return_value
        mock_athena.execute_query.return_value = []
        
        dt_tools = DataTransformationTools()
        result = dt_tools.prepare_brand_data(999)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_invalid_regex_handling(self):
        """Test handling of invalid regex patterns."""
        dt_tools = DataTransformationTools()
        result = dt_tools.validate_regex("^STARBUCKS[")
        
        assert result["success"] is True
        assert result["valid"] is False
        assert "error" in result

    @patch("agents.data_transformation.tools.AthenaClient")
    def test_invalid_mccid_handling(self, mock_athena_client):
        """Test handling of invalid MCCIDs."""
        mock_athena = mock_athena_client.return_value
        mock_athena.execute_query.return_value = [{"mccid": 5812}]
        
        dt_tools = DataTransformationTools()
        result = dt_tools.validate_mccids([5812, 9999])
        
        assert result["success"] is True
        assert result["valid"] is False
        assert 9999 in result["invalid_mccids"]
