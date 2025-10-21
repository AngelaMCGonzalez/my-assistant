"""
Main Message Router
Handles message flow and coordinates all integrations
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.integrations.whatsapp import WhatsAppIntegration
# from src.integrations.gmail import GmailIntegration
# from src.integrations.calendar import CalendarIntegration
from src.core.hitl import HITLManager
# from src.ai.summarizer import EmailSummarizer
# from src.ai.responder import EmailResponder
from src.ai.conversation import ConversationAI

logger = logging.getLogger(__name__)

class MessageRouter:
    """Main router that coordinates all integrations and handles message flow"""
    
    def __init__(self, whatsapp: WhatsAppIntegration, gmail=None, 
                 calendar=None, hitl_manager: HITLManager=None):
        self.whatsapp = whatsapp
        # self.gmail = gmail
        # self.calendar = calendar
        self.hitl_manager = hitl_manager
        
        # Initialize AI components
        # self.summarizer = EmailSummarizer()
        # self.responder = EmailResponder(calendar_integration=calendar)
        self.conversation_ai = ConversationAI()
        
        # Configuration
        self.my_phone_number = whatsapp.my_phone_number
        self.auto_check_emails = False  # Disabled to prevent automatic messages
        self.email_check_interval = 60  # 1 minute
        
        # Track sent emails for reply detection
        self.sent_emails = {}  # thread_id -> email_info
        self._load_sent_emails()
        
        # Track recent messages to prevent loops
        self.recent_messages = {}  # phone -> [messages]
        self.max_recent_messages = 5
        self.processed_messages = set()  # Track processed message IDs
        self.last_response_time = {}  # phone -> timestamp
        self.response_cooldown = 5  # seconds between responses to same phone
        
        # Background tasks will be started when the event loop is running
        self._background_task = None
    
    def _load_sent_emails(self):
        """Load sent emails tracking from file"""
        try:
            import json
            import os
            
            sent_emails_file = "data/sent_emails.json"
            if os.path.exists(sent_emails_file):
                with open(sent_emails_file, 'r') as f:
                    self.sent_emails = json.load(f)
                logger.info(f"Loaded {len(self.sent_emails)} tracked emails")
            else:
                logger.info("No sent emails file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading sent emails: {str(e)}")
            self.sent_emails = {}
    
    def _save_sent_emails(self):
        """Save sent emails tracking to file"""
        try:
            import json
            import os
            
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
            
            sent_emails_file = "data/sent_emails.json"
            with open(sent_emails_file, 'w') as f:
                json.dump(self.sent_emails, f, indent=2)
            logger.info(f"Saved {len(self.sent_emails)} tracked emails")
        except Exception as e:
            logger.error(f"Error saving sent emails: {str(e)}")
    
    def start_background_tasks(self):
        """Start background tasks when event loop is available"""
        # Don't start background tasks here - they'll be started in the FastAPI startup event
        pass
    
    async def start_background_tasks_async(self):
        """Start background tasks when event loop is running"""
        if self.auto_check_emails and self._background_task is None:
            self._background_task = asyncio.create_task(self._email_monitoring_loop())
            logger.info("Background email monitoring started")
        else:
            logger.info("Background email monitoring disabled (auto_check_emails=False)")
    
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
        
        # Skip if message is empty or just acknowledgments
        if not message or len(message) < 2:
            logger.info("Skipping empty or very short message")
            return {"status": "skipped", "message": "Empty message"}
        
        # Skip if this is a message from the assistant itself (prevent loops)
        if message_data.get("fromMe", False) or message_data.get("is_from_me", False):
            logger.info("Skipping message from assistant itself")
            return {"status": "skipped", "message": "Message from assistant"}
        
        # Skip if this is an acknowledgment message
        if any(ack_word in message.lower() for ack_word in ["sent", "delivered", "read", "ok", "true"]):
            logger.info("Skipping acknowledgment message")
            return {"status": "skipped", "message": "Acknowledgment message"}
        
        # Skip if message contains assistant's own responses (prevent loops)
        assistant_responses = [
            "¡claro! puedo platicar contigo sobre cualquier tema",
            "puedo platicar contigo sobre cualquier tema",
            "lo siento, estoy teniendo problemas para procesar tu mensaje",
            "entiendo que dijiste",
            "estoy aquí para ayudarte"
        ]
        if any(response in message.lower() for response in assistant_responses):
            logger.info("Skipping message containing assistant response")
            return {"status": "skipped", "message": "Contains assistant response"}
        
        # Skip if this is a webhook event for message creation/acknowledgment
        event_type = message_data.get("event_type", "")
        if event_type in ["message_ack", "message_create", "message_sent"]:
            logger.info(f"Skipping webhook event: {event_type}")
            return {"status": "skipped", "message": f"Webhook event: {event_type}"}
        
        # Skip if we've already processed this message
        message_id = message_data.get("message_id") or message_data.get("id")
        if message_id and message_id in self.processed_messages:
            logger.info(f"Skipping already processed message: {message_id}")
            return {"status": "skipped", "message": "Already processed"}
        
        # Mark this message as processed
        if message_id:
            self.processed_messages.add(message_id)
            # Keep only last 100 processed message IDs to prevent memory issues
            if len(self.processed_messages) > 100:
                self.processed_messages = set(list(self.processed_messages)[-50:])
        
        # Rate limiting - prevent rapid-fire responses
        current_time = datetime.now().timestamp()
        if from_phone in self.last_response_time:
            time_since_last = current_time - self.last_response_time[from_phone]
            if time_since_last < self.response_cooldown:
                logger.info(f"Rate limiting: {time_since_last:.1f}s since last response to {from_phone}")
                return {"status": "rate_limited", "message": "Too soon since last response"}
        
        # Update last response time
        self.last_response_time[from_phone] = current_time
        
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
        
        # Check if there are any pending HITL actions that need user response
        pending_actions = self.hitl_manager.get_pending_actions()
        if pending_actions:
            # If there are pending actions, only respond to approval/rejection responses
            if any(word in message.lower() for word in ["✅", "❌", "sí", "no", "yes", "no", "aprobar", "rechazar"]):
                # This might be a response to a pending action, let HITL handle it
                return {"status": "hitl_processing", "message": "Processing HITL response"}
            else:
                # There are pending actions but this doesn't look like a response
                return {"status": "pending_actions", "message": "Please respond to pending actions first"}
        
        # Only respond to direct questions or requests (Human-in-the-Loop approach)
        question_indicators = [
            "?", "pregunta", "question", "ayuda", "help", "qué", "what", "cómo", "how", 
            "cuándo", "when", "dónde", "where", "por qué", "why", "puedes", "can you"
        ]
        
        if any(indicator in message.lower() for indicator in question_indicators):
            # This looks like a question or request, respond with AI
            return await self._handle_ai_conversation(message, response_phone)
        else:
            # Not a question or request, don't respond automatically
            return {"status": "no_response", "message": "No automatic response needed"}
    
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
        # elif command == "/emails":
        #     return await self._check_and_send_emails(from_phone)
        # elif command == "/allemails":
        #     return await self._check_and_send_all_emails(from_phone)
        # elif command == "/calendar":
        #     return await self._send_calendar_summary(from_phone)
        elif command == "/help":
            return await self._send_help_message(from_phone)
        elif command == "/clear":
            return await self._clear_conversation(from_phone)
        elif command == "/personality":
            return await self._show_personality(from_phone)
        elif command == "/summary":
            return await self._show_conversation_summary(from_phone)
        # elif command == "/autoemails":
        #     return await self._toggle_auto_emails(from_phone)
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
        
        # Check for email sending requests (Spanish and English)
        if any(word in message_lower for word in ["envíame", "enviar", "send", "correo a", "email to"]):
            return await self._handle_send_email_command(message, from_phone)
        elif "check" in message_lower or "new" in message_lower or "revisar" in message_lower:
            return await self._check_and_send_emails(from_phone)
        elif "reply" in message_lower or "responder" in message_lower:
            return await self._handle_reply_command(message, from_phone)
        else:
            # Default response for general messages
            return await self.whatsapp.send_message(
                from_phone, 
                "👋 ¡Hola! Soy tu asistente. Puedes preguntarme sobre:\n\n📧 Correos: 'revisar correos'\n📅 Calendario: 'horarios disponibles'\n📝 Enviar email: 'enviar email a...'\n\n¿En qué puedo ayudarte?"
            )
    
    async def _check_availability_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle availability check command"""
        try:
            # Check if Calendar is authenticated
            calendar_status = self.calendar.get_status()
            if not calendar_status.get("authenticated", False):
                return await self.whatsapp.send_message(
                    from_phone, 
                    "📅 Google Calendar no está configurado. Por favor, configura las credenciales de Calendar primero."
                )
            
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
            # Check if Gmail is authenticated
            gmail_status = self.gmail.get_status()
            if not gmail_status.get("authenticated", False):
                return await self.whatsapp.send_message(
                    from_phone, 
                    "📧 Gmail no está configurado. Por favor, configura las credenciales de Gmail primero."
                )
            
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
    
    async def _handle_send_email_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle send email command"""
        try:
            import re
            
            # Extract email address
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            email_match = re.search(email_pattern, message)
            
            if not email_match:
                return await self.whatsapp.send_message(
                    from_phone, 
                    "❌ No se encontró una dirección de correo válida en el mensaje."
                )
            
            recipient_email = email_match.group(1)
            
            # Generate email content using AI
            email_content = await self._generate_email_content(message, recipient_email)
            
            # Send the email
            result = await self.gmail.send_email(
                to=recipient_email,
                subject=email_content["subject"],
                body=email_content["body"]
            )
            
            if result.get("success"):
                # Track the sent email for reply detection
                thread_id = result.get("thread_id")
                if thread_id:
                    self.sent_emails[thread_id] = {
                        "recipient": recipient_email,
                        "subject": email_content["subject"],
                        "sent_time": asyncio.get_event_loop().time(),
                        "original_request": message
                    }
                    self._save_sent_emails()  # Save to file
                    logger.info(f"Tracking sent email thread: {thread_id} to {recipient_email}")
                
                return await self.whatsapp.send_message(
                    from_phone, 
                    f"✅ Correo enviado exitosamente a {recipient_email}\n\nAsunto: {email_content['subject']}\n\nContenido: {email_content['body'][:100]}..."
                )
            else:
                return await self.whatsapp.send_message(
                    from_phone, 
                    f"❌ Error al enviar el correo: {result.get('error', 'Error desconocido')}"
                )
                
        except Exception as e:
            logger.error(f"Error handling send email command: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al procesar la solicitud de correo: {str(e)}"
            )
    
    async def _generate_email_content(self, message: str, recipient: str) -> Dict[str, str]:
        """Generate email content using AI"""
        try:
            import re
            
            # Extract the actual request content, removing the instruction part
            # Look for patterns like "preguntando si está disponible para una reunión mañana a las 9 a.m."
            meeting_pattern = r'preguntando si está disponible para una reunión (.+?)(?:\.|$)'
            meeting_match = re.search(meeting_pattern, message.lower())
            
            if meeting_match:
                meeting_details = meeting_match.group(1)
                subject = "¿Podemos reunirnos?"
                body = f"""Hola {recipient.split('@')[0]},

