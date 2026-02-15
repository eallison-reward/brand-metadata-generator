"""Unit tests for Data Transformation Agent."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agents.data_transformation.tools import DataTransformationTools


@pytest.fixture
def mock_athena():
    """Mock Athena client."""
    with patch("agents.data_transformation.tools.AthenaClient") as mock:
        yield mock


@pytest.fixture
def mock_dual_storage():
    """Mock DualStorageClient."""
    with patch("agents.data_transformation.tools.DualStorageClient") as mock:
        yield mock


@pytest.fixture
def tools(mock_athena, mock_dual_storage):
    """Create DataTransformationTools instance with mocked clients."""
    return DataTransformationTools()


class TestAthenaQueries:
    """Test Athena query functionality."""

    def test_query_athena_success(self, tools, mock_athena):
        """Test successful Athena query."""
        mock_instance = mock_athena.return_value
        mock_instance.query_table.return_value = [
            {"brandid": 1, "brandname": "Test Brand", "sector": "Retail"}
        ]
        
        result = tools.query_athena("brand", where="brandid = 1")
        
        assert result["success"] is True
        assert result["row_count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["brandname"] == "Test Brand"

    def test_query_athena_error(self, tools, mock_athena):
        """Test Athena query error handling."""
        mock_instance = mock_athena.return_value
        mock_instance.query_table.side_effect = Exception("Query failed")
        
        result = tools.query_athena("brand")
        
        assert result["success"] is False
        assert "error" in result
        assert "Query failed" in result["error"]


class TestDataValidation:
    """Test data validation functionality."""

    def test_validate_regex_valid(self, tools):
        """Test validation of valid regex pattern."""
        result = tools.validate_regex("^STARBUCKS.*")
        
        assert result["success"] is True
        assert result["valid"] is True
        assert result["pattern"] == "^STARBUCKS.*"

    def test_validate_regex_invalid(self, tools):
        """Test validation of invalid regex pattern."""
        result = tools.validate_regex("^STARBUCKS[")
        
        assert result["success"] is True
        assert result["valid"] is False
        assert "error" in result

    def test_validate_mccids_all_valid(self, tools, mock_athena):
        """Test MCCID validation with all valid IDs."""
        mock_instance = mock_athena.return_value
        mock_instance.execute_query.return_value = [
            {"mccid": 5812},
            {"mccid": 5814},
            {"mccid": 5411},
        ]
        
        result = tools.validate_mccids([5812, 5814])
        
        assert result["success"] is True
        assert result["valid"] is True
        assert len(result["invalid_mccids"]) == 0

    def test_validate_mccids_some_invalid(self, tools, mock_athena):
        """Test MCCID validation with some invalid IDs."""
        mock_instance = mock_athena.return_value
        mock_instance.execute_query.return_value = [
            {"mccid": 5812},
            {"mccid": 5814},
        ]
        
        result = tools.validate_mccids([5812, 9999])
        
        assert result["success"] is True
        assert result["valid"] is False
        assert 9999 in result["invalid_mccids"]
        assert 5812 not in result["invalid_mccids"]

    def test_validate_foreign_keys_no_issues(self, tools, mock_athena):
        """Test foreign key validation with no issues."""
        mock_instance = mock_athena.return_value
        mock_instance.execute_query.return_value = [{"count": 0}]
        
        result = tools.validate_foreign_keys()
        
        assert result["success"] is True
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_foreign_keys_with_issues(self, tools, mock_athena):
        """Test foreign key validation with orphaned records."""
        mock_instance = mock_athena.return_value
        # First call returns orphaned combos, others return 0
        mock_instance.execute_query.side_effect = [
            [{"count": 5}],  # Orphaned combos
            [{"count": 0}],  # No orphaned MCCIDs
            [{"count": 0}],  # No orphaned brand_to_check
        ]
        
        result = tools.validate_foreign_keys()
        
        assert result["success"] is True
        assert result["valid"] is False
        assert len(result["issues"]) == 1
        assert "5 combos" in result["issues"][0]["issue"]


class TestS3Operations:
    """Test dual storage functionality."""

    def test_write_to_s3_success(self, tools, mock_dual_storage):
        """Test successful write using dual storage."""
        mock_instance = mock_dual_storage.return_value
        mock_instance.write_metadata.return_value = {
            "s3_key": "metadata/brand_123.json",
            "bucket": "brand-generator-rwrd-023-eu-west-1",
            "table": "generated_metadata",
            "status": "success"
        }
        
        metadata = {"regex": "^TEST.*", "mccids": [5812]}
        result = tools.write_to_s3(123, metadata)
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert "s3_key" in result
        assert "table" in result

    def test_write_to_s3_error(self, tools, mock_dual_storage):
        """Test write error handling."""
        mock_instance = mock_dual_storage.return_value
        mock_instance.write_metadata.side_effect = Exception("Dual storage error")
        
        result = tools.write_to_s3(123, {})
        
        assert result["success"] is False
        assert "error" in result

    def test_read_from_s3_found(self, tools, mock_dual_storage):
        """Test successful read."""
        mock_instance = mock_dual_storage.return_value
        mock_instance.read_metadata.return_value = {"regex": "^TEST.*"}
        
        result = tools.read_from_s3(123)
        
        assert result["success"] is True
        assert result["found"] is True
        assert "metadata" in result

    def test_read_from_s3_not_found(self, tools, mock_dual_storage):
        """Test read when file doesn't exist."""
        mock_instance = mock_dual_storage.return_value
        mock_instance.read_metadata.return_value = None
        
        result = tools.read_from_s3(123)
        
        assert result["success"] is True
        assert result["found"] is False


