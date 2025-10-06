"""
Gmail Integration using Gmail API
Handles reading emails, sending replies, and monitoring new messages
"""

import os
import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logging.warning("Gmail API libraries not installed. Please install google-api-python-client and google-auth-oauthlib")

logger = logging.getLogger(__name__)

class GmailIntegration:
    def __init__(self):
        self.service = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly', 
                      'https://www.googleapis.com/auth/gmail.send',
                      'https://www.googleapis.com/auth/gmail.modify']
        
        if GMAIL_AVAILABLE:
            self._authenticate()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the Gmail integration"""
        return {
            "available": GMAIL_AVAILABLE,
            "authenticated": self.service is not None,
            "scopes": self.scopes
        }
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        try:
            creds = None
            token_file = 'token.json'
            
            # Load existing credentials
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
            # If there are no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', './credentials/gmail_credentials.json')
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API authenticated successfully")
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {str(e)}")
            self.service = None
    
    async def get_recent_emails(self, max_results: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """
        Get recent emails from Gmail
        
        Args:
            max_results: Maximum number of emails to retrieve
            query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
            
        Returns:
            List of email data
        """
        if not self.service:
            logger.error("Gmail service not available")
            return []
        
        try:
            # Get list of messages
            results = self.service.users().messages().list(
                userId='me', 
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = await self.get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    async def get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific email
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Email details or None if error
        """
        if not self.service:
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            email_data = {
                'id': message_id,
                'thread_id': message['threadId'],
                'snippet': message.get('snippet', ''),
                'date': None,
                'subject': '',
                'sender': '',
                'recipient': '',
                'body': '',
                'is_read': 'UNREAD' not in message['labelIds'],
                'labels': message['labelIds']
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'date':
                    email_data['date'] = value
                elif name == 'subject':
                    email_data['subject'] = value
                elif name == 'from':
                    email_data['sender'] = value
                elif name == 'to':
                    email_data['recipient'] = value
            
            # Extract body
            email_data['body'] = self._extract_email_body(message['payload'])
            
            return email_data
            
        except HttpError as e:
            logger.error(f"Error fetching email details: {str(e)}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    async def send_email(self, to: str, subject: str, body: str, reply_to_message_id: str = None) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            reply_to_message_id: ID of message to reply to (optional)
            
        Returns:
            Result of the send operation
        """
        if not self.service:
            return {"success": False, "error": "Gmail service not available"}
        
        try:
            # Create message
            message = self._create_message(to, subject, body, reply_to_message_id)
            
            # Send message
            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully: {result['id']}")
            
            return {
                "success": True,
                "message_id": result['id'],
                "thread_id": result['threadId']
            }
            
        except HttpError as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_message(self, to: str, subject: str, body: str, reply_to_message_id: str = None) -> Dict[str, Any]:
        """Create a Gmail message"""
        message_text = f"To: {to}\r\n"
        message_text += f"Subject: {subject}\r\n"
        message_text += "Content-Type: text/plain; charset=utf-8\r\n"
        message_text += "\r\n"
        message_text += body
        
        if reply_to_message_id:
            message_text += f"\r\n\r\n---\r\nIn-Reply-To: {reply_to_message_id}"
        
        message_bytes = message_text.encode('utf-8')
        message_b64 = base64.urlsafe_b64encode(message_bytes).decode('utf-8')
        
        message = {
            'raw': message_b64
        }
        
        if reply_to_message_id:
            message['threadId'] = reply_to_message_id
        
        return message
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Error marking email as read: {str(e)}")
            return False
    
    async def add_label(self, message_id: str, label_id: str) -> bool:
        """Add a label to an email"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Error adding label: {str(e)}")
            return False
    
    async def get_unread_emails(self) -> List[Dict[str, Any]]:
        """Get unread emails from specified domain only"""
        domain_filter = os.getenv('EMAIL_DOMAIN_FILTER', '@binara.pro')
        query = f"is:unread from:{domain_filter}"
        return await self.get_recent_emails(query=query)
    
    async def get_all_unread_emails(self) -> List[Dict[str, Any]]:
        """Get all unread emails (no domain filter)"""
        return await self.get_recent_emails(query="is:unread")
    
    async def search_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search emails with a specific query"""
        return await self.get_recent_emails(query=query, max_results=max_results)

