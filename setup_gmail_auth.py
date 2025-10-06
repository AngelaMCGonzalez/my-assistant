#!/usr/bin/env python3
"""
Gmail API Authentication Setup
Run this script to authenticate with Gmail API for the first time
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]

def setup_gmail_auth():
    """Set up Gmail API authentication"""
    credentials_file = './credentials/gmail_credentials.json'
    token_file = './credentials/gmail_token.json'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"❌ Gmail credentials file not found: {credentials_file}")
        print("Please download your Gmail API credentials from Google Cloud Console")
        print("and save them as 'gmail_credentials.json' in the credentials/ directory")
        return False
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If there are no valid credentials, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing Gmail credentials...")
            creds.refresh(Request())
        else:
            print("🔐 Starting Gmail OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Gmail credentials saved to {token_file}")
    
    # Test the connection
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().getProfile(userId='me').execute()
        print(f"✅ Gmail API connected successfully!")
        print(f"📧 Email: {results.get('emailAddress')}")
        print(f"📊 Total messages: {results.get('messagesTotal')}")
        return True
    except Exception as e:
        print(f"❌ Error testing Gmail API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Gmail API authentication...")
    success = setup_gmail_auth()
    if success:
        print("🎉 Gmail setup complete! You can now use email features.")
    else:
        print("❌ Gmail setup failed. Please check the error messages above.")