¿Cómo estás? Te escribo para ver si podemos reunirnos.

¿Estarías disponible para una reunión {meeting_details}?

Si ese horario no te funciona, dime cuándo te conviene mejor.

¡Gracias!

Saludos"""
            else:
                # For other types of requests, extract the actual content
                # Remove instruction words and extract the core message
                content = message
                # Remove common instruction patterns
                instruction_patterns = [
                    r'envíame un correo a [^ ]+ preguntando',
                    r'send me an email to [^ ]+ asking',
                    r'envía un correo a [^ ]+ preguntando',
                    r'envíame un correo a [^ ]+ diciendo',
                    r'send an email to [^ ]+ saying'
                ]
                
                for pattern in instruction_patterns:
                    content = re.sub(pattern, '', content, flags=re.IGNORECASE)
                
                content = content.strip()
                
                subject = "Hola"
                body = f"""Hola {recipient.split('@')[0]},

{content}

¡Gracias!

Saludos"""
            
            return {
                "subject": subject,
                "body": body
            }
            
        except Exception as e:
            logger.error(f"Error generating email content: {str(e)}")
            return {
                "subject": "Hola",
                "body": f"Hola {recipient.split('@')[0]},\n\n¿Cómo estás?\n\nSaludos"
            }
    
    async def _handle_reply_command(self, message: str, from_phone: str) -> Dict[str, Any]:
        """Handle reply command"""
        return await self.whatsapp.send_message(
            from_phone, 
            "Función de respuesta no implementada aún."
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
    
    async def _process_email_reply(self, email_data: Dict[str, Any], from_phone: str) -> Dict[str, Any]:
        """Process a reply to a tracked email"""
        try:
            thread_id = email_data.get("thread_id")
            sent_email_info = self.sent_emails.get(thread_id, {})
            
            # Summarize the reply
            summary = await self.summarizer.summarize_email(email_data)
            
            # Generate suggested response to the reply
            response = await self.responder.generate_response(email_data, summary)
            
            # Create pending action for reply to the reply
            action_data = {
                "email_id": email_data["id"],
                "thread_id": thread_id,
                "sender": email_data["sender"],
                "subject": email_data["subject"],
                "summary": summary["summary"],
                "suggested_reply": response["response"],
                "original_recipient": sent_email_info.get("recipient", "Unknown"),
                "original_subject": sent_email_info.get("subject", "Unknown")
            }
            
            action = self.hitl_manager.create_pending_action("email_reply", action_data)
            
            # Send notification about the reply
            notification_message = f"""📧 ¡Recibiste una respuesta!

