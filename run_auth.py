#!/usr/bin/env python3
"""
Run the Calendar Authentication Server
This provides a web UI to set up Google Calendar authentication
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from auth_calendar import app
    print("🔐 Calendar Authentication Server")
    print("=" * 50)
    print("📱 Open your browser and go to: http://localhost:5001")
    print("🔧 This will help you set up Google Calendar authentication")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
except ImportError as e:
    print(f"❌ Error importing authentication server: {e}")
    print("💡 Make sure Flask is installed: pip install flask")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting authentication server: {e}")
    sys.exit(1)
