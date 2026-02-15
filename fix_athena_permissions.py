#!/usr/bin/env python3
"""Fix Athena permissions for conversational tools."""

import boto3
import json

def fix_athena_permissions():
    """Add missing Athena permissions to the conversational tools role."""
    
    iam_client = boto3.client('iam', region_name='eu-west-1')
    role_name = "brand_metagen_conversational_tools_dev"
    policy_name = "conversational_tools_policy"
    
    # Updated policy with additional Athena permissions
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:ListBucketMultipartUploads",
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload"
                ],
                "Resource": [
                    "arn:aws:s3:::brand-generator-rwrd-023-eu-west-1",
                    "arn:aws:s3:::brand-generator-rwrd-023-eu-west-1/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:StopQueryExecution",
                    "athena:GetWorkGroup",
                    "athena:GetDataCatalog"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetPartitions",
                    "glue:GetDatabases",
                    "glue:GetTables"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "states:StartExecution",
                    "states:DescribeExecution",
                    "states:ListExecutions"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:eu-west-1:536824473420:*"
            }
        ]
    }
    
    try:
        # Update the role policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Updated IAM policy for role: {role_name}")
        print("Added permissions for:")
        print("  - Additional S3 operations (GetBucketLocation, multipart uploads)")
        print("  - Additional Athena operations (GetWorkGroup, GetDataCatalog)")
        print("  - Additional Glue operations (GetDatabases, GetTables)")
        print("  - CloudWatch Logs permissions")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update IAM policy: {str(e)}")
        return False

if __name__ == "__main__":
    fix_athena_permissions()