De: {email_data.get('sender', 'Unknown')}
Asunto: {email_data.get('subject', 'No subject')}

Resumen: {summary.get('summary', 'No summary')}

Respuesta sugerida: {response.get('response', 'No response')[:200]}...

¿Quieres enviar esta respuesta? Responde ✅ para aprobar o ❌ para rechazar."""
            
            await self.whatsapp.send_message(from_phone, notification_message)
            
            logger.info(f"Processed email reply from {email_data.get('sender')} in thread {thread_id}")
            return {"status": "success", "action_created": action.id}
            
        except Exception as e:
            logger.error(f"Error processing email reply: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al procesar la respuesta: {str(e)}"
            )
    
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
            
            # Check for duplicate message to prevent loops
            if self._is_duplicate_message(from_phone, response):
                logger.warning(f"Prevented duplicate calendar summary to {from_phone}")
                return {"status": "blocked", "message": "Duplicate message prevented"}
            
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
                # "gmail": self.gmail.get_status(),
                # "calendar": self.calendar.get_status(),
                "hitl": self.hitl_manager.get_status(),
                "ai": {
                    # "summarizer": self.summarizer.get_status(),
                    # "responder": self.responder.get_status()
                    "conversation": self.conversation_ai.get_status()
                }
            }
            
            response = "🤖 Estado del Sistema\n\n"
            response += f"📱 WhatsApp: {'✅' if status['whatsapp']['configured'] else '❌'}\n"
            response += f"📧 Gmail: ❌ (Deshabilitado)\n"
            response += f"📅 Calendar: ❌ (Deshabilitado)\n"
            response += f"🤖 AI: {'✅' if status['ai']['conversation']['configured'] else '❌'}\n"
            response += f"📬 Auto-emails: ❌ (Deshabilitado)\n"
            response += f"⏳ Acciones Pendientes: {status['hitl']['pending_actions_count']}\n"
            
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
            # Check if we have AI conversation available
            ai_status = self.conversation_ai.get_status()
            
            if ai_status.get("configured", False):
                # Use enhanced conversation AI
                context = "Eres un asistente de WhatsApp inteligente y amigable."
                response = await self.conversation_ai.generate_response(message, context, from_phone)
            else:
                # Fallback to simple pattern matching
                response = await self._handle_simple_conversation(message)
            
            return await self.whatsapp.send_message(from_phone, response)
            
        except Exception as e:
            logger.error(f"Error in AI conversation: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                "Lo siento, estoy teniendo problemas para procesar tu mensaje. ¿Puedo ayudarte con algo más específico?"
            )
    
    async def _handle_simple_conversation(self, message: str) -> str:
        """Handle simple conversation with pattern matching (fallback)"""
        message_lower = message.lower().strip()
        
        # Greeting responses (Spanish and English)
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "hola", "buenos días", "buenas tardes", "buenas noches"]):
            return "¡Hola! 👋 Soy tu asistente de WhatsApp. ¿En qué te puedo ayudar? Puedes preguntarme sobre tus correos, calendario o simplemente platicar."
        
        # Help requests (Spanish and English)
        elif any(word in message_lower for word in ["help", "what can you do", "what do you do", "ayuda", "qué puedes hacer", "qué haces"]):
            return "Te puedo ayudar con:\n📧 Tus correos\n📅 Tu calendario\n💬 Platicar contigo\n\n¡Usa /help para ver todos los comandos!"
        
        # Status questions (Spanish and English)
        elif any(word in message_lower for word in ["how are you", "status", "working", "cómo estás", "estado", "funcionando"]):
            return "¡Todo súper bien! 🤖 Todo está funcionando perfecto. ¿Qué quieres hacer?"
        
        # Email questions (Spanish and English) - DISABLED
        # elif any(word in message_lower for word in ["email", "emails", "mail", "correo", "correos"]):
        #     return "¡Claro! Te puedo ayudar con tus correos. Usa /emails para ver los nuevos o pídeme lo que necesites."
        
        # Calendar questions (Spanish and English) - DISABLED
        # elif any(word in message_lower for word in ["calendar", "schedule", "meeting", "appointment", "calendario", "programar", "reunión", "cita"]):
        #     return "¡Perfecto! Te ayudo con tu calendario. Usa /calendar para ver tu agenda o pídeme que programe algo."
        
        # Time/date questions (Spanish and English)
        elif any(word in message_lower for word in ["time", "date", "today", "tomorrow", "hora", "fecha", "hoy", "mañana"]):
            from datetime import datetime
            now = datetime.now()
            return f"Hoy es {now.strftime('%A, %d de %B de %Y')} y son las {now.strftime('%I:%M %p')}. ¿En qué te ayudo?"
        
        # Thank you responses (Spanish and English)
        elif any(word in message_lower for word in ["thank", "thanks", "appreciate", "gracias", "agradezco"]):
            return "¡De nada! 😊 ¿Necesitas algo más?"
        
        # Default response
        else:
            return f"Entiendo que dijiste: '{message}'\n\n¡Estoy aquí para ayudarte! Puedo platicar contigo y responder preguntas. Usa /help para ver los comandos disponibles."
    
    async def _send_help_message(self, from_phone: str) -> Dict[str, Any]:
        """Send help message to user"""
        help_text = """🤖 Asistente de WhatsApp - Ayuda

