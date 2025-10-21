#!/usr/bin/env python3
"""
Google Calendar Authentication Helper
Provides a simple web interface to authenticate and get calendar tokens
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar OAuth2 configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendar Authentication</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #0056b3; }
        .code { background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace; word-break: break-all; }
        .step { margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; background: white; }
    </style>
</head>
<body>
    <h1>📅 Google Calendar Authentication</h1>
    
    {% if message %}
    <div class="container {{ message_type }}">
        <h3>{{ message_title }}</h3>
        <p>{{ message }}</p>
    </div>
    {% endif %}
    
    <div class="step">
        <h3>Step 1: Upload Credentials File</h3>
        <p>Upload your Google Cloud Console credentials JSON file:</p>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="credentials_file" accept=".json" required>
            <button type="submit" name="action" value="upload">Upload Credentials</button>
        </form>
    </div>
    
    {% if credentials_uploaded %}
    <div class="step">
        <h3>Step 2: Authenticate with Google</h3>
        <p>Click the button below to authenticate with Google Calendar:</p>
        <form method="post">
            <button type="submit" name="action" value="authenticate">🔐 Authenticate with Google</button>
        </form>
    </div>
    {% endif %}
    
    {% if auth_url %}
    <div class="step">
        <h3>Step 3: Complete Authentication</h3>
        <p>Click the link below to complete the authentication process:</p>
        <a href="{{ auth_url }}" target="_blank" style="display: inline-block; background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
            🌐 Open Google Authentication
        </a>
        <p><small>This will open in a new tab. After authentication, you'll get an authorization code.</small></p>
    </div>
    {% endif %}
    
    {% if tokens %}
    <div class="step">
        <h3>✅ Authentication Complete!</h3>
        <p>Your calendar tokens have been generated successfully. Copy these values to your environment variables:</p>
        
        <h4>CALENDAR_CREDENTIALS_JSON:</h4>
        <div class="code">{{ tokens.credentials }}</div>
        
        <h4>CALENDAR_TOKEN_JSON:</h4>
        <div class="code">{{ tokens.token }}</div>
        
        <p><strong>Next steps:</strong></p>
        <ol>
            <li>Copy the values above to your environment variables</li>
            <li>Redeploy your application</li>
            <li>Test the calendar integration</li>
        </ol>
    </div>
    {% endif %}
    
    <div class="step">
        <h3>📋 Manual Authentication (Alternative)</h3>
        <p>If the automatic process doesn't work, you can manually authenticate:</p>
        <ol>
            <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
            <li>Create a new project or select existing one</li>
            <li>Enable Google Calendar API</li>
            <li>Create OAuth2 credentials (Desktop application)</li>
            <li>Download the credentials JSON file</li>
            <li>Use the Google OAuth2 Playground to get tokens</li>
        </ol>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Main authentication page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/', methods=['POST'])
def handle_auth():
    """Handle authentication steps"""
    action = request.form.get('action')
    
    if action == 'upload':
        return handle_credentials_upload()
    elif action == 'authenticate':
        return handle_google_auth()
    else:
        return redirect(url_for('index'))

def handle_credentials_upload():
    """Handle credentials file upload"""
    try:
        if 'credentials_file' not in request.files:
            return render_template_string(HTML_TEMPLATE, 
                message="No file uploaded", 
                message_type="error",
                message_title="Upload Error")
        
        file = request.files['credentials_file']
        if file.filename == '':
            return render_template_string(HTML_TEMPLATE, 
                message="No file selected", 
                message_type="error",
                message_title="Upload Error")
        
        # Save credentials file
        credentials_data = file.read().decode('utf-8')
        credentials_json = json.loads(credentials_data)
        
        # Validate credentials format
        if 'installed' not in credentials_json and 'web' not in credentials_json:
            return render_template_string(HTML_TEMPLATE, 
                message="Invalid credentials format. Please upload a valid Google OAuth2 credentials file.", 
                message_type="error",
                message_title="Invalid File")
        
        # Store credentials in session (in production, use proper session storage)
        app.config['CREDENTIALS_DATA'] = credentials_data
        
        return render_template_string(HTML_TEMPLATE, 
            message="Credentials uploaded successfully! You can now authenticate with Google.", 
            message_type="success",
            message_title="Upload Successful",
            credentials_uploaded=True)
            
    except Exception as e:
        logger.error(f"Error uploading credentials: {str(e)}")
        return render_template_string(HTML_TEMPLATE, 
            message=f"Error processing credentials: {str(e)}", 
            message_type="error",
            message_title="Upload Error")

def handle_google_auth():
    """Handle Google OAuth2 authentication"""
    try:
        if not CALENDAR_AVAILABLE:
            return render_template_string(HTML_TEMPLATE, 
                message="Google Calendar libraries not installed. Please install google-api-python-client and google-auth-oauthlib", 
                message_type="error",
                message_title="Missing Dependencies")
        
        credentials_data = app.config.get('CREDENTIALS_DATA')
        if not credentials_data:
            return render_template_string(HTML_TEMPLATE, 
                message="Please upload credentials file first", 
                message_type="error",
                message_title="No Credentials")
        
        # Create temporary credentials file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(credentials_data)
            credentials_file = f.name
        
        try:
            # Create OAuth2 flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            # Store flow in session for later use
            app.config['OAUTH_FLOW'] = flow
            
            return render_template_string(HTML_TEMPLATE, 
                message="Click the link below to authenticate with Google", 
                message_type="info",
                message_title="Authentication Required",
                auth_url=auth_url)
                
        finally:
            # Clean up temporary file
            os.unlink(credentials_file)
            
    except Exception as e:
        logger.error(f"Error setting up Google auth: {str(e)}")
        return render_template_string(HTML_TEMPLATE, 
            message=f"Error setting up authentication: {str(e)}", 
            message_type="error",
            message_title="Authentication Error")

@app.route('/callback')
def auth_callback():
    """Handle OAuth2 callback"""
    try:
        code = request.args.get('code')
        if not code:
            return render_template_string(HTML_TEMPLATE, 
                message="No authorization code received", 
                message_type="error",
                message_title="Authentication Failed")
        
        flow = app.config.get('OAUTH_FLOW')
        if not flow:
            return render_template_string(HTML_TEMPLATE, 
                message="Authentication session expired. Please start over.", 
                message_type="error",
                message_title="Session Expired")
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Test the credentials
        service = build('calendar', 'v3', credentials=credentials)
        calendar_list = service.calendarList().list().execute()
        
        # Prepare tokens for display
        tokens = {
            'credentials': app.config.get('CREDENTIALS_DATA', '{}'),
            'token': credentials.to_json()
        }
        
        return render_template_string(HTML_TEMPLATE, 
            message="Authentication successful! Your tokens are ready.", 
            message_type="success",
            message_title="✅ Success!",
            tokens=tokens)
            
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}")
        return render_template_string(HTML_TEMPLATE, 
            message=f"Authentication failed: {str(e)}", 
            message_type="error",
            message_title="Authentication Failed")

if __name__ == '__main__':
    print("🔐 Starting Calendar Authentication Server...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("🔧 This will help you set up Google Calendar authentication")
    app.run(debug=True, host='0.0.0.0', port=5000)
