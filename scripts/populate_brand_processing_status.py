#!/usr/bin/env python3
"""Script to populate DynamoDB brand_processing_status table from Athena data."""

import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

from shared.storage.athena_client import AthenaClient
from shared.storage.dynamodb_client import DynamoDBClient


def get_brands_from_athena(athena_client: AthenaClient) -> List[int]:
    """Get list of brand IDs from brands_to_check table.
    
    Args:
        athena_client: Athena client instance
        
    Returns:
        List of brand IDs
    """
    print("📊 Querying brands_to_check table...")
    
    try:
        # Query brands_to_check table
        results = athena_client.execute_query(
            "SELECT DISTINCT brandid FROM brands_to_check ORDER BY brandid"
        )
        
        brand_ids = [row['brandid'] for row in results]
        print(f"   Found {len(brand_ids)} brands to process")
        return brand_ids
        
    except Exception as e:
        print(f"❌ Failed to query brands_to_check: {e}")
        return []


def get_brand_details(athena_client: AthenaClient, brand_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get brand details from brand table.
    
    Args:
        athena_client: Athena client instance
        brand_ids: List of brand IDs to lookup
        
    Returns:
        Dictionary mapping brand ID to brand details
    """
    print("🔍 Looking up brand details...")
    
    if not brand_ids:
        return {}
    
    try:
        # Create IN clause for brand IDs
        brand_ids_str = ",".join(str(bid) for bid in brand_ids)
        
        # Query brand table for details
        results = athena_client.execute_query(f"""
            SELECT brandid, brandname, sector
            FROM brand 
            WHERE brandid IN ({brand_ids_str})
        """)
        
        # Create lookup dictionary
        brand_details = {}
        for row in results:
            brand_details[row['brandid']] = {
                'brandname': row['brandname'],
                'sector': row['sector']
            }
        
        print(f"   Found details for {len(brand_details)} brands")
        
        # Report missing brands
        missing_brands = set(brand_ids) - set(brand_details.keys())
        if missing_brands:
            print(f"   ⚠️  Missing details for {len(missing_brands)} brands: {sorted(list(missing_brands))[:10]}...")
        
        return brand_details
        
    except Exception as e:
        print(f"❌ Failed to query brand details: {e}")
        return {}


def create_brand_records(
    brand_ids: List[int], 
    brand_details: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Create DynamoDB records for brands.
    
    Args:
        brand_ids: List of brand IDs
        brand_details: Brand details lookup
        
    Returns:
        List of DynamoDB records
    """
    print("📝 Creating DynamoDB records...")
    
    current_time = datetime.now(timezone.utc).isoformat()
    records = []
    
    for brand_id in brand_ids:
        details = brand_details.get(brand_id, {})
        
        record = {
            'brandid': brand_id,
            'brandname': details.get('brandname', f'Brand {brand_id}'),
            'sector': details.get('sector', 'Unknown'),
            'brand_status': 'unprocessed',
            'created_at': current_time,
            'updated_at': current_time,
            'workflow_execution_arn': None,
            'retry_count': 0,
            'last_error': None
        }
        
        records.append(record)
    
    print(f"   Created {len(records)} records")
    return records


def populate_dynamodb_table(
    dynamodb_client: DynamoDBClient,
    records: List[Dict[str, Any]],
    batch_size: int = 25
) -> bool:
    """Populate DynamoDB table with brand records.
    
    Args:
        dynamodb_client: DynamoDB client instance
        records: List of records to insert
        batch_size: Number of records per batch
        
    Returns:
        True if successful, False otherwise
    """
    print(f"💾 Populating DynamoDB table with {len(records)} records...")
    
    try:
        # Process in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            print(f"   Processing batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}...")
            
            dynamodb_client.batch_put_brands(batch)
        
        print("   ✅ All records inserted successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to populate DynamoDB: {e}")
        return False


def verify_population(dynamodb_client: DynamoDBClient, expected_count: int) -> bool:
    """Verify the population was successful.
    
    Args:
        dynamodb_client: DynamoDB client instance
        expected_count: Expected number of records
        
    Returns:
        True if verification passed, False otherwise
    """
    print("🔍 Verifying population...")
    
    try:
        # Get status counts
        status_counts = dynamodb_client.get_status_counts()
        total_count = sum(status_counts.values())
        
        print(f"   Total records: {total_count}")
        print(f"   Expected: {expected_count}")
        
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        
        if total_count == expected_count:
            print("   ✅ Verification passed!")
            return True
        else:
            print(f"   ❌ Count mismatch: expected {expected_count}, got {total_count}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to verify population: {e}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate DynamoDB from Athena data")
    parser.add_argument(
        "--dynamodb-table",
        default="brand_processing_status_dev",
        help="DynamoDB table name"
    )
    parser.add_argument(
        "--athena-database",
        default="brand_metadata_generator_db",
        help="Athena database name"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region"
    )
    parser.add_argument(
        "--s3-output",
        default="s3://brand-generator-rwrd-023-eu-west-1/query-results/",
        help="S3 output location for Athena queries"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting brand processing status population...")
    print(f"   DynamoDB table: {args.dynamodb_table}")
    print(f"   Athena database: {args.athena_database}")
    print(f"   Region: {args.region}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    # Initialize clients
    athena_client = AthenaClient(
        database=args.athena_database,
        region=args.region,
        output_location=args.s3_output
    )
    
    dynamodb_client = DynamoDBClient(
        table_name=args.dynamodb_table,
        region=args.region
    )
    
    # Step 1: Get brand IDs from Athena
    brand_ids = get_brands_from_athena(athena_client)
    if not brand_ids:
        print("❌ No brands found to process")
        sys.exit(1)
    
    # Step 2: Get brand details
    brand_details = get_brand_details(athena_client, brand_ids)
    
    # Step 3: Create DynamoDB records
    records = create_brand_records(brand_ids, brand_details)
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Would insert the following records:")
        for i, record in enumerate(records[:5]):  # Show first 5
            print(f"   {i+1}. Brand {record['brandid']}: {record['brandname']} ({record['sector']})")
        if len(records) > 5:
            print(f"   ... and {len(records) - 5} more records")
        print(f"\nTotal records to insert: {len(records)}")
        sys.exit(0)
    
    # Step 4: Populate DynamoDB
    success = populate_dynamodb_table(dynamodb_client, records)
    if not success:
        sys.exit(1)
    
    # Step 5: Verify population
    verify_success = verify_population(dynamodb_client, len(brand_ids))
    
    print("\n🎉 Population complete!")
    sys.exit(0 if verify_success else 1)


if __name__ == "__main__":
    main()