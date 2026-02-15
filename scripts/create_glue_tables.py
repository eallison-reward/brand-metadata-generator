#!/usr/bin/env python3
"""Create Glue tables for conversational interface agent.

This script creates the four Glue tables required by the conversational
interface agent:
- generated_metadata
- feedback_history
- workflow_executions
- escalations
"""

import boto3
import sys

AWS_REGION = "eu-west-1"
DATABASE_NAME = "brand_metadata_generator_db"
S3_BUCKET = "brand-generator-rwrd-023-eu-west-1"

# Table definitions
TABLES = {
    "generated_metadata": {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "brandid", "Type": "int"},
                {"Name": "brandname", "Type": "string"},
                {"Name": "regex", "Type": "string"},
                {"Name": "mccids", "Type": "array<int>"},
                {"Name": "confidence_score", "Type": "double"},
                {"Name": "version", "Type": "int"},
                {"Name": "generated_at", "Type": "timestamp"},
                {"Name": "evaluator_issues", "Type": "array<string>"},
                {"Name": "coverage_narratives_matched", "Type": "double"},
                {"Name": "coverage_false_positives", "Type": "double"},
            ],
            "Location": f"s3://{S3_BUCKET}/metadata/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                "Parameters": {"serialization.format": "1"},
            },
        },
        "TableType": "EXTERNAL_TABLE",
    },
    "feedback_history": {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "feedback_id", "Type": "string"},
                {"Name": "brandid", "Type": "int"},
                {"Name": "metadata_version", "Type": "int"},
                {"Name": "feedback_text", "Type": "string"},
                {"Name": "category", "Type": "string"},
                {"Name": "issues_identified", "Type": "array<string>"},
                {"Name": "misclassified_combos", "Type": "array<int>"},
                {"Name": "submitted_at", "Type": "timestamp"},
                {"Name": "submitted_by", "Type": "string"},
            ],
            "Location": f"s3://{S3_BUCKET}/feedback/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                "Parameters": {"serialization.format": "1"},
            },
        },
        "TableType": "EXTERNAL_TABLE",
    },
    "workflow_executions": {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "execution_arn", "Type": "string"},
                {"Name": "brandid", "Type": "int"},
                {"Name": "status", "Type": "string"},
                {"Name": "start_time", "Type": "timestamp"},
                {"Name": "stop_time", "Type": "timestamp"},
                {"Name": "duration_seconds", "Type": "int"},
                {"Name": "error_message", "Type": "string"},
                {"Name": "input_data", "Type": "string"},
                {"Name": "output_data", "Type": "string"},
            ],
            "Location": f"s3://{S3_BUCKET}/workflow-executions/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                "Parameters": {"serialization.format": "1"},
            },
        },
        "TableType": "EXTERNAL_TABLE",
    },
    "escalations": {
        "StorageDescriptor": {
            "Columns": [
                {"Name": "escalation_id", "Type": "string"},
                {"Name": "brandid", "Type": "int"},
                {"Name": "brandname", "Type": "string"},
                {"Name": "reason", "Type": "string"},
                {"Name": "confidence_score", "Type": "double"},
                {"Name": "escalated_at", "Type": "timestamp"},
                {"Name": "resolved_at", "Type": "timestamp"},
                {"Name": "resolved_by", "Type": "string"},
                {"Name": "resolution_notes", "Type": "string"},
                {"Name": "status", "Type": "string"},
            ],
            "Location": f"s3://{S3_BUCKET}/escalations/",
            "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
            "SerdeInfo": {
                "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                "Parameters": {"serialization.format": "1"},
            },
        },
        "TableType": "EXTERNAL_TABLE",
    },
}


def create_table(glue_client, table_name, table_definition):
    """Create a Glue table.
    
    Args:
        glue_client: Boto3 Glue client
        table_name: Name of the table
        table_definition: Table definition dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if table already exists
        try:
            glue_client.get_table(DatabaseName=DATABASE_NAME, Name=table_name)
            print(f"   ℹ️  Table '{table_name}' already exists, updating...")
            
            # Update existing table
            glue_client.update_table(
                DatabaseName=DATABASE_NAME,
                TableInput={
                    "Name": table_name,
                    **table_definition,
                },
            )
            print(f"   ✅ Table '{table_name}' updated successfully")
            return True
            
        except glue_client.exceptions.EntityNotFoundException:
            # Create new table
            print(f"   Creating table '{table_name}'...")
            glue_client.create_table(
                DatabaseName=DATABASE_NAME,
                TableInput={
                    "Name": table_name,
                    **table_definition,
                },
            )
            print(f"   ✅ Table '{table_name}' created successfully")
            return True
            
    except Exception as e:
        print(f"   ❌ Failed to create/update table '{table_name}': {str(e)}")
        return False


def main():
    """Main entry point."""
    print(f"\n{'='*70}")
    print(f"Creating Glue Tables for Conversational Interface Agent")
    print(f"{'='*70}")
    print(f"Database: {DATABASE_NAME}")
    print(f"Region: {AWS_REGION}")
    print(f"S3 Bucket: {S3_BUCKET}")
    print()
    
    # Initialize Glue client
    glue_client = boto3.client("glue", region_name=AWS_REGION)
    
    # Verify database exists
    try:
        glue_client.get_database(Name=DATABASE_NAME)
        print(f"✅ Database '{DATABASE_NAME}' exists\n")
    except glue_client.exceptions.EntityNotFoundException:
        print(f"❌ Database '{DATABASE_NAME}' not found")
        print(f"   Please create the database first")
        sys.exit(1)
    
    # Create each table
    success_count = 0
    for table_name, table_definition in TABLES.items():
        if create_table(glue_client, table_name, table_definition):
            success_count += 1
        print()
    
    # Summary
    print(f"{'='*70}")
    if success_count == len(TABLES):
        print(f"✅ Successfully created/updated all {len(TABLES)} tables")
        print(f"{'='*70}\n")
        
        # List all tables
        print("Verifying tables...")
        response = glue_client.get_tables(DatabaseName=DATABASE_NAME)
        table_names = [t["Name"] for t in response["TableList"]]
        print(f"\nTables in {DATABASE_NAME}:")
        for name in sorted(table_names):
            print(f"  - {name}")
        print()
        
        sys.exit(0)
    else:
        print(f"⚠️  Created/updated {success_count}/{len(TABLES)} tables")
        print(f"{'='*70}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
