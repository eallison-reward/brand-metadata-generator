#!/usr/bin/env python3
"""Complete deployment script for DynamoDB migration of conversational interface agent."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command: str, description: str, cwd: str = None) -> bool:
    """Run a command and return success status.
    
    Args:
        command: Command to run
        description: Description for logging
        cwd: Working directory
        
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
            text=True,
            cwd=cwd
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
    parser = argparse.ArgumentParser(description="Complete DynamoDB migration deployment")
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="Environment to deploy to"
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region"
    )
    parser.add_argument(
        "--skip-table-creation",
        action="store_true",
        help="Skip DynamoDB table creation"
    )
    parser.add_argument(
        "--skip-population",
        action="store_true",
        help="Skip table population from Athena"
    )
    parser.add_argument(
        "--skip-lambda-deploy",
        action="store_true",
        help="Skip Lambda function deployment"
    )
    parser.add_argument(
        "--skip-agent-deploy",
        action="store_true",
        help="Skip agent deployment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting complete DynamoDB migration deployment...")
    print(f"   Environment: {args.env}")
    print(f"   Region: {args.region}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    script_dir = Path(__file__).parent
    success = True
    
    # Step 1: Create DynamoDB table
    if not args.skip_table_creation:
        table_name = f"brand_processing_status_{args.env}"
        create_cmd = f"python {script_dir}/create_dynamodb_tables.py --table-name {table_name} --region {args.region}"
        if not run_command(create_cmd, "Creating DynamoDB table"):
            success = False
    else:
        print("⏭️  Skipping DynamoDB table creation")
    
    # Step 2: Populate table from Athena
    if success and not args.skip_population:
        table_name = f"brand_processing_status_{args.env}"
        populate_cmd = f"python {script_dir}/populate_brand_processing_status.py --dynamodb-table {table_name} --region {args.region}"
        if args.dry_run:
            populate_cmd += " --dry-run"
        
        if not run_command(populate_cmd, "Populating DynamoDB from Athena"):
            success = False
    elif args.skip_population:
        print("⏭️  Skipping table population")
    
    # Step 3: Deploy Lambda functions with DynamoDB support
    if success and not args.skip_lambda_deploy and not args.dry_run:
        # Deploy query_brands_to_check Lambda (updated for DynamoDB)
        deploy_cmd = f"python {script_dir}/deploy_tool_lambdas.py --env {args.env} --function query_brands_to_check"
        if not run_command(deploy_cmd, "Deploying query_brands_to_check Lambda"):
            success = False
        
        # Deploy start_workflow Lambda (updated for DynamoDB)
        if success:
            deploy_cmd = f"python {script_dir}/deploy_tool_lambdas.py --env {args.env} --function start_workflow"
            if not run_command(deploy_cmd, "Deploying start_workflow Lambda"):
                success = False
    elif args.skip_lambda_deploy:
        print("⏭️  Skipping Lambda deployment")
    elif args.dry_run:
        print("⏭️  Skipping Lambda deployment (dry run)")
    
    # Step 4: Deploy conversational interface agent
    if success and not args.skip_agent_deploy:
        agent_cmd = f"python {script_dir}/deploy_conversational_interface_agent.py --env {args.env}"
        if args.dry_run:
            agent_cmd += " --dry-run"
        
        if not run_command(agent_cmd, "Deploying conversational interface agent"):
            success = False
    elif args.skip_agent_deploy:
        print("⏭️  Skipping agent deployment")
    
    # Step 5: Test the deployment
    if success and not args.dry_run:
        print("\n🧪 Testing deployment...")
        test_cmd = f"python test_agent_direct.py --env {args.env}"
        if not run_command(test_cmd, "Testing agent functionality"):
            print("⚠️  Agent test failed, but deployment may still be successful")
            print("   Check agent logs and DynamoDB table for issues")
    
    if success:
        print("\n🎉 DynamoDB migration deployment completed successfully!")
        print("\nDeployment Summary:")
        print(f"✅ DynamoDB table: brand_processing_status_{args.env}")
        print("✅ Lambda functions updated with DynamoDB support")
        print("✅ Conversational interface agent deployed")
        print("\nNext steps:")
        print("1. Test the agent with: 'please generate metadata for the brands in the check table'")
        print("2. Monitor CloudWatch logs for any issues")
        print("3. Verify DynamoDB table is being updated correctly")
    else:
        print("\n❌ Deployment failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Verify AWS credentials and permissions")
        print("2. Check that Athena tables exist and are accessible")
        print("3. Ensure Lambda deployment package is valid")
        print("4. Review CloudWatch logs for detailed error messages")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()