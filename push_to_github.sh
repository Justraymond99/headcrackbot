#!/bin/bash
# Helper script to push to GitHub

echo "🚀 Pushing to GitHub for Railway Deployment"
echo "==========================================="
echo ""

# Check if remote exists
if git remote | grep -q origin; then
    echo "✅ Remote 'origin' already exists"
    REMOTE_URL=$(git remote get-url origin)
    echo "   URL: $REMOTE_URL"
    echo ""
    read -p "Push to existing remote? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push -u origin main
        echo ""
        echo "✅ Pushed to GitHub!"
        echo ""
        echo "Next steps:"
        echo "1. Go to railway.app"
        echo "2. New Project → Deploy from GitHub repo"
        echo "3. Select your repository"
    fi
else
    echo "⚠️  No GitHub remote configured yet"
    echo ""
    echo "📋 Steps to create GitHub repo:"
    echo ""
    echo "1. Go to: https://github.com/new"
    echo "2. Repository name: hourly-picks-scheduler (or any name)"
    echo "3. Choose: Private (recommended)"
    echo "4. DO NOT check 'Initialize with README'"
    echo "5. Click 'Create repository'"
    echo ""
    read -p "Have you created the repo? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Enter your GitHub username: " GITHUB_USER
        read -p "Enter your repo name: " REPO_NAME
        
        REMOTE_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"
        echo ""
        echo "Adding remote: $REMOTE_URL"
        git remote add origin "$REMOTE_URL"
        git branch -M main
        git push -u origin main
        
        echo ""
        echo "✅ Pushed to GitHub!"
        echo ""
        echo "Next steps:"
        echo "1. Go to railway.app"
        echo "2. New Project → Deploy from GitHub repo"
        echo "3. Select: $REPO_NAME"
    else
        echo ""
        echo "Create the repo first, then run this script again!"
    fi
fi

