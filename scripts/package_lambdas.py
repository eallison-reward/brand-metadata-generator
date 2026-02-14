#!/usr/bin/env python3
"""Package Lambda functions into ZIP files for deployment.

This script creates ZIP files for all Lambda functions required by Terraform.
"""

import os
import zipfile
from pathlib import Path


def create_lambda_zip(function_name: str, source_dir: str, output_dir: str):
    """Create ZIP file for a Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        source_dir: Directory containing the Lambda function code
        output_dir: Directory to write the ZIP file
    """
    zip_path = Path(output_dir) / f"{function_name}.zip"
    
    print(f"Creating {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        source_path = Path(source_dir)
        
        # Add handler.py
        handler_file = source_path / "handler.py"
        if handler_file.exists():
            zipf.write(handler_file, "handler.py")
            print(f"  Added handler.py")
        else:
            print(f"  Warning: handler.py not found in {source_path}")
        
        # Add __init__.py if it exists
        init_file = source_path / "__init__.py"
        if init_file.exists():
            zipf.write(init_file, "__init__.py")
            print(f"  Added __init__.py")
    
    print(f"  Created {zip_path} ({zip_path.stat().st_size} bytes)")


def main():
    """Main entry point."""
    # Lambda functions to package
    lambda_functions = [
        "feedback_submission",
        "feedback_retrieval",
        "status_updates",
        "brand_data_retrieval",
        "feedback_processing_loop",
        "wait_for_feedback",
        "prepare_human_review",
        "escalation",
        "metadata_regeneration",
        "update_monitoring",
        "result_aggregation",
    ]
    
    base_dir = Path(__file__).parent.parent
    lambda_dir = base_dir / "lambda_functions"
    output_dir = lambda_dir
    
    print(f"Packaging Lambda functions...")
    print(f"Source directory: {lambda_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    for function_name in lambda_functions:
        source_dir = lambda_dir / function_name
        if source_dir.exists():
            create_lambda_zip(function_name, source_dir, output_dir)
        else:
            print(f"Warning: {source_dir} not found, skipping...")
        print()
    
    print("Done!")


if __name__ == "__main__":
    main()
