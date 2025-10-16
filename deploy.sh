#!/bin/bash

# Production Deployment Script
echo "🚀 Deploying WhatsApp Email Assistant to Production"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root."
    exit 1
fi

# Create production requirements
echo "📦 Creating production requirements..."
cp requirements.production.txt requirements.txt

# Remove development files
echo "🧹 Cleaning up development files..."
rm -f setup*.py
rm -f test*.py
rm -f run.py
rm -f docker-compose.yml
rm -f Dockerfile

# Create necessary directories
echo "📁 Creating production directories..."
mkdir -p data
mkdir -p logs

# Check for required files
echo "✅ Checking required files..."
required_files=("app.py" "production.py" "Procfile" "requirements.txt" "src/")
for file in "${required_files[@]}"; do
    if [ -e "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

# Check for credentials
echo "🔐 Checking credentials..."
if [ -f "credentials.json" ] || [ -f "token.json" ]; then
    echo "  ⚠️  Warning: Credential files found. Make sure to upload them to your production platform."
else
    echo "  ℹ️  No credential files found. You'll need to upload them to production."
fi

echo ""
echo "🎉 Project is ready for production deployment!"
echo ""
echo "Next steps:"
echo "1. Commit your changes: git add . && git commit -m 'Ready for production'"
echo "2. Deploy to your chosen platform (Railway, Heroku, etc.)"
echo "3. Upload credentials.json and token.json files"
echo "4. Set environment variables"
echo "5. Configure webhook URLs"
echo ""
echo "📖 See DEPLOYMENT.md for detailed instructions"