class TestDataPreparation:
    """Test data preparation functionality."""

    def test_prepare_brand_data_success(self, tools, mock_athena):
        """Test successful brand data preparation."""
        mock_instance = mock_athena.return_value
        mock_instance.execute_query.side_effect = [
            # Brand query
            [{"brandid": 123, "brandname": "Starbucks", "sector": "Food & Beverage"}],
            # Combo query
            [
                {"ccid": 1, "mid": "MID1", "narrative": "STARBUCKS #123", "mccid": 5812, "mcc_desc": "Eating Places", "mcc_sector": "Food"},
                {"ccid": 2, "mid": "MID2", "narrative": "STARBUCKS #456", "mccid": 5812, "mcc_desc": "Eating Places", "mcc_sector": "Food"},
            ],
        ]
        
        result = tools.prepare_brand_data(123)
        
        assert result["success"] is True
        assert result["brandid"] == 123
        assert result["brandname"] == "Starbucks"
        assert result["combo_count"] == 2
        assert len(result["unique_mccids"]) == 1
        assert 5812 in result["unique_mccids"]

    def test_prepare_brand_data_not_found(self, tools, mock_athena):
        """Test brand data preparation when brand doesn't exist."""
        mock_instance = mock_athena.return_value
        mock_instance.execute_query.return_value = []
        
        result = tools.prepare_brand_data(999)
        
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_apply_metadata_to_combos(self, tools, mock_athena):
        """Test applying metadata to combos."""
        # Mock the athena client's execute_query method
        tools.athena.execute_query = MagicMock(return_value=[
            {"ccid": 1, "mid": "MID1", "narrative": "STARBUCKS #123", "mccid": 5812, "current_brandid": 100},
            {"ccid": 2, "mid": "MID2", "narrative": "SHELL STATION", "mccid": 5541, "current_brandid": 200},
            {"ccid": 3, "mid": "MID3", "narrative": "STARBUCKS COFFEE", "mccid": 5812, "current_brandid": 100},
        ])
        
        result = tools.apply_metadata_to_combos(123, "^STARBUCKS", [5812])
        
        assert result["success"] is True
        assert result["total_matched"] == 2
        assert all(combo["mccid"] == 5812 for combo in result["matched_combos"])
        assert all("STARBUCKS" in combo["narrative"] for combo in result["matched_combos"])
