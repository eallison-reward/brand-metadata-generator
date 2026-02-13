#!/bin/bash
# Package Lambda functions for deployment

set -e

echo "Packaging Lambda functions..."

# Create dist directory if it doesn't exist
mkdir -p lambda_functions/dist

# Package workflow_init
echo "Packaging workflow_init..."
cd lambda_functions/workflow_init
pip install -r requirements.txt -t .
zip -r ../workflow_init.zip . -x "*.pyc" -x "__pycache__/*"
cd ../..

# Package orchestrator_invoke
echo "Packaging orchestrator_invoke..."
cd lambda_functions/orchestrator_invoke
pip install -r requirements.txt -t .
zip -r ../orchestrator_invoke.zip . -x "*.pyc" -x "__pycache__/*"
cd ../..

# Package result_aggregation
echo "Packaging result_aggregation..."
cd lambda_functions/result_aggregation
pip install -r requirements.txt -t .
zip -r ../result_aggregation.zip . -x "*.pyc" -x "__pycache__/*"
cd ../..

echo "Lambda functions packaged successfully!"
echo "Packages created:"
echo "  - lambda_functions/workflow_init.zip"
echo "  - lambda_functions/orchestrator_invoke.zip"
echo "  - lambda_functions/result_aggregation.zip"
