#!/usr/bin/env python3
"""Script to create DynamoDB tables for brand processing status tracking."""

import boto3
import json
import sys
from botocore.exceptions import ClientError


def create_brand_processing_status_table(
    table_name: str = "brand_processing_status_dev",
    region: str = "eu-west-1"
) -> bool:
    """Create the brand_processing_status DynamoDB table.
    
    Args:
        table_name: Name of the table to create
        region: AWS region
        
    Returns:
        True if successful, False otherwise
    """
    dynamodb = boto3.client("dynamodb", region_name=region)
    
    table_definition = {
        "TableName": table_name,
        "KeySchema": [
            {
                "AttributeName": "brandid",
                "KeyType": "HASH"
            }
        ],
        "AttributeDefinitions": [
            {
                "AttributeName": "brandid",
                "AttributeType": "N"
            },
            {
                "AttributeName": "brand_status",
                "AttributeType": "S"
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "brand-status-index",
                "KeySchema": [
                    {
                        "AttributeName": "brand_status",
                        "KeyType": "HASH"
                    }
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        ],
        "ProvisionedThroughput": {
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5
        }
    }
    
    try:
        print(f"Creating table {table_name}...")
        response = dynamodb.create_table(**table_definition)
        
        print(f"Table creation initiated. Status: {response['TableDescription']['TableStatus']}")
        
        # Wait for table to be active
        print("Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"✅ Table {table_name} created successfully!")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Failed to create table: {e}")
            return False


def verify_table_structure(table_name: str, region: str = "eu-west-1") -> bool:
    """Verify the table structure is correct.
    
    Args:
        table_name: Name of the table to verify
        region: AWS region
        
    Returns:
        True if structure is correct, False otherwise
    """
    dynamodb = boto3.client("dynamodb", region_name=region)
    
    try:
        response = dynamodb.describe_table(TableName=table_name)
        table_desc = response['Table']
        
        print(f"\n📋 Table Structure for {table_name}:")
        print(f"   Status: {table_desc['TableStatus']}")
        print(f"   Key Schema: {table_desc['KeySchema']}")
        
        # Check GSI
        gsi_found = False
        for gsi in table_desc.get('GlobalSecondaryIndexes', []):
            if gsi['IndexName'] == 'brand-status-index':
                print(f"   GSI: {gsi['IndexName']} - {gsi['IndexStatus']}")
                gsi_found = True
                break
        
        if not gsi_found:
            print("   ❌ brand-status-index GSI not found!")
            return False
        
        print("   ✅ Table structure verified!")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to verify table: {e}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create DynamoDB tables for brand processing")
    parser.add_argument(
        "--table-name", 
        default="brand_processing_status_dev",
        help="Name of the table to create"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1", 
        help="AWS region"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing table structure"
    )
    
    args = parser.parse_args()
    
    if args.verify_only:
        success = verify_table_structure(args.table_name, args.region)
    else:
        success = create_brand_processing_status_table(args.table_name, args.region)
        if success:
            verify_table_structure(args.table_name, args.region)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()