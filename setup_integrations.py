#!/usr/bin/env python3
"""
Integration Setup Script
This script helps you set up Gmail and Calendar integrations
"""

import os
import subprocess
import sys
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("📦 Installing required packages...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        print("✅ Required packages installed!")
    else:
        print("✅ All required packages are already installed!")

def setup_environment():
    """Set up environment variables"""
    env_content = """# Basic configuration
DEBUG=true
LOG_LEVEL=INFO

# WhatsApp Integration (UltraMsg) - Your actual values
ULTRAMSG_API_URL=https://api.ultramsg.com
ULTRAMSG_INSTANCE_ID=140834
ULTRAMSG_TOKEN=your_actual_token_here
MY_PHONE_NUMBER=5530386114

# OpenAI Configuration - Add your actual API key
OPENAI_API_KEY=your_openai_api_key_here

# Gmail and Calendar Integration
GMAIL_CREDENTIALS_FILE=./credentials/gmail_credentials.json
GMAIL_TOKEN_FILE=./credentials/gmail_token.json
CALENDAR_CREDENTIALS_FILE=./credentials/calendar_credentials.json
CALENDAR_TOKEN_FILE=./credentials/calendar_token.json
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with default configuration")
        print("⚠️  Please update the token values in .env file")
    else:
        print("✅ .env file already exists")

def main():
    print("🚀 Setting up Gmail and Calendar integrations...")
    
    # Check requirements
    check_requirements()
    
    # Create credentials directory
    os.makedirs('credentials', exist_ok=True)
    print("✅ Created credentials directory")
    
    # Set up environment
    setup_environment()
    
    print("\n📋 Next steps:")
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Gmail API and Calendar API")
    print("4. Create OAuth 2.0 credentials for Desktop Application")
    print("5. Download the credentials and save them as:")
    print("   - credentials/gmail_credentials.json")
    print("   - credentials/calendar_credentials.json")
    print("6. Update your .env file with actual token values")
    print("7. Run: python setup_gmail_auth.py")
    print("8. Run: python setup_calendar_auth.py")
    print("\n🎉 Then your assistant will have full email and calendar capabilities!")

if __name__ == "__main__":
    main()


