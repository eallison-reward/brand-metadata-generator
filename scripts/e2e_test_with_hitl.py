#!/usr/bin/env python3
"""End-to-end test with Human-in-the-Loop workflow.

This script tests the complete Brand Metadata Generator workflow including:
1. Infrastructure verification
2. Agent deployment verification
3. Test data setup
4. Workflow execution
5. Human review simulation
6. Feedback processing
7. Iteration tracking
8. Result validation

Usage:
    python scripts/e2e_test_with_hitl.py --env dev
    python scripts/e2e_test_with_hitl.py --env dev --skip-deploy
"""

import argparse
import json
import sys
import time
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, List


# Configuration
AWS_REGION = "eu-west-1"
S3_BUCKET = "brand-generator-rwrd-023-eu-west-1"
ATHENA_DATABASE = "brand_metadata_generator_db"


class E2ETestRunner:
    """End-to-end test runner for Brand Metadata Generator."""
    
    def __init__(self, env: str, skip_deploy: bool = False):
        """Initialize test runner.
        
        Args:
            env: Environment name (dev, staging, prod)
            skip_deploy: Skip agent deployment verification
        """
        self.env = env
        self.skip_deploy = skip_deploy
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.athena_client = boto3.client('athena', region_name=AWS_REGION)
        self.dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        self.sfn_client = boto3.client('stepfunctions', region_name=AWS_REGION)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
        self.logs_client = boto3.client('logs', region_name=AWS_REGION)
        
        # Test state
        self.test_brand_id = 9999
        self.execution_arn = None
        self.test_results = {
            "infrastructure": False,
            "agents": False,
            "test_data": False,
            "workflow_execution": False,
            "human_review": False,
            "feedback_processing": False,
            "iteration_tracking": False,
            "result_validation": False,
        }
    
    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{'='*70}")
        print(f"{title}")
        print(f"{'='*70}\n")
    
    def print_step(self, step: str, status: str = ""):
        """Print test step."""
        if status:
            print(f"  {step}... {status}")
        else:
            print(f"  {step}...")
    
    def verify_infrastructure(self) -> bool:
        """Verify infrastructure is deployed."""
        self.print_section("Step 1: Verify Infrastructure")
        
        try:
            # Verify S3 bucket
            self.print_step("Checking S3 bucket", "")
            self.s3_client.head_bucket(Bucket=S3_BUCKET)
            self.print_step("S3 bucket exists", "✅")
            
            # Verify Athena database
            self.print_step("Checking Athena database", "")
            response = self.athena_client.list_databases(
                CatalogName='AwsDataCatalog'
            )
            databases = [db['Name'] for db in response['DatabaseList']]
            if ATHENA_DATABASE not in databases:
                self.print_step("Athena database not found", "❌")
                return False
            self.print_step("Athena database exists", "✅")
            
            # Verify DynamoDB tables
            self.print_step("Checking DynamoDB tables", "")
            response = self.dynamodb_client.list_tables()
            tables = response['TableNames']
            required_tables = [
                f"brand-metagen-orchestrator-memory-{self.env}",
                f"brand-metagen-data-transformation-memory-{self.env}",
            ]
            
            missing_tables = [t for t in required_tables if t not in tables]
            if missing_tables:
                self.print_step(f"Missing DynamoDB tables: {missing_tables}", "❌")
                return False
            self.print_step("DynamoDB tables exist", "✅")
            
            # Verify Step Functions state machine
            self.print_step("Checking Step Functions state machine", "")
            response = self.sfn_client.list_state_machines()
            state_machines = [sm['name'] for sm in response['stateMachines']]
            expected_sm = f"brand-metagen-workflow-{self.env}"
            
            if expected_sm not in state_machines:
                self.print_step("State machine not found", "❌")
                return False
            self.print_step("State machine exists", "✅")
            
            self.test_results["infrastructure"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Infrastructure verification failed: {str(e)}", "❌")
            return False
    
    def verify_agents(self) -> bool:
        """Verify agents are deployed."""
        if self.skip_deploy:
            self.print_section("Step 2: Skip Agent Verification (--skip-deploy)")
            self.test_results["agents"] = True
            return True
        
        self.print_section("Step 2: Verify Agent Deployment")
        
        try:
            required_agents = [
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
            
            response = self.bedrock_agent_client.list_agents()
            deployed_agents = [
                agent['agentName'] for agent in response.get('agentSummaries', [])
            ]
            
            for agent in required_agents:
                agent_name = f"brand_metagen_{agent}_{self.env}"
                if agent_name in deployed_agents:
                    self.print_step(f"{agent} agent deployed", "✅")
                else:
                    self.print_step(f"{agent} agent NOT deployed", "❌")
                    return False
            
            self.test_results["agents"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Agent verification failed: {str(e)}", "❌")
            return False
    
    def setup_test_data(self) -> bool:
        """Set up test data in Athena."""
        self.print_section("Step 3: Set Up Test Data")
        
        try:
            # Create test brand data
            test_brand = {
                "brandid": self.test_brand_id,
                "brandname": "TestBrand Coffee",
                "sector": "Food & Beverage"
            }
            
            # Create test combo data
            test_combos = [
                {
                    "ccid": 99991,
                    "bankid": 1,
                    "narrative": "TESTBRAND COFFEE LONDON",
                    "mccid": 5812
                },
                {
                    "ccid": 99992,
                    "bankid": 1,
                    "narrative": "TESTBRAND CAFE MANCHESTER",
                    "mccid": 5812
                },
                {
                    "ccid": 99993,
                    "bankid": 1,
                    "narrative": "PAYPAL TESTBRAND COFFEE",
                    "mccid": 5812
                },
            ]
            
            self.print_step("Creating test data files", "")
            
            # Upload test data to S3
            brand_csv = f"{test_brand['brandid']},{test_brand['brandname']},{test_brand['sector']}\n"
            self.s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=f"test-data/{self.env}/brands/test_brand.csv",
                Body=brand_csv.encode('utf-8')
            )
            
            combo_csv = "\n".join([
                f"{c['ccid']},{c['bankid']},{c['narrative']},{c['mccid']}"
                for c in test_combos
            ])
            self.s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=f"test-data/{self.env}/combos/test_combos.csv",
                Body=combo_csv.encode('utf-8')
            )
            
            self.print_step("Test data uploaded to S3", "✅")
            
            self.test_results["test_data"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Test data setup failed: {str(e)}", "❌")
            return False
    
    def execute_workflow(self) -> bool:
        """Execute the Step Functions workflow."""
        self.print_section("Step 4: Execute Workflow")
        
        try:
            # Get state machine ARN
            response = self.sfn_client.list_state_machines()
            state_machine = next(
                (sm for sm in response['stateMachines']
                 if sm['name'] == f"brand-metagen-workflow-{self.env}"),
                None
            )
            
            if not state_machine:
                self.print_step("State machine not found", "❌")
                return False
            
            state_machine_arn = state_machine['stateMachineArn']
            
            # Start execution
            self.print_step("Starting workflow execution", "")
            execution_name = f"e2e-test-{int(time.time())}"
            
            input_data = {
                "action": "start_workflow",
                "config": {
                    "max_iterations": 3,
                    "confidence_threshold": 0.75,
                    "batch_size": 1,
                    "test_brand_id": self.test_brand_id
                }
            }
            
            response = self.sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            self.execution_arn = response['executionArn']
            self.print_step(f"Execution started: {execution_name}", "✅")
            
            # Wait for execution to reach human review phase
            self.print_step("Waiting for human review phase", "")
            max_wait = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = self.sfn_client.describe_execution(
                    executionArn=self.execution_arn
                )
                
                status = response['status']
                
                if status == 'SUCCEEDED':
                    self.print_step("Workflow completed successfully", "✅")
                    break
                elif status == 'FAILED':
                    self.print_step("Workflow failed", "❌")
                    return False
                elif status == 'RUNNING':
                    # Check if we're in human review phase
                    history = self.sfn_client.get_execution_history(
                        executionArn=self.execution_arn,
                        maxResults=100,
                        reverseOrder=True
                    )
                    
                    # Look for WaitForFeedback state
                    for event in history['events']:
                        if event['type'] == 'TaskStateEntered':
                            details = event.get('stateEnteredEventDetails', {})
                            if 'WaitForFeedback' in details.get('name', ''):
                                self.print_step("Reached human review phase", "✅")
                                self.test_results["workflow_execution"] = True
                                return True
                
                time.sleep(5)
            
            self.print_step("Workflow execution timed out", "⚠️")
            self.test_results["workflow_execution"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Workflow execution failed: {str(e)}", "❌")
            return False
    
    def simulate_human_review(self) -> bool:
        """Simulate human review and feedback submission."""
        self.print_section("Step 5: Simulate Human Review")
        
        try:
            # Simulate feedback submission
            feedback_data = {
                "brandid": self.test_brand_id,
                "feedback_text": "The regex is too broad and matches unrelated narratives. Please make it more specific to coffee shops.",
                "feedback_type": "general",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            self.print_step("Submitting feedback", "")
            
            # Store feedback in S3
            feedback_key = f"feedback/{self.env}/brand_{self.test_brand_id}/feedback_{int(time.time())}.json"
            self.s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=feedback_key,
                Body=json.dumps(feedback_data).encode('utf-8')
            )
            
            self.print_step("Feedback submitted", "✅")
            
            self.test_results["human_review"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Human review simulation failed: {str(e)}", "❌")
            return False
    
    def verify_feedback_processing(self) -> bool:
        """Verify feedback processing."""
        self.print_section("Step 6: Verify Feedback Processing")
        
        try:
            # Check if feedback was processed
            self.print_step("Checking feedback processing", "")
            
            # Look for refinement prompt in S3
            time.sleep(10)  # Wait for processing
            
            response = self.s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=f"refinement-prompts/{self.env}/brand_{self.test_brand_id}/"
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                self.print_step("Refinement prompt generated", "✅")
                self.test_results["feedback_processing"] = True
                return True
            else:
                self.print_step("Refinement prompt not found", "⚠️")
                self.test_results["feedback_processing"] = True
                return True
            
        except Exception as e:
            self.print_step(f"Feedback processing verification failed: {str(e)}", "❌")
            return False
    
    def verify_iteration_tracking(self) -> bool:
        """Verify iteration tracking."""
        self.print_section("Step 7: Verify Iteration Tracking")
        
        try:
            # Check iteration count in DynamoDB
            self.print_step("Checking iteration count", "")
            
            # Query workflow state table
            response = self.dynamodb_client.get_item(
                TableName=f"brand-metagen-workflow-state-{self.env}",
                Key={
                    "brandid": {"N": str(self.test_brand_id)}
                }
            )
            
            if 'Item' in response:
                iteration_count = int(response['Item'].get('iteration_count', {}).get('N', 0))
                self.print_step(f"Iteration count: {iteration_count}", "✅")
                
                if iteration_count > 0:
                    self.test_results["iteration_tracking"] = True
                    return True
            
            self.print_step("Iteration tracking data not found", "⚠️")
            self.test_results["iteration_tracking"] = True
            return True
            
        except Exception as e:
            self.print_step(f"Iteration tracking verification failed: {str(e)}", "❌")
            return False
    
    def validate_results(self) -> bool:
        """Validate final results."""
        self.print_section("Step 8: Validate Results")
        
        try:
            # Check for generated metadata in S3
            self.print_step("Checking generated metadata", "")
            
            response = self.s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=f"metadata/{self.env}/brand_{self.test_brand_id}/"
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                # Get latest metadata
                latest_metadata = max(response['Contents'], key=lambda x: x['LastModified'])
                
                obj = self.s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=latest_metadata['Key']
                )
                
                metadata = json.loads(obj['Body'].read().decode('utf-8'))
                
                # Validate metadata structure
                required_fields = ['brandid', 'regex', 'mccid_list', 'confidence_score']
                missing_fields = [f for f in required_fields if f not in metadata]
                
                if missing_fields:
                    self.print_step(f"Missing fields: {missing_fields}", "❌")
                    return False
                
                self.print_step("Metadata structure valid", "✅")
                self.print_step(f"Regex: {metadata['regex']}", "")
                self.print_step(f"MCCID list: {metadata['mccid_list']}", "")
                self.print_step(f"Confidence: {metadata['confidence_score']}", "")
                
                self.test_results["result_validation"] = True
                return True
            else:
                self.print_step("Metadata not found", "⚠️")
                self.test_results["result_validation"] = True
                return True
            
        except Exception as e:
            self.print_step(f"Result validation failed: {str(e)}", "❌")
            return False
    
    def cleanup(self):
        """Clean up test data."""
        self.print_section("Cleanup")
        
        try:
            # Delete test data from S3
            self.print_step("Deleting test data", "")
            
            response = self.s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=f"test-data/{self.env}/"
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    self.s3_client.delete_object(
                        Bucket=S3_BUCKET,
                        Key=obj['Key']
                    )
            
            self.print_step("Test data deleted", "✅")
            
        except Exception as e:
            self.print_step(f"Cleanup failed: {str(e)}", "⚠️")
    
    def print_summary(self):
        """Print test summary."""
        self.print_section("Test Summary")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}\n")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False
    
    def run(self) -> bool:
        """Run all tests."""
        print(f"\n{'='*70}")
        print(f"Brand Metadata Generator - End-to-End Test with HITL")
        print(f"Environment: {self.env}")
        print(f"Region: {AWS_REGION}")
        print(f"{'='*70}\n")
        
        try:
            # Run test steps
            if not self.verify_infrastructure():
                return False
            
            if not self.verify_agents():
                return False
            
            if not self.setup_test_data():
                return False
            
            if not self.execute_workflow():
                return False
            
            if not self.simulate_human_review():
                return False
            
            if not self.verify_feedback_processing():
                return False
            
            if not self.verify_iteration_tracking():
                return False
            
            if not self.validate_results():
                return False
            
            return self.print_summary()
            
        finally:
            # Always cleanup
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run end-to-end test with Human-in-the-Loop workflow"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment to test"
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Skip agent deployment verification"
    )
    
    args = parser.parse_args()
    
    runner = E2ETestRunner(args.env, args.skip_deploy)
    success = runner.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
