#!/usr/bin/env python3
"""
Google Calendar API Authentication Setup
Run this script to authenticate with Calendar API for the first time
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

def setup_calendar_auth():
    """Set up Calendar API authentication"""
    credentials_file = './credentials/calendar_credentials.json'
    token_file = './credentials/calendar_token.json'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"❌ Calendar credentials file not found: {credentials_file}")
        print("Please download your Calendar API credentials from Google Cloud Console")
        print("and save them as 'calendar_credentials.json' in the credentials/ directory")
        return False
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing Calendar credentials...")
            creds.refresh(Request())
        else:
            print("🔐 Starting Calendar OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Calendar credentials saved to {token_file}")
    
    # Test the connection
    try:
        service = build('calendar', 'v3', credentials=creds)
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        print(f"✅ Calendar API connected successfully!")
        print(f"📅 Found {len(calendars)} calendars:")
        for calendar in calendars[:3]:  # Show first 3 calendars
            print(f"   - {calendar.get('summary', 'Unknown')}")
        if len(calendars) > 3:
            print(f"   ... and {len(calendars) - 3} more")
        return True
    except Exception as e:
        print(f"❌ Error testing Calendar API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Calendar API authentication...")
    success = setup_calendar_auth()
    if success:
        print("🎉 Calendar setup complete! You can now use calendar features.")
    else:
        print("❌ Calendar setup failed. Please check the error messages above.")


