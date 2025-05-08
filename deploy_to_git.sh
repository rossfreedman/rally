#!/bin/bash

# Exit on error
set -e

# Show git status
echo "Checking git status..."
git status

# Stage all changes
echo "Staging all changes..."
git add -A

# Check if there is anything to commit
if git diff --cached --quiet; then
  echo "No changes to commit. Exiting."
  exit 0
fi

# Prompt for commit message
read -p "Enter commit message: " commit_message

# Commit changes
git commit -m "$commit_message"

# Push to main branch
echo "Pushing to origin main..."
git push origin main

echo "Deployment to git complete!" 