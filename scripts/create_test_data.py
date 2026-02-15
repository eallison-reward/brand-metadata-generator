#!/usr/bin/env python3
"""Create test data for the conversational interface agent."""

import boto3
import json
from datetime import datetime

AWS_REGION = "eu-west-1"
S3_BUCKET = "brand-generator-rwrd-023-eu-west-1"
DATABASE_NAME = "brand_metadata_generator_db"

def create_test_brand_data():
    """Create test brand data in S3."""
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    
    # Test brand data
    test_brands = [
        {"brandid": 12345, "brandname": "Starbucks", "sector": "Food & Beverage"},
        {"brandid": 67890, "brandname": "Nike", "sector": "Retail"},
        {"brandid": 11111, "brandname": "Apple", "sector": "Technology"},
        {"brandid": 22222, "brandname": "McDonald's", "sector": "Food & Beverage"},
        {"brandid": 33333, "brandname": "Amazon", "sector": "Retail"},
    ]
    
    # Create CSV content for brand table
    brand_csv = "brandid,brandname,sector\n"
    for brand in test_brands:
        brand_csv += f"{brand['brandid']},{brand['brandname']},{brand['sector']}\n"
    
    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key="test-data/brands/test_brands.csv",
        Body=brand_csv.encode('utf-8')
    )
    
    # Create brands_to_check data (subset of brands)
    brands_to_check_csv = "brandid\n"
    for brand in test_brands[:3]:  # Only first 3 brands need processing
        brands_to_check_csv += f"{brand['brandid']}\n"
    
    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key="test-data/brands_to_check/test_brands_to_check.csv",
        Body=brands_to_check_csv.encode('utf-8')
    )
    
    print("✅ Test data uploaded to S3")
    return test_brands

def create_glue_tables():
    """Create Glue tables for brand and brands_to_check."""
    glue_client = boto3.client('glue', region_name=AWS_REGION)
    
    # Brand table definition
    brand_table = {
        "Name": "brand",
        "StorageDescriptor": {
            "Columns": [
                {"Name": "brandid", "Type": "int"},
                {"Name": "brandname", "Type": "string"},
                {"Name": "sector", "Type": "string"},
            ],
            "Location": f"s3://{S3_BUCKET}/test-data/brands/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                "Parameters": {
                    "field.delim": ",",
                    "skip.header.line.count": "1"
                },
            },
        },
        "TableType": "EXTERNAL_TABLE",
    }
    
    # brands_to_check table definition
    brands_to_check_table = {
        "Name": "brands_to_check",
        "StorageDescriptor": {
            "Columns": [
                {"Name": "brandid", "Type": "int"},
            ],
            "Location": f"s3://{S3_BUCKET}/test-data/brands_to_check/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                "Parameters": {
                    "field.delim": ",",
                    "skip.header.line.count": "1"
                },
            },
        },
        "TableType": "EXTERNAL_TABLE",
    }
    
    # Create/update tables
    for table_def in [brand_table, brands_to_check_table]:
        table_name = table_def["Name"]
        try:
            # Try to update existing table
            try:
                glue_client.get_table(DatabaseName=DATABASE_NAME, Name=table_name)
                glue_client.update_table(
                    DatabaseName=DATABASE_NAME,
                    TableInput=table_def
                )
                print(f"✅ Updated table: {table_name}")
            except glue_client.exceptions.EntityNotFoundException:
                # Create new table
                glue_client.create_table(
                    DatabaseName=DATABASE_NAME,
                    TableInput=table_def
                )
                print(f"✅ Created table: {table_name}")
                
        except Exception as e:
            print(f"❌ Failed to create/update table {table_name}: {e}")

def main():
    """Main function."""
    print("🚀 Creating test data for conversational interface agent...")
    
    # Create test data in S3
    test_brands = create_test_brand_data()
    
    # Create Glue tables
    create_glue_tables()
    
    print("\n📋 Test data created:")
    print("   - 5 test brands in brand table")
    print("   - 3 brands in brands_to_check table")
    print("   - Glue tables created/updated")
    
    print("\n🔍 Test brands:")
    for brand in test_brands:
        status = "needs processing" if brand['brandid'] in [12345, 67890, 11111] else "not in queue"
        print(f"   - {brand['brandid']}: {brand['brandname']} ({brand['sector']}) - {status}")

if __name__ == "__main__":
    main()