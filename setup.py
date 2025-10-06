#!/usr/bin/env python3
"""
Setup script for Personal WhatsApp Assistant
Helps with initial configuration and dependency installation
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print("✅ Python version is compatible")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

def create_config_files():
    """Create necessary configuration files"""
    print("📝 Creating configuration files...")
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# UltraMsg Configuration
ULTRAMSG_API_URL=https://api.ultramsg.com
ULTRAMSG_INSTANCE_ID=your_instance_id_here
ULTRAMSG_TOKEN=your_token_here
MY_PHONE_NUMBER=1234567890

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Custom settings
EMAIL_CHECK_INTERVAL=300
AUTO_CHECK_EMAILS=true
"""
        with open(env_file, "w") as f:
            f.write(env_content)
        print("✅ Created .env file")
    else:
        print("✅ .env file already exists")
    
    # Create user style file
    style_file = Path("user_style.json")
    if not style_file.exists():
        style_content = {
            "tone": "professional",
            "formality": "medium",
            "length_preference": "medium",
            "greeting_style": "Hi",
            "closing_style": "Best regards",
            "common_phrases": [],
            "avoid_phrases": [],
            "signature": ""
        }
        with open(style_file, "w") as f:
            json.dump(style_content, f, indent=2)
        print("✅ Created user_style.json")
    else:
        print("✅ user_style.json already exists")
    
    # Create HITL config file
    hitl_file = Path("hitl_config.json")
    if not hitl_file.exists():
        hitl_content = {
            "auto_approve_patterns": [],
            "auto_reject_patterns": []
        }
        with open(hitl_file, "w") as f:
            json.dump(hitl_content, f, indent=2)
        print("✅ Created hitl_config.json")
    else:
        print("✅ hitl_config.json already exists")

def check_api_credentials():
    """Check if API credentials are configured"""
    print("🔑 Checking API credentials...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    credentials = {
        "ULTRAMSG_INSTANCE_ID": os.getenv("ULTRAMSG_INSTANCE_ID"),
        "ULTRAMSG_TOKEN": os.getenv("ULTRAMSG_TOKEN"),
        "MY_PHONE_NUMBER": os.getenv("MY_PHONE_NUMBER"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
    }
    
    missing = []
    for key, value in credentials.items():
        if not value or value.endswith("_here"):
            missing.append(key)
    
    if missing:
        print("⚠️  Missing or incomplete credentials:")
        for key in missing:
            print(f"   - {key}")
        print("\nPlease update your .env file with the correct values")
        return False
    else:
        print("✅ All API credentials are configured")
        return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = ["logs", "data"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/ directory")

def main():
    """Main setup function"""
    print("🤖 Personal WhatsApp Assistant Setup")
    print("=" * 40)
    
    # Check Python version
    check_python_version()
    
    # Install dependencies
    install_dependencies()
    
    # Create configuration files
    create_config_files()
    
    # Create directories
    create_directories()
    
    # Check credentials
    credentials_ok = check_api_credentials()
    
    print("\n" + "=" * 40)
    if credentials_ok:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Set up your API credentials (Gmail, Calendar, UltraMsg)")
        print("2. Run: python app.py")
        print("3. Follow the OAuth setup instructions")
    else:
        print("⚠️  Setup completed with warnings")
        print("\nPlease complete the configuration and run setup again")
    
    print("\nFor detailed setup instructions, see README.md")

if __name__ == "__main__":
    main()

