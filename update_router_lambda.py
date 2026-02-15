#!/usr/bin/env python3
"""Update just the router Lambda code."""

import boto3
import zipfile
import tempfile
from pathlib import Path

def update_router_lambda():
    """Update the router Lambda function code."""
    
    lambda_client = boto3.client('lambda', region_name='eu-west-1')
    function_name = "brand_metagen_conversational_router_dev"
    
    # Package Lambda code
    handler_path = Path("lambda_functions/conversational_router/handler.py")
    
    if not handler_path.exists():
        print(f"❌ Router handler not found: {handler_path}")
        return False
    
    # Create deployment package
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
        zip_path = tmp_file.name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, 'handler.py')
        
        # Read zip file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
    
    try:
        print(f"Updating Lambda function code: {function_name}")
        
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✅ Router Lambda code updated successfully")
        print(f"   Version: {response.get('Version')}")
        print(f"   Last Modified: {response.get('LastModified')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update router Lambda: {str(e)}")
        return False

if __name__ == "__main__":
    update_router_lambda()