Comandos disponibles:
/status - Verificar estado del sistema
/help - Mostrar esta ayuda
/clear - Limpiar historial de conversación
/personality - Ver personalidad de la IA
/summary - Resumen de la conversación

Funciones disponibles:
• Conversación inteligente con IA
• Memoria de conversación
• Personalización automática
• Respuestas contextuales

¡Puedo platicar contigo sobre cualquier tema! 🗣️
"""
        
        return await self.whatsapp.send_message(from_phone, help_text)
    
    async def _clear_conversation(self, from_phone: str) -> Dict[str, Any]:
        """Clear conversation history"""
        try:
            self.conversation_ai.clear_conversation_history()
            return await self.whatsapp.send_message(
                from_phone, 
                "🧹 ¡Conversación limpiada! Empezamos de nuevo."
            )
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al limpiar la conversación: {str(e)}"
            )
    
    async def _show_personality(self, from_phone: str) -> Dict[str, Any]:
        """Show AI personality traits"""
        try:
            personality = self.conversation_ai.personality_traits
            response = f"""🤖 Mi Personalidad:

😊 Tono: {personality['tone']}
📝 Formalidad: {personality['formality']}
😄 Humor: {personality['humor']}
🌍 Idioma: {personality['language']}
📏 Longitud: {personality['response_length']}

