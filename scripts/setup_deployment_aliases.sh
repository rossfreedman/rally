#!/bin/bash
# Setup deployment helper aliases for Rally project

echo "Setting up deployment helper aliases..."

# Create the aliases
cat >> ~/.zshrc << 'EOF'

# Rally Deployment Helpers
alias deploy-check='python scripts/check_deployment_status.py'
alias deploy-status='git status && echo -e "\n--- Unpushed commits ---" && git log origin/main..HEAD --oneline'
alias deploy-sync='git add . && git commit -m "sync: Update from local development" && git push origin main'
alias deploy-diff='git diff origin/main..HEAD --name-only'

EOF

echo "✅ Aliases added to ~/.zshrc"
echo ""
echo "🔄 Run 'source ~/.zshrc' or restart your terminal to use:"
echo "   deploy-check     - Check if local/remote are in sync"
echo "   deploy-status    - Quick git status and unpushed commits"
echo "   deploy-sync      - Quick commit and push (use carefully!)"
echo "   deploy-diff      - See what files differ from deployed version" 