#!/bin/bash

# Heritage Shops Forecasting - Quick Deploy Script
# This script helps you deploy to GitHub and Streamlit Cloud

echo "================================"
echo "Heritage Shops Deployment Helper"
echo "================================"
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Get GitHub username
echo ""
read -p "Enter your GitHub username: " github_username

# Get repository name
echo ""
read -p "Enter repository name (default: heritage-shops-forecasting): " repo_name
repo_name=${repo_name:-heritage-shops-forecasting}

echo ""
echo "📝 Summary:"
echo "  Repository: https://github.com/$github_username/$repo_name"
echo ""
read -p "Is this correct? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "❌ Cancelled"
    exit 1
fi

# Add all files
echo ""
echo "📦 Adding files to Git..."
git add .

# Commit
echo ""
read -p "Enter commit message (default: Initial commit): " commit_msg
commit_msg=${commit_msg:-"Initial commit - Heritage Shops forecasting system"}

git commit -m "$commit_msg"
echo "✅ Files committed"

# Check if remote exists
if git remote | grep -q "origin"; then
    echo "🔄 Remote 'origin' already exists, removing..."
    git remote remove origin
fi

# Add remote
echo ""
echo "🔗 Connecting to GitHub..."
git remote add origin "https://github.com/$github_username/$repo_name.git"

# Rename branch to main if needed
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "main" ]; then
    echo "📝 Renaming branch to 'main'..."
    git branch -M main
fi

# Push to GitHub
echo ""
echo "🚀 Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ================================"
    echo "✅ Successfully pushed to GitHub!"
    echo "✅ ================================"
    echo ""
    echo "📊 Your repository: https://github.com/$github_username/$repo_name"
    echo ""
    echo "🌐 NEXT STEPS:"
    echo "1. Go to: https://streamlit.io/cloud"
    echo "2. Sign in with GitHub"
    echo "3. Click 'New app'"
    echo "4. Select your repository: $github_username/$repo_name"
    echo "5. Main file: app.py"
    echo "6. Click 'Deploy!'"
    echo ""
    echo "Your app will be live at:"
    echo "https://$repo_name.streamlit.app"
    echo ""
else
    echo ""
    echo "❌ Push failed. Common issues:"
    echo "  1. Repository doesn't exist on GitHub"
    echo "     → Create it at: https://github.com/new"
    echo "  2. Authentication failed"
    echo "     → Set up SSH keys or use GitHub CLI"
    echo ""
    echo "After fixing, run: git push -u origin main"
fi