¿Te gustaría que cambie algo? ¡Dímelo!"""
            
            return await self.whatsapp.send_message(from_phone, response)
        except Exception as e:
            logger.error(f"Error showing personality: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al mostrar personalidad: {str(e)}"
            )
    
    async def _show_conversation_summary(self, from_phone: str) -> Dict[str, Any]:
        """Show conversation summary"""
        try:
            summary = self.conversation_ai.get_conversation_summary()
            return await self.whatsapp.send_message(from_phone, summary)
        except Exception as e:
            logger.error(f"Error showing conversation summary: {str(e)}")
            return await self.whatsapp.send_message(
                from_phone, 
                f"❌ Error al mostrar resumen: {str(e)}"
            )
    
    async def _toggle_auto_emails(self, from_phone: str) -> Dict[str, Any]:
        """Toggle automatic email checking"""
        self.auto_check_emails = not self.auto_check_emails
        
        if self.auto_check_emails:
            # Start the background task if it's not running
            if self._background_task is None:
                self._background_task = asyncio.create_task(self._email_monitoring_loop())
            message = "✅ Auto-email checking ENABLED. I'll check for new emails every minute."
        else:
            # Stop the background task
            if self._background_task:
                self._background_task.cancel()
                self._background_task = None
            message = "❌ Auto-email checking DISABLED. I'll only check emails when you ask."
        
        return await self.whatsapp.send_message(from_phone, message)
    
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
            # Get the thread_id if available (for replies to tracked emails)
            thread_id = action_data.get("thread_id")
            
            if thread_id:
                # This is a reply to a tracked email - send as a new email in the same thread
                result = await self.gmail.send_email(
                    to=action_data["sender"],
                    subject=action_data["subject"],  # Keep original subject (already has Re:)
                    body=action_data["suggested_reply"]
                )
            else:
                # This is a reply to a regular email - send as new email
                result = await self.gmail.send_email(
                    to=action_data["sender"],
                    subject=f"Re: {action_data['subject']}",
                    body=action_data["suggested_reply"]
                )
            
            if result["success"]:
                # Mark original email as read
                await self.gmail.mark_as_read(action_data["email_id"])
                
                # Send confirmation to user
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"✅ Correo enviado exitosamente a {action_data['sender']}"
                )
                
                return {"status": "success", "message": "Email sent"}
            else:
                await self.whatsapp.send_message(
                    self.my_phone_number,
                    f"❌ Error al enviar el correo: {result.get('error', 'Unknown error')}"
                )
                
                return {"status": "error", "message": result.get("error")}
                
        except Exception as e:
            logger.error(f"Error executing email reply: {str(e)}")
            await self.whatsapp.send_message(
                self.my_phone_number,
                f"❌ Error al procesar la respuesta: {str(e)}"
            )
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
        """Background loop to monitor for new emails and replies"""
        while self.auto_check_emails:  # Exit loop when auto-checking is disabled
            try:
                if self.auto_check_emails:
                    # Check for new emails
                    emails = await self.gmail.get_unread_emails()
                    
                    for email in emails:
                        # Check if this is a reply to a tracked email
                        thread_id = email.get("thread_id")
                        if thread_id and thread_id in self.sent_emails:
                            await self._process_email_reply(email, self.my_phone_number)
                        else:
                            await self._process_new_email(email, self.my_phone_number)
                
                # Wait before next check (only if still enabled)
                if self.auto_check_emails:
                    await asyncio.sleep(self.email_check_interval)
                
            except Exception as e:
                logger.error(f"Error in email monitoring loop: {str(e)}")
                if self.auto_check_emails:
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("Email monitoring loop stopped (auto-checking disabled)")
    
    def _is_duplicate_message(self, phone: str, message: str) -> bool:
        """Check if this is a duplicate message to prevent loops"""
        if phone not in self.recent_messages:
            self.recent_messages[phone] = []
        
        # Check if this exact message was sent recently
        if message in self.recent_messages[phone]:
            logger.warning(f"Duplicate message detected for {phone}, ignoring")
            return True
        
        # Add message to recent messages
        self.recent_messages[phone].append(message)
        
        # Keep only recent messages
        if len(self.recent_messages[phone]) > self.max_recent_messages:
            self.recent_messages[phone] = self.recent_messages[phone][-self.max_recent_messages:]
        
        return False
    
    async def process_new_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new email (called by webhook)"""
        return await self._process_new_email(email_data, self.my_phone_number)
    
    async def process_calendar_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a calendar event (called by webhook)"""
        # Handle calendar event notifications
        logger.info(f"Calendar event processed: {event_data}")
        return {"status": "success", "message": "Calendar event processed"}

