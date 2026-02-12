# Initialize Git repository and create initial commit (PowerShell)

Write-Host "Initializing Brand Metadata Generator repository..." -ForegroundColor Green

# Initialize git if not already initialized
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "Git repository already initialized" -ForegroundColor Cyan
}

# Create initial commit
Write-Host "Creating initial commit..." -ForegroundColor Yellow
git add .
git commit -m "chore: initial project setup" -m "Add project structure with agents, infrastructure, and tests" -m "Add README, CONTRIBUTING, and documentation" -m "Add Terraform modules for AWS infrastructure" -m "Add Python dependencies and setup files" -m "Add CI/CD workflow with GitHub Actions" -m "Add deployment scripts for AgentCore agents"

Write-Host "Initial commit created" -ForegroundColor Green

# Display next steps
Write-Host ""
Write-Host "Repository initialized successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Create a repository on GitHub"
Write-Host "2. Add the remote:"
Write-Host "   git remote add origin https://github.com/your-org/brand-metadata-generator.git"
Write-Host "3. Push to GitHub:"
Write-Host "   git branch -M main"
Write-Host "   git push -u origin main"
Write-Host ""
Write-Host "Or use GitHub CLI:" -ForegroundColor Cyan
Write-Host "   gh repo create brand-metadata-generator --public --source=. --remote=origin"
Write-Host "   git push -u origin main"
