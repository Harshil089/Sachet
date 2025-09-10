#!/bin/bash
# Deployment script for Missing Child Alert System

echo "🚀 Deploying Missing Child Alert System..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root."
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "🔄 Initializing Git repository..."
    git init
fi

# Add all files
echo "📁 Adding files to Git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Deploy missing child alert system with persistent database"

# Check if remote exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "❌ No remote repository found. Please add your GitHub repository:"
    echo "   git remote add origin https://github.com/yourusername/your-repo.git"
    exit 1
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main

echo "✅ Code pushed to GitHub successfully!"
echo ""
echo "Next steps:"
echo "1. Go to https://render.com"
echo "2. Connect your GitHub repository"
echo "3. Create a PostgreSQL database"
echo "4. Set the DATABASE_URL environment variable"
echo "5. Deploy your web service"
echo ""
echo "Your data will persist across deployments! 🎉"
