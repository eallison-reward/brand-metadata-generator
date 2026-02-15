#!/usr/bin/env python3
"""Complete setup script for DynamoDB brand processing status tracking."""

import sys
import subprocess
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status.
    
    Args:
        command: Command to run
        description: Description for logging
        
    Returns:
        True if successful, False otherwise
    """
    print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(result.stdout)
        
        print(f"✅ {description} completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete DynamoDB setup for brand processing")
    parser.add_argument(
        "--table-name",
        default="brand_processing_status_dev",
        help="DynamoDB table name"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region"
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Skip table creation (table already exists)"
    )
    parser.add_argument(
        "--skip-populate",
        action="store_true",
        help="Skip population (table already populated)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Setting up DynamoDB brand processing status tracking...")
    print(f"   Table: {args.table_name}")
    print(f"   Region: {args.region}")
    print(f"   Skip create: {args.skip_create}")
    print(f"   Skip populate: {args.skip_populate}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    success = True
    
    # Step 1: Create DynamoDB table
    if not args.skip_create:
        create_cmd = f"python {script_dir}/create_dynamodb_tables.py --table-name {args.table_name} --region {args.region}"
        if not run_command(create_cmd, "Creating DynamoDB table"):
            success = False
    else:
        print("⏭️  Skipping table creation")
    
    # Step 2: Populate table from Athena data
    if success and not args.skip_populate:
        populate_cmd = f"python {script_dir}/populate_brand_processing_status.py --dynamodb-table {args.table_name} --region {args.region}"
        if args.dry_run:
            populate_cmd += " --dry-run"
        
        if not run_command(populate_cmd, "Populating table from Athena data"):
            success = False
    elif args.skip_populate:
        print("⏭️  Skipping table population")
    
    # Step 3: Verify setup
    if success and not args.dry_run:
        verify_cmd = f"python {script_dir}/create_dynamodb_tables.py --table-name {args.table_name} --region {args.region} --verify-only"
        run_command(verify_cmd, "Verifying table structure")
    
    if success:
        print("\n🎉 DynamoDB setup completed successfully!")
        print("\nNext steps:")
        print("1. Update Lambda IAM permissions to include DynamoDB access")
        print("2. Deploy updated Lambda functions")
        print("3. Test the conversational agent")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()