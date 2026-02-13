# PowerShell script to package Lambda functions for deployment

Write-Host "Packaging Lambda functions..." -ForegroundColor Green

# Create dist directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "lambda_functions" | Out-Null

# Package workflow_init
Write-Host "Packaging workflow_init..." -ForegroundColor Yellow
Set-Location "lambda_functions/workflow_init"
pip install -r requirements.txt -t .
Compress-Archive -Path * -DestinationPath "../workflow_init.zip" -Force
Set-Location "../.."

# Package orchestrator_invoke
Write-Host "Packaging orchestrator_invoke..." -ForegroundColor Yellow
Set-Location "lambda_functions/orchestrator_invoke"
pip install -r requirements.txt -t .
Compress-Archive -Path * -DestinationPath "../orchestrator_invoke.zip" -Force
Set-Location "../.."

# Package result_aggregation
Write-Host "Packaging result_aggregation..." -ForegroundColor Yellow
Set-Location "lambda_functions/result_aggregation"
pip install -r requirements.txt -t .
Compress-Archive -Path * -DestinationPath "../result_aggregation.zip" -Force
Set-Location "../.."

Write-Host "Lambda functions packaged successfully!" -ForegroundColor Green
Write-Host "Packages created:" -ForegroundColor Cyan
Write-Host "  - lambda_functions/workflow_init.zip"
Write-Host "  - lambda_functions/orchestrator_invoke.zip"
Write-Host "  - lambda_functions/result_aggregation.zip"
