#!/usr/bin/env python3
"""
Script to create the escalations Glue table in AWS Athena.

This script reads the SQL DDL from infrastructure/glue_tables/escalations.sql
and executes it using the Athena client to create the table in the Glue catalog.

Requirements: 6.4, 6.5
"""

import os
import sys
import time
import boto3
from pathlib import Path

# AWS Configuration
AWS_REGION = "eu-west-1"
ATHENA_DATABASE = "brand_metadata_generator_db"
S3_OUTPUT_LOCATION = "s3://brand-generator-rwrd-023-eu-west-1/athena-results/"
SQL_FILE_PATH = "infrastructure/glue_tables/escalations.sql"


def read_sql_file(file_path: str) -> str:
    """Read SQL DDL from file."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: SQL file not found at {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading SQL file: {e}")
        sys.exit(1)


def execute_athena_query(client, query: str, database: str, output_location: str) -> str:
    """
    Execute an Athena query and return the execution ID.
    
    Args:
        client: Boto3 Athena client
        query: SQL query to execute
        database: Athena database name
        output_location: S3 location for query results
        
    Returns:
        Query execution ID
    """
    try:
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': output_location}
        )
        return response['QueryExecutionId']
    except Exception as e:
        print(f"Error starting query execution: {e}")
        raise


def wait_for_query_completion(client, execution_id: str, max_wait_seconds: int = 60) -> dict:
    """
    Wait for Athena query to complete and return the final status.
    
    Args:
        client: Boto3 Athena client
        execution_id: Query execution ID
        max_wait_seconds: Maximum time to wait for completion
        
    Returns:
        Query execution details
    """
    start_time = time.time()
    
    while True:
        if time.time() - start_time > max_wait_seconds:
            raise TimeoutError(f"Query execution timed out after {max_wait_seconds} seconds")
        
        response = client.get_query_execution(QueryExecutionId=execution_id)
        status = response['QueryExecution']['Status']['State']
        
        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            return response['QueryExecution']
        
        time.sleep(2)


def create_glue_table():
    """Main function to create the escalations Glue table."""
    print("=" * 60)
    print("Creating escalations Glue Table")
    print("=" * 60)
    
    # Initialize Athena client
    print(f"\n1. Initializing Athena client (region: {AWS_REGION})...")
    athena_client = boto3.client('athena', region_name=AWS_REGION)
    
    # Read SQL DDL
    print(f"\n2. Reading SQL DDL from {SQL_FILE_PATH}...")
    sql_ddl = read_sql_file(SQL_FILE_PATH)
    print(f"   SQL DDL loaded ({len(sql_ddl)} characters)")
    
    # Execute query
    print(f"\n3. Executing CREATE TABLE query...")
    print(f"   Database: {ATHENA_DATABASE}")
    print(f"   Output location: {S3_OUTPUT_LOCATION}")
    
    try:
        execution_id = execute_athena_query(
            athena_client,
            sql_ddl,
            ATHENA_DATABASE,
            S3_OUTPUT_LOCATION
        )
        print(f"   Query execution started: {execution_id}")
    except Exception as e:
        print(f"\n❌ Failed to start query execution: {e}")
        sys.exit(1)
    
    # Wait for completion
    print(f"\n4. Waiting for query completion...")
    try:
        execution_details = wait_for_query_completion(athena_client, execution_id)
        status = execution_details['Status']['State']
        
        if status == 'SUCCEEDED':
            print(f"\n✅ Table created successfully!")
            print(f"   Table: {ATHENA_DATABASE}.escalations")
            print(f"   Location: s3://brand-generator-rwrd-023-eu-west-1/escalations/")
            print(f"   Execution ID: {execution_id}")
            return True
        else:
            reason = execution_details['Status'].get('StateChangeReason', 'Unknown error')
            print(f"\n❌ Table creation failed: {reason}")
            return False
            
    except TimeoutError as e:
        print(f"\n❌ {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error waiting for query completion: {e}")
        return False


if __name__ == "__main__":
    print("\nGenerating Glue Table: escalations")
    print(f"Region: {AWS_REGION}")
    print(f"Database: {ATHENA_DATABASE}\n")
    
    success = create_glue_table()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Glue table creation completed successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Glue table creation failed")
        print("=" * 60)
        sys.exit(1)
