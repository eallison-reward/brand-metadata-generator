"""Tools for Data Transformation Agent."""

import re
from typing import Any, Dict, List, Optional

from shared.storage.athena_client import AthenaClient
from shared.storage.dual_storage import DualStorageClient


class DataTransformationTools:
    """Tools for data ingestion, validation, and storage."""

    def __init__(
        self,
        athena_database: str = "brand_metadata_generator_db",
        s3_bucket: str = "brand-generator-rwrd-023-eu-west-1",
        region: str = "eu-west-1",
    ):
        """Initialize tools with AWS clients.
        
        Args:
            athena_database: Athena database name
            s3_bucket: S3 bucket name
            region: AWS region
        """
        self.athena = AthenaClient(database=athena_database, region=region)
        self.dual_storage = DualStorageClient(bucket=s3_bucket, database=athena_database, region=region)

    def query_athena(
        self, table_name: str, columns: str = "*", where: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute Athena query on specified table.
        
        Args:
            table_name: Name of table to query
            columns: Columns to select
            where: Optional WHERE clause
            limit: Optional LIMIT value
            
        Returns:
            Dictionary with success status and results
        """
        try:
            results = self.athena.query_table(
                table_name=table_name, columns=columns, where=where, limit=limit
            )
            return {
                "success": True,
                "table": table_name,
                "row_count": len(results),
                "results": results,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "table": table_name}

    def validate_foreign_keys(self) -> Dict[str, Any]:
        """Validate foreign key relationships between tables.
        
        Returns:
            Dictionary with validation results
        """
        issues = []
        
        try:
            # Check combo.brandid references brand.brandid
            query = """
            SELECT COUNT(*) as count
            FROM combo c
            LEFT JOIN brand b ON c.brandid = b.brandid
            WHERE b.brandid IS NULL
            """
            result = self.athena.execute_query(query)
            orphaned_combos = result[0]["count"] if result else 0
            
            if orphaned_combos > 0:
                issues.append({
                    "table": "combo",
                    "column": "brandid",
                    "issue": f"{orphaned_combos} combos reference non-existent brands"
                })
            
            # Check combo.mccid references mcc.mccid
            query = """
            SELECT COUNT(*) as count
            FROM combo c
            LEFT JOIN mcc m ON c.mccid = m.mccid
            WHERE m.mccid IS NULL
            """
            result = self.athena.execute_query(query)
            orphaned_mccids = result[0]["count"] if result else 0
            
            if orphaned_mccids > 0:
                issues.append({
                    "table": "combo",
                    "column": "mccid",
                    "issue": f"{orphaned_mccids} combos reference non-existent MCCs"
                })
            
            # Check brand_to_check.brandid references brand.brandid
            query = """
            SELECT COUNT(*) as count
            FROM brand_to_check btc
            LEFT JOIN brand b ON btc.brandid = b.brandid
            WHERE b.brandid IS NULL
            """
            result = self.athena.execute_query(query)
            orphaned_checks = result[0]["count"] if result else 0
            
            if orphaned_checks > 0:
                issues.append({
                    "table": "brand_to_check",
                    "column": "brandid",
                    "issue": f"{orphaned_checks} brand_to_check entries reference non-existent brands"
                })
            
            return {
                "success": True,
                "valid": len(issues) == 0,
                "issues": issues,
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_regex(self, pattern: str) -> Dict[str, Any]:
        """Validate regex pattern syntax.
        
        Args:
            pattern: Regex pattern to validate
            
        Returns:
            Dictionary with validation result
        """
        try:
            re.compile(pattern)
            return {
                "success": True,
                "valid": True,
                "pattern": pattern,
            }
        except re.error as e:
            return {
                "success": True,
                "valid": False,
                "pattern": pattern,
                "error": str(e),
            }

    def validate_mccids(self, mccid_list: List[int]) -> Dict[str, Any]:
        """Validate that MCCIDs exist in mcc table.
        
        Args:
            mccid_list: List of MCCID values to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Get all valid MCCIDs from database
            query = "SELECT mccid FROM mcc"
            results = self.athena.execute_query(query)
            valid_mccids = {row["mccid"] for row in results}
            
            # Check which provided MCCIDs are invalid
            invalid_mccids = [mccid for mccid in mccid_list if mccid not in valid_mccids]
            
            return {
                "success": True,
                "valid": len(invalid_mccids) == 0,
                "total_provided": len(mccid_list),
                "invalid_mccids": invalid_mccids,
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_to_s3(self, brandid: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Write brand metadata to both S3 and Athena using dual storage.
        
        Args:
            brandid: Brand ID
            metadata: Metadata dictionary
            
        Returns:
            Dictionary with write result
        """
        try:
            result = self.dual_storage.write_metadata(brandid, metadata)
            return {
                "success": True,
                "brandid": brandid,
                "s3_key": result["s3_key"],
                "bucket": result["bucket"],
                "table": result["table"],
            }
        except Exception as e:
            return {"success": False, "brandid": brandid, "error": str(e)}

    def read_from_s3(self, brandid: int) -> Dict[str, Any]:
        """Read brand metadata from S3.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Dictionary with read result
        """
        try:
            metadata = self.dual_storage.read_metadata(brandid)
            if metadata is None:
                return {
                    "success": True,
                    "found": False,
                    "brandid": brandid,
                }
            return {
                "success": True,
                "found": True,
                "brandid": brandid,
                "metadata": metadata,
            }
        except Exception as e:
            return {"success": False, "brandid": brandid, "error": str(e)}

    def prepare_brand_data(self, brandid: int) -> Dict[str, Any]:
        """Aggregate all data for a brand.
        
        Args:
            brandid: Brand ID
            
        Returns:
            Dictionary with brand data
        """
        try:
            # Get brand info
            brand_query = f"SELECT * FROM brand WHERE brandid = {brandid}"
            brand_results = self.athena.execute_query(brand_query)
            
            if not brand_results:
                return {
                    "success": False,
                    "error": f"Brand {brandid} not found",
                }
            
            brand_info = brand_results[0]
            
            # Get all combos for this brand
            combo_query = f"""
            SELECT c.ccid, c.mid, c.narrative, c.mccid, m.mcc_desc, m.sector as mcc_sector
            FROM combo c
            JOIN mcc m ON c.mccid = m.mccid
            WHERE c.brandid = {brandid}
            """
            combos = self.athena.execute_query(combo_query)
            
            # Get unique MCCIDs
            mccids = list(set(combo["mccid"] for combo in combos))
            
            # Get unique narratives
            narratives = list(set(combo["narrative"] for combo in combos))
            
            return {
                "success": True,
                "brandid": brandid,
                "brandname": brand_info["brandname"],
                "sector": brand_info["sector"],
                "combo_count": len(combos),
                "combos": combos,
                "unique_mccids": mccids,
                "unique_narratives": narratives,
            }
            
        except Exception as e:
            return {"success": False, "brandid": brandid, "error": str(e)}

    def apply_metadata_to_combos(
        self, brandid: int, regex_pattern: str, mccid_list: List[int]
    ) -> Dict[str, Any]:
        """Apply metadata to combos and return matches.
        
        Args:
            brandid: Brand ID
            regex_pattern: Regex pattern for narrative matching
            mccid_list: List of valid MCCIDs
            
        Returns:
            Dictionary with matched combos
        """
        try:
            # Compile regex
            regex = re.compile(regex_pattern, re.IGNORECASE)
            
            # Get all combos (not just for this brand - we need to find matches across all combos)
            combo_query = """
            SELECT c.ccid, c.mid, c.narrative, c.mccid, c.brandid as current_brandid
            FROM combo c
            """
            all_combos = self.athena.execute_query(combo_query)
            
            # Filter combos that match both regex and MCCID
            matched_combos = []
            for combo in all_combos:
                narrative = combo["narrative"]
                mccid = combo["mccid"]
                
                # Check if narrative matches regex AND mccid is in list
                if regex.search(narrative) and mccid in mccid_list:
                    matched_combos.append({
                        "ccid": combo["ccid"],
                        "mid": combo["mid"],
                        "narrative": combo["narrative"],
                        "mccid": combo["mccid"],
                        "current_brandid": combo["current_brandid"],
                        "matched_brandid": brandid,
                    })
            
            return {
                "success": True,
                "brandid": brandid,
                "regex_pattern": regex_pattern,
                "mccid_list": mccid_list,
                "total_matched": len(matched_combos),
                "matched_combos": matched_combos,
            }
            
        except Exception as e:
            return {"success": False, "brandid": brandid, "error": str(e)}
