#!/usr/bin/env python3
"""Script to remove inconsistent test records from DynamoDB brand_processing_status table."""

import sys
from typing import List

from shared.storage.dynamodb_client import DynamoDBClient


def remove_test_records(
    dynamodb_client: DynamoDBClient,
    test_brandids: List[int],
    dry_run: bool = False
) -> bool:
    """Remove test records from DynamoDB table.
    
    Args:
        dynamodb_client: DynamoDB client instance
        test_brandids: List of test brand IDs to remove
        dry_run: If True, show what would be done without making changes
        
    Returns:
        True if successful, False otherwise
    """
    print(f"🧹 {'[DRY RUN] ' if dry_run else ''}Removing {len(test_brandids)} test records...")
    
    try:
        for brandid in test_brandids:
            # Check if record exists first
            existing_record = dynamodb_client.get_brand_by_id(brandid)
            
            if existing_record:
                print(f"   Found test record: Brand {brandid} - {existing_record.get('brandname', 'Unknown')}")
                
                if not dry_run:
                    # Delete the record
                    dynamodb_client.table.delete_item(Key={"brandid": brandid})
                    print(f"   ✅ Deleted brand {brandid}")
                else:
                    print(f"   [DRY RUN] Would delete brand {brandid}")
            else:
                print(f"   ⚠️  Brand {brandid} not found (already removed?)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to remove test records: {e}")
        return False


def verify_cleanup(
    dynamodb_client: DynamoDBClient,
    test_brandids: List[int]
) -> bool:
    """Verify that test records have been removed.
    
    Args:
        dynamodb_client: DynamoDB client instance
        test_brandids: List of test brand IDs that should be removed
        
    Returns:
        True if all test records are gone, False otherwise
    """
    print("🔍 Verifying cleanup...")
    
    try:
        remaining_test_records = []
        
        for brandid in test_brandids:
            record = dynamodb_client.get_brand_by_id(brandid)
            if record:
                remaining_test_records.append(brandid)
        
        if remaining_test_records:
            print(f"   ❌ {len(remaining_test_records)} test records still exist: {remaining_test_records}")
            return False
        else:
            print("   ✅ All test records successfully removed!")
            return True
            
    except Exception as e:
        print(f"❌ Failed to verify cleanup: {e}")
        return False


def show_final_status(dynamodb_client: DynamoDBClient) -> None:
    """Show final table status after cleanup.
    
    Args:
        dynamodb_client: DynamoDB client instance
    """
    print("📊 Final table status:")
    
    try:
        # Get status counts
        status_counts = dynamodb_client.get_status_counts()
        total_count = sum(status_counts.values())
        
        print(f"   Total records: {total_count}")
        
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
            
    except Exception as e:
        print(f"❌ Failed to get final status: {e}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove inconsistent test records from DynamoDB")
    parser.add_argument(
        "--dynamodb-table",
        default="brand_processing_status_dev",
        help="DynamoDB table name"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region"
    )
    parser.add_argument(
        "--test-brandids",
        nargs="+",
        type=int,
        default=[12345, 11111, 67890],
        help="Test brand IDs to remove (default: 12345 11111 67890)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting test record cleanup...")
    print(f"   DynamoDB table: {args.dynamodb_table}")
    print(f"   Region: {args.region}")
    print(f"   Test brand IDs: {args.test_brandids}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    # Initialize DynamoDB client
    dynamodb_client = DynamoDBClient(
        table_name=args.dynamodb_table,
        region=args.region
    )
    
    # Show current status
    print("📊 Current table status:")
    show_final_status(dynamodb_client)
    print()
    
    # Remove test records
    success = remove_test_records(
        dynamodb_client, 
        args.test_brandids, 
        dry_run=args.dry_run
    )
    
    if not success:
        sys.exit(1)
    
    if not args.dry_run:
        # Verify cleanup
        verify_success = verify_cleanup(dynamodb_client, args.test_brandids)
        
        # Show final status
        print()
        show_final_status(dynamodb_client)
        
        print("\n🎉 Cleanup complete!")
        sys.exit(0 if verify_success else 1)
    else:
        print("\n🔍 DRY RUN complete - no changes made")
        sys.exit(0)


if __name__ == "__main__":
    main()