#!/usr/bin/env python3
"""Verify deployment of Brand Metadata Generator infrastructure and agents.

This script verifies that all required components are deployed and configured correctly.

Usage:
    python scripts/verify_deployment.py --env dev
    python scripts/verify_deployment.py --env prod --verbose
"""

import argparse
import sys
import boto3
from typing import Dict, List, Tuple


# Configuration
AWS_REGION = "eu-west-1"
S3_BUCKET = "brand-generator-rwrd-023-eu-west-1"
ATHENA_DATABASE = "brand_metadata_generator_db"

REQUIRED_AGENTS = [
    "orchestrator",
    "data_transformation",
    "evaluator",
    "metadata_production",
    "commercial_assessment",
    "confirmation",
    "tiebreaker",
    "feedback_processing",
    "learning_analytics",
]

REQUIRED_ATHENA_TABLES = [
    "brand",
    "brand_to_check",
    "combo",
    "mcc",
]


class DeploymentVerifier:
    """Verify deployment of infrastructure and agents."""
    
    def __init__(self, env: str, verbose: bool = False):
        """Initialize verifier.
        
        Args:
            env: Environment name
            verbose: Enable verbose output
        """
        self.env = env
        self.verbose = verbose
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.athena_client = boto3.client('athena', region_name=AWS_REGION)
        self.glue_client = boto3.client('glue', region_name=AWS_REGION)
        self.dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        self.sfn_client = boto3.client('stepfunctions', region_name=AWS_REGION)
        self.lambda_client = boto3.client('lambda', region_name=AWS_REGION)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
        self.iam_client = boto3.client('iam', region_name=AWS_REGION)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        
        # Verification results
        self.results = {
            "s3": [],
            "athena": [],
            "dynamodb": [],
            "step_functions": [],
            "lambda": [],
            "agents": [],
            "iam": [],
            "cloudwatch": [],
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message."""
        if level == "INFO" and not self.verbose:
            return
        
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
        }.get(level, "")
        
        print(f"{prefix} {message}")
    
    def verify_s3(self) -> Tuple[int, int]:
        """Verify S3 bucket."""
        print("\n📦 Verifying S3 Bucket...")
        passed = 0
        failed = 0
        
        try:
            # Check bucket exists
            self.s3_client.head_bucket(Bucket=S3_BUCKET)
            self.log(f"Bucket {S3_BUCKET} exists", "SUCCESS")
            passed += 1
            
            # Check bucket region
            response = self.s3_client.get_bucket_location(Bucket=S3_BUCKET)
            location = response['LocationConstraint']
            if location == AWS_REGION:
                self.log(f"Bucket region is {AWS_REGION}", "SUCCESS")
                passed += 1
            else:
                self.log(f"Bucket region is {location}, expected {AWS_REGION}", "ERROR")
                failed += 1
            
            # Check required folders
            required_folders = [
                "input/brands/",
                "input/combos/",
                "input/mcc/",
                "metadata/",
                "feedback/",
                "query-results/",
            ]
            
            for folder in required_folders:
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=S3_BUCKET,
                        Prefix=folder,
                        MaxKeys=1
                    )
                    self.log(f"Folder {folder} accessible", "INFO")
                except Exception as e:
                    self.log(f"Folder {folder} not accessible: {str(e)}", "WARNING")
            
        except Exception as e:
            self.log(f"S3 bucket verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_athena(self) -> Tuple[int, int]:
        """Verify Athena database and tables."""
        print("\n🗄️  Verifying Athena Database...")
        passed = 0
        failed = 0
        
        try:
            # Check database exists
            response = self.athena_client.list_databases(
                CatalogName='AwsDataCatalog'
            )
            databases = [db['Name'] for db in response['DatabaseList']]
            
            if ATHENA_DATABASE in databases:
                self.log(f"Database {ATHENA_DATABASE} exists", "SUCCESS")
                passed += 1
            else:
                self.log(f"Database {ATHENA_DATABASE} not found", "ERROR")
                failed += 1
                return passed, failed
            
            # Check tables exist
            response = self.glue_client.get_tables(
                DatabaseName=ATHENA_DATABASE
            )
            tables = [table['Name'] for table in response['TableList']]
            
            for table_name in REQUIRED_ATHENA_TABLES:
                if table_name in tables:
                    self.log(f"Table {table_name} exists", "SUCCESS")
                    passed += 1
                else:
                    self.log(f"Table {table_name} not found", "ERROR")
                    failed += 1
            
            # Check Athena workgroup
            try:
                response = self.athena_client.get_work_group(
                    WorkGroup=f"brand-metagen-{self.env}"
                )
                self.log(f"Athena workgroup exists", "SUCCESS")
                passed += 1
            except:
                self.log(f"Athena workgroup not found", "WARNING")
            
        except Exception as e:
            self.log(f"Athena verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_dynamodb(self) -> Tuple[int, int]:
        """Verify DynamoDB tables."""
        print("\n💾 Verifying DynamoDB Tables...")
        passed = 0
        failed = 0
        
        try:
            response = self.dynamodb_client.list_tables()
            tables = response['TableNames']
            
            # Check agent memory tables
            for agent in REQUIRED_AGENTS:
                table_name = f"brand-metagen-{agent}-memory-{self.env}"
                if table_name in tables:
                    self.log(f"Table {table_name} exists", "SUCCESS")
                    passed += 1
                else:
                    self.log(f"Table {table_name} not found", "ERROR")
                    failed += 1
            
            # Check workflow state table
            workflow_table = f"brand-metagen-workflow-state-{self.env}"
            if workflow_table in tables:
                self.log(f"Workflow state table exists", "SUCCESS")
                passed += 1
            else:
                self.log(f"Workflow state table not found", "WARNING")
            
        except Exception as e:
            self.log(f"DynamoDB verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_step_functions(self) -> Tuple[int, int]:
        """Verify Step Functions state machine."""
        print("\n🔄 Verifying Step Functions...")
        passed = 0
        failed = 0
        
        try:
            response = self.sfn_client.list_state_machines()
            state_machines = [sm['name'] for sm in response['stateMachines']]
            
            expected_sm = f"brand-metagen-workflow-{self.env}"
            if expected_sm in state_machines:
                self.log(f"State machine {expected_sm} exists", "SUCCESS")
                passed += 1
                
                # Get state machine details
                sm = next(sm for sm in response['stateMachines'] if sm['name'] == expected_sm)
                
                response = self.sfn_client.describe_state_machine(
                    stateMachineArn=sm['stateMachineArn']
                )
                
                self.log(f"State machine status: {response['status']}", "INFO")
                
            else:
                self.log(f"State machine {expected_sm} not found", "ERROR")
                failed += 1
        
        except Exception as e:
            self.log(f"Step Functions verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_lambda(self) -> Tuple[int, int]:
        """Verify Lambda functions."""
        print("\n⚡ Verifying Lambda Functions...")
        passed = 0
        failed = 0
        
        try:
            response = self.lambda_client.list_functions()
            functions = [f['FunctionName'] for f in response['Functions']]
            
            required_functions = [
                f"brand-metagen-orchestrator-invoke-{self.env}",
                f"brand-metagen-workflow-init-{self.env}",
                f"brand-metagen-result-aggregation-{self.env}",
                f"brand-metagen-feedback-submission-{self.env}",
                f"brand-metagen-feedback-processing-{self.env}",
            ]
            
            for func_name in required_functions:
                if func_name in functions:
                    self.log(f"Function {func_name} exists", "SUCCESS")
                    passed += 1
                else:
                    self.log(f"Function {func_name} not found", "WARNING")
        
        except Exception as e:
            self.log(f"Lambda verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_agents(self) -> Tuple[int, int]:
        """Verify Bedrock agents."""
        print("\n🤖 Verifying Bedrock Agents...")
        passed = 0
        failed = 0
        
        try:
            response = self.bedrock_agent_client.list_agents()
            agents = [agent['agentName'] for agent in response.get('agentSummaries', [])]
            
            for agent in REQUIRED_AGENTS:
                agent_name = f"brand_metagen_{agent}_{self.env}"
                if agent_name in agents:
                    self.log(f"Agent {agent} deployed", "SUCCESS")
                    passed += 1
                    
                    # Get agent details
                    agent_obj = next(a for a in response['agentSummaries'] if a['agentName'] == agent_name)
                    self.log(f"  Status: {agent_obj['agentStatus']}", "INFO")
                    
                else:
                    self.log(f"Agent {agent} not deployed", "ERROR")
                    failed += 1
        
        except Exception as e:
            self.log(f"Agent verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_iam(self) -> Tuple[int, int]:
        """Verify IAM roles."""
        print("\n🔐 Verifying IAM Roles...")
        passed = 0
        failed = 0
        
        try:
            # Check agent execution role
            role_name = f"brand_metagen_agent_execution_{self.env}"
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                self.log(f"Agent execution role exists", "SUCCESS")
                passed += 1
            except:
                self.log(f"Agent execution role not found", "ERROR")
                failed += 1
            
            # Check Step Functions execution role
            sfn_role_name = f"brand_metagen_sfn_execution_{self.env}"
            try:
                response = self.iam_client.get_role(RoleName=sfn_role_name)
                self.log(f"Step Functions execution role exists", "SUCCESS")
                passed += 1
            except:
                self.log(f"Step Functions execution role not found", "WARNING")
        
        except Exception as e:
            self.log(f"IAM verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def verify_cloudwatch(self) -> Tuple[int, int]:
        """Verify CloudWatch logs and dashboards."""
        print("\n📊 Verifying CloudWatch...")
        passed = 0
        failed = 0
        
        try:
            # Check log groups
            response = self.logs_client.describe_log_groups(
                logGroupNamePrefix=f"/aws/bedrock/agentcore/brand_metagen"
            )
            
            log_groups = [lg['logGroupName'] for lg in response['logGroups']]
            
            if len(log_groups) > 0:
                self.log(f"Found {len(log_groups)} agent log groups", "SUCCESS")
                passed += 1
            else:
                self.log(f"No agent log groups found", "WARNING")
            
            # Check dashboard
            cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)
            try:
                response = cloudwatch_client.get_dashboard(
                    DashboardName=f"brand-metagen-{self.env}"
                )
                self.log(f"CloudWatch dashboard exists", "SUCCESS")
                passed += 1
            except:
                self.log(f"CloudWatch dashboard not found", "WARNING")
        
        except Exception as e:
            self.log(f"CloudWatch verification failed: {str(e)}", "ERROR")
            failed += 1
        
        return passed, failed
    
    def run(self) -> bool:
        """Run all verifications."""
        print(f"\n{'='*70}")
        print(f"Brand Metadata Generator - Deployment Verification")
        print(f"Environment: {self.env}")
        print(f"Region: {AWS_REGION}")
        print(f"{'='*70}")
        
        total_passed = 0
        total_failed = 0
        
        # Run verifications
        passed, failed = self.verify_s3()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_athena()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_dynamodb()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_step_functions()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_lambda()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_agents()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_iam()
        total_passed += passed
        total_failed += failed
        
        passed, failed = self.verify_cloudwatch()
        total_passed += passed
        total_failed += failed
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"Verification Summary")
        print(f"{'='*70}")
        print(f"Total checks: {total_passed + total_failed}")
        print(f"Passed: {total_passed} ✅")
        print(f"Failed: {total_failed} ❌")
        print()
        
        if total_failed == 0:
            print("🎉 All verifications passed! Deployment is ready.")
            return True
        else:
            print("❌ Some verifications failed. Please review and fix issues.")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify Brand Metadata Generator deployment"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment to verify"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    verifier = DeploymentVerifier(args.env, args.verbose)
    success = verifier.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
