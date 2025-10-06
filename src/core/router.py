"""
Main Message Router
Handles message flow and coordinates all integrations
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.integrations.whatsapp import WhatsAppIntegration
from src.integrations.gmail import GmailIntegration
from src.integrations.calendar import CalendarIntegration
from src.core.hitl import HITLManager
from src.ai.summarizer import EmailSummarizer
from src.ai.responder import EmailResponder

logger = logging.getLogger(__name__)

class MessageRouter:
    """Main router that coordinates all integrations and handles message flow"""
    
    def __init__(self, whatsapp: WhatsAppIntegration, gmail: GmailIntegration, 
                 calendar: CalendarIntegration, hitl_manager: HITLManager):
        self.whatsapp = whatsapp
        self.gmail = gmail
        self.calendar = calendar
        self.hitl_manager = hitl_manager
        
        # Initialize AI components
        self.summarizer = EmailSummarizer()
        self.responder = EmailResponder(calendar_integration=calendar)
        
        # Configuration
        self.my_phone_number = whatsapp.my_phone_number
        self.auto_check_emails = True
        self.email_check_interval = 300  # 5 minutes
        
        # Background tasks will be started when the event loop is running
        self._background_task = None
    
    def start_background_tasks(self):
        """Start background tasks when event loop is available"""
        # Don't start background tasks here - they'll be started in the FastAPI startup event
        pass
    
    async def start_background_tasks_async(self):
        """Start background tasks when event loop is running"""
        if self.auto_check_emails and self._background_task is None:
            self._background_task = asyncio.create_task(self._email_monitoring_loop())
            logger.info("Background email monitoring started")
    
    async def process_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming WhatsApp message
        
        Args:
            webhook_data: Raw webhook data from UltraMsg
            
        Returns:
            Processing result
        """
        try:
            # Parse the message
            message_data = self.whatsapp.parse_incoming_message(webhook_data)
            if not message_data:
                return {"status": "error", "message": "Could not parse message"}
            
            # Check if message is from the user or TO UltraMsg
            if message_data.get("is_from_me", False) or message_data.get("is_to_ultramsg", False):
                return await self._handle_user_message(message_data)
            else:
                return await self._handle_external_message(message_data)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_user_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messages from the user (commands and responses)"""
        message = message_data.get("body", "").strip()
        from_phone = message_data.get("from", "")
        to_phone = message_data.get("to", "")
        
        # Debug logging
        logger.info(f"Handling user message from: {from_phone}, to: {to_phone}")
        
        # Determine where to send the response
        if message_data.get("is_to_ultramsg", False):
            # This is a message TO UltraMsg, always send response to your personal number
            response_phone = "5530386114"  # Always send to your personal number
        elif from_phone == "5664087506":  # UltraMsg number
            # This is a message from UltraMsg TO our phone, so send response back to our phone
            response_phone = to_phone  # Send back to our phone number
        else:
            # This is a direct message, send back to sender
            response_phone = from_phone
        
        # Check if this is a response to a pending action
        hitl_result = self.hitl_manager.process_user_response(message, from_phone)
        if hitl_result and hitl_result.get("success"):
            return await self._execute_approved_action(hitl_result)
        
        # Handle commands
        if message.startswith("/"):
            return await self._handle_command(message, response_phone)
        
        # Handle calendar commands
        if any(word in message.lower() for word in ["schedule", "meeting", "appointment", "calendar"]):
            return await self._handle_calendar_command(message, response_phone)
        
        # Handle email commands
        if any(word in message.lower() for word in ["email", "reply", "send"]):
            return await self._handle_email_command(message, response_phone)
        
        # Handle any other message with AI
        return await self._handle_ai_conversation(message, response_phone)
    
    async def _handle_external_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messages from external sources (notifications, etc.)"""
        # For now, just log external messages
        logger.info(f"External message received: {message_data}")
        return {"status": "logged", "message": "External message logged"}
    
    async def _handle_command(self, command: str, from_phone: str) -> Dict[str, Any]:
        """Handle user commands"""
        command = command.lower().strip()
        
        if command == "/status":
            return await self._send_status_message(from_phone)
        elif command == "/emails":
            return await self._check_and_send_emails(from_phone)
        elif command == "/allemails":
            return await self._check_and_send_all_emails(from_phone)
        elif command == "/calendar":
            return await self._send_calendar_summary(from_phone)
        elif command == "/help":
            return await self._send_help_message(from_phone)
        else:
            return await self.whatsapp.send_message(
                from_phone, 
                "Unknown command. Use /help for available commands."
            )
    
    async def _handle_calendar_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle calendar-related commands"""
        message_lower = message.lower()
        
        if "check availability" in message_lower or "free time" in message_lower:
            return await self._check_availability_command(message, from_phone)
        elif "schedule" in message_lower or "book" in message_lower:
            return await self._schedule_meeting_command(message, from_phone)
        else:
            return await self._send_calendar_summary(from_phone)
    
    async def _handle_email_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle email-related commands"""
        message_lower = message.lower()
        
        if "check" in message_lower or "new" in message_lower:
            return await self._check_and_send_emails(from_phone)
        elif "reply" in message_lower:
            return await self._handle_reply_command(message, from_phone)
        else:
            return await self._check_and_send_emails(from_phone)
    
    async def _check_availability_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle availability check command"""
        try:
            # Parse date and time from message
            # This is a simplified parser - you might want to use a more sophisticated one
            import re
            
            # Look for date patterns
            date_patterns = [
                r'tomorrow',
                r'today',
                r'(\d{1,2})/(\d{1,2})',  # MM/DD
                r'(\d{1,2})-(\d{1,2})',  # MM-DD
            ]
            
            # Look for time patterns
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*(am|pm)?',
                r'(\d{1,2})\s*(am|pm)',
            ]
            
            # For now, check availability for the next 7 days
            start_date = datetime.now()
            end_date = start_date + timedelta(days=7)
            
            events = await self.calendar.get_events(start_date, end_date)
            
            # Find free time slots
            free_slots = await self.calendar.find_free_time_slots(
                start_date, 
                duration_minutes=60,
                working_hours=(9, 17)
            )
            
            # Format response
            if free_slots:
                response = "📅 Horarios disponibles:\n\n"
                for i, slot in enumerate(free_slots[:5]):  # Show first 5 slots
                    start_time = datetime.fromisoformat(slot['start'])
                    response += f"{i+1}. {start_time.strftime('%A, %B %d a las %I:%M %p')}\n"
            else:
                response = "📅 No se encontraron horarios libres en los próximos 7 días."
            
            return await self.whatsapp.send_message(from_phone, response)
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al verificar disponibilidad: {str(e)}"
            )
    
    async def _schedule_meeting_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle meeting scheduling command"""
        try:
            # Parse meeting details from message
            # This is simplified - you'd want more sophisticated parsing
            import re
            
            # Extract title
            title_match = re.search(r'"([^"]+)"', message)
            title = title_match.group(1) if title_match else "Meeting"
            
            # Extract time (simplified)
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', message)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                ampm = time_match.group(3)
                
                if ampm and ampm.lower() == 'pm' and hour != 12:
                    hour += 12
                elif ampm and ampm.lower() == 'am' and hour == 12:
                    hour = 0
                
                # Create datetime for today at specified time
                start_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                end_time = start_time + timedelta(hours=1)
                
                # Check availability
                availability = await self.calendar.check_availability(start_time, end_time)
                
                if availability["available"]:
                    # Create pending action for approval
                    action_data = {
                        "title": title,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "description": f"Meeting scheduled via WhatsApp: {message}"
                    }
                    
                    action = self.hitl_manager.create_pending_action("calendar_event", action_data)
                    
                    # Send approval request
                    return await self.whatsapp.send_approval_request(
                        from_phone, 
                        "calendar_event", 
                        action_data
                    )
                else:
                    conflicts = availability.get("conflicts", [])
                    response = f"❌ Horario no disponible. Conflictos:\n"
                    for conflict in conflicts:
                        response += f"- {conflict['title']} a las {conflict['start']}\n"
                    
                    return await self.whatsapp.send_message(from_phone, response)
            else:
                return await self.whatsapp.send_message(
                    from_phone, 
                    "Por favor especifica una hora para la reunión (ej: 'programar reunión a las 2:30pm')"
                )
                
        except Exception as e:
            logger.error(f"Error scheduling meeting: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al programar reunión: {str(e)}"
            )
    
    async def _check_and_send_emails(self, from_phone: str) -> Dict[str, Any]:
        """Check for new emails and send summaries"""
        try:
            # Get unread emails
            emails = await self.gmail.get_unread_emails()
            
            if not emails:
                return await self.whatsapp.send_message(
                    from_phone, 
                    "📧 No hay correos nuevos sin leer."
                )
            
            # Process each email
            for email in emails[:5]:  # Limit to 5 emails
                await self._process_new_email(email, from_phone)
            
            return {"status": "success", "emails_processed": len(emails)}
            
        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al revisar correos: {str(e)}"
            )
    
    async def _check_and_send_all_emails(self, from_phone: str) -> Dict[str, Any]:
        """Check for all unread emails (no domain filter) and send summaries"""
        try:
            # Get all unread emails (no domain filter)
            emails = await self.gmail.get_all_unread_emails()
            
            if not emails:
                return await self.whatsapp.send_message(
                    from_phone, 
                    "📧 No hay correos nuevos sin leer de ningún dominio."
                )
            
            # Process each email
            for email in emails[:5]:  # Limit to 5 emails
                await self._process_new_email(email, from_phone)
            
            return {"status": "success", "emails_processed": len(emails)}
            
        except Exception as e:
            logger.error(f"Error checking all emails: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al revisar todos los correos: {str(e)}"
            )
    
    async def _process_new_email(self, email_data: Dict[str, Any], from_phone: str) -> Dict[str, Any]:
        """Process a new email and send summary to user"""
        try:
            # Summarize email
            summary = await self.summarizer.summarize_email(email_data)
            
            # Generate suggested response
            response = await self.responder.generate_response(email_data, summary)
            
            # Create pending action for email reply
            action_data = {
                "email_id": email_data["id"],
                "sender": email_data["sender"],
                "subject": email_data["subject"],
                "summary": summary["summary"],
                "suggested_reply": response["response"],
                "original_body": email_data["body"]
            }
            
            action = self.hitl_manager.create_pending_action("email_reply", action_data)
            
            # Send approval request
            return await self.whatsapp.send_approval_request(
                from_phone, 
                "email_reply", 
                action_data
            )
            
        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _send_calendar_summary(self, from_phone: str) -> Dict[str, Any]:
        """Send calendar summary to user"""
        try:
            # Get today's events
            today_events = await self.calendar.get_today_events()
            
            # Get upcoming events
            upcoming_events = await self.calendar.get_upcoming_events(days=7)
            
            response = "📅 Resumen del Calendario\n\n"
            
            if today_events:
                response += "Hoy:\n"
                for event in today_events:
                    start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                    response += f"• {start_time.strftime('%I:%M %p')} - {event['title']}\n"
            else:
                response += "Hoy: Sin eventos\n"
            
            response += "\nPróximos (siguientes 7 días):\n"
            for event in upcoming_events[:5]:  # Show first 5
                start_time = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                response += f"• {start_time.strftime('%a %b %d, %I:%M %p')} - {event['title']}\n"
            
            return await self.whatsapp.send_message(from_phone, response)
            
        except Exception as e:
            logger.error(f"Error sending calendar summary: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al obtener el calendario: {str(e)}"
            )
    
    async def _send_status_message(self, from_phone: str) -> Dict[str, Any]:
        """Send system status to user"""
        try:
            status = {
                "whatsapp": self.whatsapp.get_status(),
                "gmail": self.gmail.get_status(),
                "calendar": self.calendar.get_status(),
                "hitl": self.hitl_manager.get_status(),
                "ai": {
                    "summarizer": self.summarizer.get_status(),
                    "responder": self.responder.get_status()
                }
            }
            
            response = "🤖 System Status\n\n"
            response += f"📱 WhatsApp: {'✅' if status['whatsapp']['configured'] else '❌'}\n"
            response += f"📧 Gmail: {'✅' if status['gmail']['authenticated'] else '❌'}\n"
            response += f"📅 Calendar: {'✅' if status['calendar']['authenticated'] else '❌'}\n"
            response += f"🤖 AI: {'✅' if status['ai']['summarizer']['initialized'] else '❌'}\n"
            response += f"⏳ Pending Actions: {status['hitl']['pending_actions_count']}\n"
            
            return await self.whatsapp.send_message(from_phone, response)
            
        except Exception as e:
            logger.error(f"Error sending status: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"Error getting status: {str(e)}"
            )
    
    async def _handle_ai_conversation(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle general conversation using AI"""
        try:
            # Simple AI-like responses for common questions
            message_lower = message.lower().strip()
            
            # Greeting responses
            if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
                response = "Hello! 👋 I'm your WhatsApp assistant. How can I help you today? You can ask me about your emails, calendar, or just chat!"
            
            # Help requests
            elif any(word in message_lower for word in ["help", "what can you do", "what do you do"]):
                response = "I can help you with:\n📧 Email management\n📅 Calendar scheduling\n💬 General conversation\n\nUse /help for specific commands!"
            
            # Status questions
            elif any(word in message_lower for word in ["how are you", "status", "working"]):
                response = "I'm working great! 🤖 All systems are operational. What would you like to do?"
            
            # Email questions
            elif any(word in message_lower for word in ["email", "emails", "mail"]):
                response = "I can help with your emails! Use /emails to check your inbox or ask me to help with specific email tasks."
            
            # Calendar questions
            elif any(word in message_lower for word in ["calendar", "schedule", "meeting", "appointment"]):
                response = "I can help with your calendar! Use /calendar to see your schedule or ask me to book meetings."
            
            # Time/date questions
            elif any(word in message_lower for word in ["time", "date", "today", "tomorrow"]):
                from datetime import datetime
                now = datetime.now()
                response = f"Today is {now.strftime('%A, %B %d, %Y')} and it's {now.strftime('%I:%M %p')}. How can I help you?"
            
            # Thank you responses
            elif any(word in message_lower for word in ["thank", "thanks", "appreciate"]):
                response = "You're welcome! 😊 Is there anything else I can help you with?"
            
            # Default response
            else:
                response = f"I understand you said: '{message}'\n\nI'm here to help! You can ask me about your emails, calendar, or just chat. Use /help for specific commands."
            
            return await self.whatsapp.send_message(from_phone, response)
            
        except Exception as e:
            logger.error(f"Error in AI conversation: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                "Sorry, I'm having trouble processing your message right now. Please try again or use /help for commands."
            )
    
    async def _send_help_message(self, from_phone: str) -> Dict[str, Any]:
        """Send help message to user"""
        help_text = """🤖 Asistente de WhatsApp - Ayuda

Comandos:
/status - Verificar estado del sistema
/emails - Revisar correos nuevos (solo @binara.pro)
/allemails - Revisar todos los correos sin leer
/calendar - Ver resumen del calendario
/help - Mostrar esta ayuda

Calendario:
• "verificar disponibilidad" - Encontrar horarios libres
• "programar reunión a las 2:30pm" - Programar una reunión
• "agendar cita mañana 10am" - Agendar cita

Correo:
• "revisar correos" - Revisar correos nuevos
• "responder a [correo]" - Responder a correo específico

Respuestas:
✅ - Aprobar acción
❌ - Rechazar acción
"""
        
        return await self.whatsapp.send_message(from_phone, help_text)
    
    async def _execute_approved_action(self, hitl_result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an approved action"""
        try:
            action_type = hitl_result.get("action_type")
            action_data = hitl_result.get("data", {})
            
            if action_type == "email_reply":
                return await self._execute_email_reply(action_data)
            elif action_type == "calendar_event":
                return await self._execute_calendar_event(action_data)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return {"status": "error", "message": "Unknown action type"}
                
        except Exception as e:
            logger.error(f"Error executing approved action: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_email_reply(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email reply action"""
        try:
            # Send the email
            result = await self.gmail.send_email(
                to=action_data["sender"],
                subject=f"Re: {action_data['subject']}",
                body=action_data["suggested_reply"],
                reply_to_message_id=action_data["email_id"]
            )
            
            if result["success"]:
                # Mark original email as read
                await self.gmail.mark_as_read(action_data["email_id"])
                
                # Send confirmation to user
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"✅ Email sent successfully to {action_data['sender']}"
                )
                
                return {"status": "success", "message": "Email sent"}
            else:
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"❌ Failed to send email: {result.get('error', 'Unknown error')}"
                )
                
                return {"status": "error", "message": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error executing email reply: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _execute_calendar_event(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calendar event creation"""
        try:
            # Parse times
            start_time = datetime.fromisoformat(action_data["start_time"])
            end_time = datetime.fromisoformat(action_data["end_time"])
            
            # Create event
            result = await self.calendar.create_event(
                title=action_data["title"],
                start_time=start_time,
                end_time=end_time,
                description=action_data.get("description", "")
            )
            
            if result["success"]:
                # Send confirmation to user
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"✅ Calendar event created: {action_data['title']} at {start_time.strftime('%I:%M %p')}"
                )
                
                return {"status": "success", "message": "Event created"}
            else:
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"❌ Failed to create event: {result.get('error', 'Unknown error')}"
                )
                
                return {"status": "error", "message": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error executing calendar event: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _email_monitoring_loop(self):
        """Background loop to monitor for new emails"""
        while True:
            try:
                if self.auto_check_emails:
                    # Check for new emails
                    emails = await self.gmail.get_unread_emails()
                    
                    for email in emails:
                        await self._process_new_email(email, self.my_phone_number)
                
                # Wait before next check
                await asyncio.sleep(self.email_check_interval)
                
            except Exception as e:
                logger.error(f"Error in email monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def process_new_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new email (called by webhook)"""
        return await self._process_new_email(email_data, self.my_phone_number)
    
    async def process_calendar_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a calendar event (called by webhook)"""
        # Handle calendar event notifications
        logger.info(f"Calendar event processed: {event_data}")
        return {"status": "success", "message": "Calendar event processed"}

