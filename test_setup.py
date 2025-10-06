#!/usr/bin/env python3
"""
Test script to verify the Personal WhatsApp Assistant setup
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import fastapi
        print("✅ FastAPI imported successfully")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn imported successfully")
    except ImportError as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        print("✅ Google Auth imported successfully")
    except ImportError as e:
        print(f"❌ Google Auth import failed: {e}")
        return False
    
    try:
        from googleapiclient.discovery import build
        print("✅ Google API Client imported successfully")
    except ImportError as e:
        print(f"❌ Google API Client import failed: {e}")
        return False
    
    try:
        from langchain.llms import OpenAI
        print("✅ LangChain imported successfully")
    except ImportError as e:
        print(f"❌ LangChain import failed: {e}")
        return False
    
    try:
        import openai
        print("✅ OpenAI imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False
    
    return True

def test_project_structure():
    """Test if project structure is correct"""
    print("\n📁 Testing project structure...")
    
    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        "src/__init__.py",
        "src/integrations/__init__.py",
        "src/integrations/whatsapp.py",
        "src/integrations/gmail.py",
        "src/integrations/calendar.py",
        "src/ai/__init__.py",
        "src/ai/summarizer.py",
        "src/ai/responder.py",
        "src/core/__init__.py",
        "src/core/hitl.py",
        "src/core/router.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_configuration():
    """Test configuration files"""
    print("\n⚙️  Testing configuration...")
    
    # Check if .env exists
    if not Path(".env").exists():
        print("⚠️  .env file not found - you'll need to create it")
        return False
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded successfully")
    except ImportError:
        print("⚠️  python-dotenv not installed - install it with: pip install python-dotenv")
        return False
    
    # Check for required environment variables
    required_vars = [
        "ULTRAMSG_INSTANCE_ID",
        "ULTRAMSG_TOKEN", 
        "MY_PHONE_NUMBER",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var).endswith("_here"):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️  Missing or incomplete environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("Please update your .env file with the correct values")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def test_ai_components():
    """Test AI components initialization"""
    print("\n🤖 Testing AI components...")
    
    try:
        from src.ai.summarizer import EmailSummarizer
        from src.ai.responder import EmailResponder
        
        summarizer = EmailSummarizer()
        responder = EmailResponder()
        
        print("✅ AI components initialized successfully")
        
        # Test status
        summarizer_status = summarizer.get_status()
        responder_status = responder.get_status()
        
        print(f"   - Summarizer available: {summarizer_status['available']}")
        print(f"   - Responder available: {responder_status['available']}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI components test failed: {e}")
        return False

def test_integrations():
    """Test integration components"""
    print("\n🔌 Testing integrations...")
    
    try:
        from src.integrations.whatsapp import WhatsAppIntegration
        from src.integrations.gmail import GmailIntegration
        from src.integrations.calendar import CalendarIntegration
        
        whatsapp = WhatsAppIntegration()
        gmail = GmailIntegration()
        calendar = CalendarIntegration()
        
        print("✅ Integration components initialized successfully")
        
        # Test status
        whatsapp_status = whatsapp.get_status()
        gmail_status = gmail.get_status()
        calendar_status = calendar.get_status()
        
        print(f"   - WhatsApp configured: {whatsapp_status['configured']}")
        print(f"   - Gmail available: {gmail_status['available']}")
        print(f"   - Calendar available: {calendar_status['available']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integrations test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Personal WhatsApp Assistant - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("AI Components", test_ai_components),
        ("Integrations", test_integrations)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Follow the OAuth setup instructions")
        print("3. Configure your UltraMsg webhook")
    else:
        print("⚠️  Some tests failed. Please fix the issues and run the test again.")
        print("\nFor help, see README.md or run: python setup.py")

if __name__ == "__main__":
    main()

