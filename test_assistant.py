#!/usr/bin/env python3
"""
Comprehensive test script for WhatsApp Assistant
"""

import requests
import json
import time
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_PHONE = "1234567890"  # Replace with your test phone number

class AssistantTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.test_results = []
    
    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_health_check(self):
        """Test basic health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False
    
    def test_status_endpoint(self):
        """Test system status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=10)
            if response.status_code == 200:
                status = response.json()
                self.log_test("Status Endpoint", True, "System status retrieved")
                
                # Check individual components
                whatsapp_ok = status.get('whatsapp', {}).get('configured', False)
                gmail_ok = status.get('gmail', {}).get('authenticated', False)
                calendar_ok = status.get('calendar', {}).get('authenticated', False)
                
                print(f"  📱 WhatsApp: {'✅' if whatsapp_ok else '❌'}")
                print(f"  📧 Gmail: {'✅' if gmail_ok else '❌'}")
                print(f"  📅 Calendar: {'✅' if calendar_ok else '❌'}")
                
                return True
            else:
                self.log_test("Status Endpoint", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Status Endpoint", False, f"Error: {str(e)}")
            return False
    
    def test_whatsapp_webhook(self):
        """Test WhatsApp webhook with sample message"""
        webhook_data = {
            "id": f"test_msg_{int(time.time())}",
            "from": TEST_PHONE,
            "to": "your_whatsapp_number",  # Replace with your actual number
            "body": "/status",
            "type": "text",
            "timestamp": str(int(time.time())),
            "is_from_me": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/whatsapp-webhook",
                json=webhook_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("WhatsApp Webhook", True, f"Response: {result.get('status', 'unknown')}")
                return True
            else:
                self.log_test("WhatsApp Webhook", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("WhatsApp Webhook", False, f"Error: {str(e)}")
            return False
    
    def test_command_endpoint(self):
        """Test command endpoint for direct testing"""
        commands = [
            "/status",
            "/help",
            "/emails",
            "/calendar"
        ]
        
        success_count = 0
        for cmd in commands:
            try:
                command_data = {
                    "command": cmd,
                    "parameters": {},
                    "user_phone": TEST_PHONE
                }
                
                response = requests.post(
                    f"{self.base_url}/command",
                    json=command_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success', False):
                        success_count += 1
                        print(f"  ✅ Command '{cmd}': {result.get('message', 'OK')}")
                    else:
                        print(f"  ⚠️  Command '{cmd}': {result.get('error', 'Unknown error')}")
                else:
                    print(f"  ❌ Command '{cmd}': HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Command '{cmd}': {str(e)}")
        
        self.log_test("Command Endpoint", success_count > 0, f"{success_count}/{len(commands)} commands successful")
        return success_count > 0
    
    def test_ai_components(self):
        """Test AI components if available"""
        try:
            # Test if we can import the AI modules
            import sys
            sys.path.append('src')
            
            from ai.responder import EmailResponder
            from ai.summarizer import EmailSummarizer
            
            responder = EmailResponder()
            summarizer = EmailSummarizer()
            
            responder_status = responder.get_status()
            summarizer_status = summarizer.get_status()
            
            responder_ok = responder_status.get('available', False) and responder_status.get('api_key_set', False)
            summarizer_ok = summarizer_status.get('available', False) and summarizer_status.get('api_key_set', False)
            
            self.log_test("AI Responder", responder_ok, f"Available: {responder_ok}")
            self.log_test("AI Summarizer", summarizer_ok, f"Available: {summarizer_ok}")
            
            return responder_ok and summarizer_ok
            
        except Exception as e:
            self.log_test("AI Components", False, f"Error: {str(e)}")
            return False
    
    def test_environment_setup(self):
        """Test environment configuration"""
        required_vars = [
            "OPENAI_API_KEY",
            "ULTRAMSG_API_URL",
            "ULTRAMSG_INSTANCE_ID",
            "ULTRAMSG_TOKEN",
            "MY_PHONE_NUMBER"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.log_test("Environment Setup", False, f"Missing variables: {', '.join(missing_vars)}")
            return False
        else:
            self.log_test("Environment Setup", True, "All required environment variables set")
            return True
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🧪 Starting WhatsApp Assistant Tests")
        print("=" * 60)
        
        tests = [
            ("Environment Setup", self.test_environment_setup),
            ("Health Check", self.test_health_check),
            ("Status Endpoint", self.test_status_endpoint),
            ("WhatsApp Webhook", self.test_whatsapp_webhook),
            ("Command Endpoint", self.test_command_endpoint),
            ("AI Components", self.test_ai_components)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
        
        print(f"\n📊 Test Results Summary")
        print("=" * 60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! Your assistant is ready to go!")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the output above for details.")
            print("\n💡 Common fixes:")
            print("   - Make sure the server is running: python app_enhanced.py")
            print("   - Check your .env file has all required variables")
            print("   - Verify your API keys are valid")
        
        return passed == total

def main():
    """Main test runner"""
    tester = AssistantTester()
    success = tester.run_all_tests()
    
    # Save test results
    with open('test_results.json', 'w') as f:
        json.dump(tester.test_results, f, indent=2)
    
    print(f"\n📄 Test results saved to test_results.json")
    return success

if __name__ == "__main__":
    main()


