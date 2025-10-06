"""
WhatsApp Integration using UltraMsg API
Handles sending and receiving WhatsApp messages
"""

import requests
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class WhatsAppIntegration:
    def __init__(self):
        self.api_url = os.getenv("ULTRAMSG_API_URL", "https://api.ultramsg.com")
        self.instance_id = os.getenv("ULTRAMSG_INSTANCE_ID")
        self.token = os.getenv("ULTRAMSG_TOKEN")
        self.my_phone_number = os.getenv("MY_PHONE_NUMBER")  # Your WhatsApp number
        
        # Build the correct API URL
        if self.api_url and self.instance_id:
            # If the API URL already contains the instance ID, use it as is
            if self.instance_id in self.api_url:
                pass  # URL already contains instance ID
            elif self.api_url.endswith('/'):
                self.api_url = f"{self.api_url}{self.instance_id}/"
            else:
                self.api_url = f"{self.api_url}/{self.instance_id}/"
        
        # Debug logging
        logger.info(f"Environment variables loaded:")
        logger.info(f"  ULTRAMSG_API_URL: {self.api_url}")
        logger.info(f"  ULTRAMSG_INSTANCE_ID: {self.instance_id}")
        logger.info(f"  ULTRAMSG_TOKEN: {'***' if self.token else None}")
        logger.info(f"  MY_PHONE_NUMBER: {self.my_phone_number}")
        
        if not all([self.api_url, self.instance_id, self.token, self.my_phone_number]):
            logger.warning("WhatsApp integration not fully configured. Please set environment variables.")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the WhatsApp integration"""
        return {
            "configured": bool(self.instance_id and self.token),
            "api_url": self.api_url,
            "instance_id": self.instance_id,
            "my_phone_number": self.my_phone_number
        }
    
    async def send_message(self, to: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """
        Send a WhatsApp message
        
        Args:
            to: Recipient phone number (with country code, no +)
            message: Message content
            message_type: Type of message (text, image, document, etc.)
        """
        try:
            url = f"{self.api_url}messages/chat"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "token": self.token,
                "to": to,
                "body": message,
                "type": message_type
            }
            
            logger.info(f"Sending WhatsApp message to URL: {url}")
            logger.info(f"Request data: {data}")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Message sent successfully to {to}: {result}")
            
            return {
                "success": True,
                "message_id": result.get("id"),
                "response": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_media_message(self, to: str, media_url: str, caption: str = "", message_type: str = "image") -> Dict[str, Any]:
        """
        Send a media message (image, document, etc.)
        
        Args:
            to: Recipient phone number
            media_url: URL of the media file
            caption: Caption for the media
            message_type: Type of media (image, document, audio, video)
        """
        try:
            url = f"{self.api_url}messages/chat"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "token": self.token,
                "to": to,
                "media": media_url,
                "type": message_type,
                "caption": caption
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Media message sent successfully to {to}: {result}")
            
            return {
                "success": True,
                "message_id": result.get("id"),
                "response": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp media message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_incoming_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook data from UltraMsg
        
        Args:
            webhook_data: Raw webhook data from UltraMsg
            
        Returns:
            Parsed message data or None if not a valid message
        """
        try:
            # UltraMsg webhook structure may vary, adjust based on actual format
            if "data" in webhook_data:
                message_data = webhook_data["data"]
            else:
                message_data = webhook_data
            
            # Extract message information
            from_number = message_data.get("from")
            to_number = message_data.get("to")
            
            # Debug logging
            logger.info(f"Received message - From: {from_number}, To: {to_number}, My number: {self.my_phone_number}")
            
            message_info = {
                "message_id": message_data.get("id"),
                "from": from_number,
                "to": to_number,
                "body": message_data.get("body", ""),
                "type": message_data.get("type", "text"),
                "timestamp": message_data.get("timestamp"),
                "is_from_me": to_number == self.my_phone_number,
                "is_to_ultramsg": to_number == "5664087506",  # Messages TO UltraMsg
                "raw_data": message_data
            }
            
            logger.info(f"Message parsed - is_from_me: {message_info['is_from_me']}")
            
            # Handle different message types
            if message_info["type"] == "image":
                message_info["media_url"] = message_data.get("media")
            elif message_info["type"] == "document":
                message_info["media_url"] = message_data.get("media")
                message_info["filename"] = message_data.get("filename")
            
            return message_info
            
        except Exception as e:
            logger.error(f"Error parsing incoming message: {str(e)}")
            return None
    
    async def send_approval_request(self, to: str, action_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a human-in-the-loop approval request
        
        Args:
            to: Recipient phone number
            action_type: Type of action (email_reply, calendar_event, etc.)
            details: Details about the action
        """
        try:
            if action_type == "email_reply":
                message = self._format_email_approval_request(details)
            elif action_type == "calendar_event":
                message = self._format_calendar_approval_request(details)
            else:
                message = f"🤖 Action required: {action_type}\n\n{json.dumps(details, indent=2)}\n\nApprove? ✅/❌"
            
            return await self.send_message(to, message)
            
        except Exception as e:
            logger.error(f"Error sending approval request: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _format_email_approval_request(self, details: Dict[str, Any]) -> str:
        """Format email approval request message"""
        sender = details.get("sender", "Unknown")
        subject = details.get("subject", "No subject")
        summary = details.get("summary", "No summary available")
        suggested_reply = details.get("suggested_reply", "No suggested reply")
        
        message = f"""📧 Nuevo correo de {sender}
📋 Asunto: {subject}

📝 Resumen: {summary}

💬 Respuesta sugerida:
{suggested_reply}

¿Enviar? ✅/❌"""
        
        return message
    
    def _format_calendar_approval_request(self, details: Dict[str, Any]) -> str:
        """Format calendar approval request message"""
        event_title = details.get("title", "New Event")
        start_time = details.get("start_time", "Unknown time")
        duration = details.get("duration", "Unknown duration")
        attendees = details.get("attendees", [])
        
        message = f"""📅 Calendar Event Request
📋 Title: {event_title}
⏰ Time: {start_time}
⏱️ Duration: {duration}"""
        
        if attendees:
            message += f"\n👥 Attendees: {', '.join(attendees)}"
        
        message += "\n\nCreate event? ✅/❌"
        
        return message
    
    def is_approval_response(self, message: str) -> Optional[str]:
        """
        Check if a message is an approval response
        
        Args:
            message: Message text
            
        Returns:
            'approve' if approved, 'reject' if rejected, None if not an approval response
        """
        message = message.strip().lower()
        
        if any(approval in message for approval in ["✅", "yes", "y", "approve", "ok", "sí", "si"]):
            return "approve"
        elif any(rejection in message for rejection in ["❌", "no", "n", "reject", "cancel", "no"]):
            return "reject"
        
        return None

