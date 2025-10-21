# 📅 Google Calendar Authentication Setup

This guide will help you set up Google Calendar authentication for your WhatsApp assistant.

## 🚀 Quick Start

### 1. Run the Authentication Server

```bash
python run_auth.py
```

This will start a web server at `http://localhost:5000`

### 2. Open the Authentication UI

Open your browser and go to: **http://localhost:5000**

## 📋 Step-by-Step Process

### Step 1: Get Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Choose **Desktop Application** as the application type
6. Download the credentials JSON file

### Step 2: Use the Authentication UI

1. **Upload Credentials**: Upload the JSON file you downloaded
2. **Authenticate**: Click "Authenticate with Google"
3. **Complete OAuth**: Follow the Google authentication flow
4. **Copy Tokens**: Copy the generated tokens to your environment variables

### Step 3: Set Environment Variables

Copy the generated values to your environment:

```bash
# In your .env file or environment variables
CALENDAR_CREDENTIALS_JSON='{"installed":{"client_id":"...","client_secret":"..."}}'
CALENDAR_TOKEN_JSON='{"token":"ya29.a0AQQ_BDQhW9_XajH64CocTie0Pit90YAmP-voWWonhoCQCTVDIID+CDV7...","refresh_token":"1//04...","token_uri":"https://oauth2.googleapis.com/token","client_id":"...","client_secret":"...","scopes":["https://www.googleapis.com/auth/calendar"],"expiry":"2024-01-15T10:30:00Z"}'
```

## 🔧 Manual Setup (Alternative)

If the UI doesn't work, you can set up authentication manually:

### 1. Install Dependencies

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

### 2. Create Credentials File

Create `credentials/calendar_credentials.json` with your Google Cloud credentials:

```json
{
  "installed": {
    "client_id": "your-client-id.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your-client-secret",
    "redirect_uris": ["http://localhost"]
  }
}
```

### 3. Run Authentication Script

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials/calendar_credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    print("Credentials JSON:")
    print(creds.to_json())
    
    return creds

if __name__ == '__main__':
    authenticate()
```

## 🧪 Testing the Integration

After setting up authentication, test the calendar integration:

```bash
# Test the calendar integration
python -c "
from src.integrations.calendar import CalendarIntegration
calendar = CalendarIntegration()
print('Calendar Status:', calendar.get_status())
"
```

## 🔍 Troubleshooting

### Common Issues:

1. **"Invalid credentials"**: Token expired, need to refresh or re-authenticate
2. **"Invalid scope"**: Wrong scopes in token, need to re-authenticate with correct scopes
3. **"File not found"**: Credentials file path is incorrect

### Solutions:

1. **Re-authenticate**: Use the authentication UI to get fresh tokens
2. **Check scopes**: Ensure your token has calendar scopes
3. **Verify files**: Check that credential files exist and are valid JSON

## 📱 Using the Calendar Integration

Once authenticated, you can use these commands in WhatsApp:

- `/calendar` - View calendar summary
- `/events` - List upcoming events
- `/create` - Create a new event
- `/delete` - Delete an event
- `/edit` - Edit an event

## 🔒 Security Notes

- Keep your credentials secure
- Don't commit credentials to version control
- Use environment variables for production
- Tokens expire and need periodic refresh

## 🆘 Need Help?

If you encounter issues:

1. Check the logs for specific error messages
2. Verify your Google Cloud Console setup
3. Ensure all required APIs are enabled
4. Check that your OAuth2 credentials are correct
