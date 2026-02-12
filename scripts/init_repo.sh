#!/bin/bash
# Initialize Git repository and create initial commit

set -e

echo "🚀 Initializing Brand Metadata Generator repository..."

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "ℹ️  Git repository already initialized"
fi

# Create initial commit
echo "📝 Creating initial commit..."
git add .
git commit -m "chore: initial project setup

- Add project structure with agents, infrastructure, and tests
- Add README, CONTRIBUTING, and documentation
- Add Terraform modules for AWS infrastructure
- Add Python dependencies and setup files
- Add CI/CD workflow with GitHub Actions
- Add deployment scripts for AgentCore agents"

echo "✅ Initial commit created"

# Display next steps
echo ""
echo "🎉 Repository initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Create a repository on GitHub"
echo "2. Add the remote:"
echo "   git remote add origin https://github.com/your-org/brand-metadata-generator.git"
echo "3. Push to GitHub:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "Or use GitHub CLI:"
echo "   gh repo create brand-metadata-generator --public --source=. --remote=origin"
echo "   git push -u origin main"
