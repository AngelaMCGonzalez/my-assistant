"""
AI Email Response Generator using LangChain and OpenAI
Handles generating suggested email responses based on user style and context
"""

import os
import logging
from typing import Dict, Any, Optional, List
import json

try:
    from langchain_openai import OpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain_core.output_parsers import BaseOutputParser
    from langchain_community.callbacks.manager import get_openai_callback
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("LangChain not installed. Please install langchain and openai")

logger = logging.getLogger(__name__)

class ResponseOutputParser(BaseOutputParser):
    """Custom parser for response generation output"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse the LLM output into structured response data"""
        try:
            # Try to parse as JSON first (fallback for old format)
            if text.strip().startswith('{'):
                return json.loads(text)
            
            # For the new simple format, the entire text is the response
            response_data = {
                "response": text.strip(),
                "tone": "professional",
                "confidence": "high",
                "suggestions": []
            }
            
            # Try to extract structured data if present
            lines = text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Handle Spanish format
                if line.lower().startswith("respuesta:"):
                    response_data["response"] = line[10:].strip()
                elif line.lower().startswith("tono:"):
                    response_data["tone"] = line[5:].strip().lower()
                elif line.lower().startswith("confianza:"):
                    response_data["confidence"] = line[9:].strip().lower()
                # Fallback for English format
                elif line.lower().startswith("response:"):
                    response_data["response"] = line[9:].strip()
                elif line.lower().startswith("tone:"):
                    response_data["tone"] = line[5:].strip().lower()
                elif line.lower().startswith("confidence:"):
                    response_data["confidence"] = line[10:].strip().lower()
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error parsing response output: {str(e)}")
            return {
                "response": text,
                "tone": "professional",
                "confidence": "medium",
                "suggestions": []
            }

class EmailResponder:
    def __init__(self, calendar_integration=None):
        self.llm = None
        self.response_chain = None
        self.rewrite_chain = None
        self.user_style = self._load_user_style()
        self.calendar = calendar_integration
        
        if LANGCHAIN_AVAILABLE:
            self._initialize_llm()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the responder"""
        return {
            "available": LANGCHAIN_AVAILABLE,
            "initialized": self.llm is not None,
            "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
            "user_style_loaded": bool(self.user_style)
        }
    
    def _load_user_style(self) -> Dict[str, Any]:
        """Load user's writing style preferences"""
        try:
            style_file = "user_style.json"
            if os.path.exists(style_file):
                with open(style_file, 'r') as f:
                    return json.load(f)
            else:
                # Default style
                return {
                    "tone": "professional",
                    "formality": "medium",
                    "length_preference": "medium",
                    "greeting_style": "Hi",
                    "closing_style": "Best regards",
                    "common_phrases": [],
                    "avoid_phrases": [],
                    "signature": ""
                }
        except Exception as e:
            logger.error(f"Error loading user style: {str(e)}")
            return {}
    
    def _initialize_llm(self):
        """Initialize the OpenAI LLM"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set")
                return
            
            self.llm = OpenAI(
                temperature=0.7,
                max_tokens=1200,
                openai_api_key=api_key
            )
            
            # Create response generation prompt template
            response_template = """
            Eres un asistente que responde correos electrónicos. Responde SOLO con el texto del correo, sin explicaciones adicionales.

            Correo a responder:
            De: {sender}
            Asunto: {subject}
            Contenido: {content}
            
            Resumen: {summary}
            
            Escribe una respuesta profesional en español que incluya:
            - Saludo apropiado
            - Respuesta al contenido del correo
            - Despedida profesional
            
            Respuesta:"""
            
            response_prompt = PromptTemplate(
                input_variables=["sender", "subject", "content", "summary"],
                template=response_template
            )
            
            self.response_chain = LLMChain(
                llm=self.llm,
                prompt=response_prompt,
                output_parser=ResponseOutputParser()
            )
            
            # Create rewrite prompt template
            rewrite_template = """
            Reescribe la siguiente respuesta de correo electrónico según las preferencias de estilo del usuario:
            
            Respuesta Original:
            {original_response}
            
            Estilo del Usuario:
            - Tono: {tone}
            - Formalidad: {formality}
            - Longitud: {length_preference}
            - Saludo: {greeting_style}
            - Despedida: {closing_style}
            - Frases comunes: {common_phrases}
            - Evitar frases: {avoid_phrases}
            
            Instrucciones:
            1. Mantén el mensaje central pero ajusta el tono y estilo
            2. Usa el saludo y despedida preferidos del usuario
            3. Incorpora frases comunes si es apropiado
            4. Evita frases que al usuario no le gustan
            5. Ajusta el nivel de formalidad según se solicite
            
            Devuelve solo el texto de la respuesta reescrita en español.
            """
            
            rewrite_prompt = PromptTemplate(
                input_variables=["original_response", "tone", "formality", "length_preference",
                               "greeting_style", "closing_style", "common_phrases", "avoid_phrases"],
                template=rewrite_template
            )
            
            self.rewrite_chain = LLMChain(
                llm=self.llm,
                prompt=rewrite_prompt
            )
            
            logger.info("Email responder initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing responder: {str(e)}")
            self.llm = None
    
    async def _check_meeting_availability(self, email_content: str, summary: str) -> Dict[str, Any]:
        """Check calendar availability for meeting requests"""
        if not self.calendar:
            return {"available": True, "suggestions": []}
        
        try:
            import re
            from datetime import datetime, timedelta
            
            # Extract time information from email content and summary
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?',
                r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',
                r'mañana|tomorrow|tomorrow',
                r'(\d{1,2})\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
            ]
            
            # Look for time mentions in the content
            content_lower = (email_content + " " + summary).lower()
            
            # Check if it mentions tomorrow or specific times
            if any(word in content_lower for word in ['mañana', 'tomorrow', 'reunión', 'meeting', 'cita', 'appointment']):
                tomorrow = datetime.now() + timedelta(days=1)
                
                # First, check if a specific time is mentioned (like 4 p.m.)
                specific_time = None
                time_match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm|a\.m\.|p\.m\.)', content_lower)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3)
                    
                    # Convert to 24-hour format
                    if period and 'pm' in period.lower() and hour != 12:
                        hour += 12
                    elif period and 'am' in period.lower() and hour == 12:
                        hour = 0
                    
                    logger.info(f"Extracted time: {hour}:{minute:02d} from '{time_match.group(0)}'")
                    specific_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    logger.info(f"Specific time set to: {specific_time}")
                
                # If no specific time mentioned, default to 4 PM
                if not specific_time:
                    specific_time = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0)
                
                # Check availability for the specific time
                end_time = specific_time + timedelta(hours=1)
                logger.info(f"Checking availability for {specific_time} to {end_time}")
                availability = await self.calendar.check_availability(specific_time, end_time)
                logger.info(f"Availability result: {availability}")
                
                if availability.get("available", False):
                    return {
                        "available": True,
                        "suggestions": []
                    }
                else:
                    # If not available, find alternative times
                    meeting_times = [
                        (9, 0),   # 9:00 AM
                        (10, 0),  # 10:00 AM
                        (11, 0),  # 11:00 AM
                        (14, 0),  # 2:00 PM
                        (15, 0),  # 3:00 PM
                        (16, 0),  # 4:00 PM
                        (17, 0),  # 5:00 PM
                    ]
                    
                    available_times = []
                    for hour, minute in meeting_times:
                        alt_start = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        alt_end = alt_start + timedelta(hours=1)
                        
                        alt_availability = await self.calendar.check_availability(alt_start, alt_end)
                        if alt_availability.get("available", False):
                            available_times.append(alt_start.strftime("%I:%M %p"))
                    
                    return {
                        "available": False,
                        "suggestions": available_times[:3] if available_times else ["No hay horarios disponibles mañana"]
                    }
            
            return {"available": True, "suggestions": []}
            
        except Exception as e:
            logger.error(f"Error checking meeting availability: {str(e)}")
            return {"available": True, "suggestions": []}
    
    async def generate_response(self, email_data: Dict[str, Any], summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a suggested email response
        
        Args:
            email_data: Original email data
            summary_data: Email summary from summarizer
            
        Returns:
            Generated response with metadata
        """
        if not self.response_chain:
            return {
                "response": "AI response generation not available",
                "tone": "professional",
                "confidence": "low",
                "suggestions": [],
                "error": "Responder not initialized"
            }
        
        try:
            # Extract information
            sender = email_data.get("sender", "Unknown")
            subject = email_data.get("subject", "No subject")
            content = email_data.get("body", "")
            summary = summary_data.get("summary", "")
            
            # Truncate content if too long
            if len(content) > 2000:
                content = content[:2000] + "..."
            
            # Check calendar availability for meeting requests
            availability_info = await self._check_meeting_availability(content, summary)
            
            # Modify the prompt based on availability
            if not availability_info.get("available", True):
                # If not available, include alternative times in the prompt
                suggestions = availability_info.get("suggestions", [])
                if suggestions:
                    summary += f"\n\nNota: No estoy disponible en el horario solicitado. Horarios alternativos disponibles: {', '.join(suggestions)}"
                else:
                    summary += "\n\nNota: No estoy disponible en el horario solicitado. Por favor sugiere otros horarios."
            
            # Generate response
            with get_openai_callback() as cb:
                result = self.response_chain.run(
                    sender=sender,
                    subject=subject,
                    content=content,
                    summary=summary
                )
                
                logger.info(f"Response generated - Tokens used: {cb.total_tokens}")
                logger.info(f"Raw response: {result}")
            
            # Add metadata
            result["original_email_id"] = email_data.get("id")
            result["original_sender"] = sender
            result["original_subject"] = subject
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "response": f"Error generating response: {str(e)}",
                "tone": "professional",
                "confidence": "low",
                "suggestions": [],
                "error": str(e)
            }
    
    async def rewrite_response(self, response: str, style_preferences: Dict[str, Any] = None) -> str:
        """
        Rewrite a response according to user's style preferences
        
        Args:
            response: Original response text
            style_preferences: Optional style overrides
            
        Returns:
            Rewritten response
        """
        if not self.rewrite_chain:
            return response
        
        try:
            # Use provided preferences or default user style
            style = style_preferences or self.user_style
            
            result = self.rewrite_chain.run(
                original_response=response,
                tone=style.get("tone", "professional"),
                formality=style.get("formality", "medium"),
                length_preference=style.get("length_preference", "medium"),
                greeting_style=style.get("greeting_style", "Hi"),
                closing_style=style.get("closing_style", "Best regards"),
                common_phrases=", ".join(style.get("common_phrases", [])),
                avoid_phrases=", ".join(style.get("avoid_phrases", []))
            )
            
            return result.strip()
            
        except Exception as e:
            logger.error(f"Error rewriting response: {str(e)}")
            return response
    
    async def generate_meeting_response(self, email_data: Dict[str, Any], 
                                      available_times: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a response for meeting requests with available times
        
        Args:
            email_data: Original meeting request email
            available_times: List of available time slots
            
        Returns:
            Meeting response with suggested times
        """
        if not self.llm:
            return {
                "response": "AI response generation not available",
                "tone": "professional",
                "confidence": "low",
                "suggestions": []
            }
        
        try:
            # Format available times
            time_options = []
            for slot in available_times[:3]:  # Limit to 3 options
                time_options.append(f"- {slot['start']} ({slot['duration_minutes']} minutes)")
            
            time_text = "\n".join(time_options) if time_options else "No available times found"
            
            prompt = f"""
            Generate a meeting response email:
            
            Original Request:
            From: {email_data.get('sender', 'Unknown')}
            Subject: {email_data.get('subject', 'Meeting Request')}
            Content: {email_data.get('body', '')[:500]}
            
            Available Times:
            {time_text}
            
            User's Style:
            - Greeting: {self.user_style.get('greeting_style', 'Hi')}
            - Closing: {self.user_style.get('closing_style', 'Best regards')}
            - Tone: {self.user_style.get('tone', 'professional')}
            
            Instructions:
            1. Acknowledge the meeting request
            2. Suggest 2-3 available time slots
            3. Ask for confirmation
            4. Be polite and professional
            5. Include your signature if available
            
            Return only the email response text.
            """
            
            response = self.llm(prompt)
            
            return {
                "response": response.strip(),
                "tone": self.user_style.get("tone", "professional"),
                "confidence": "high",
                "suggestions": [],
                "type": "meeting_response"
            }
            
        except Exception as e:
            logger.error(f"Error generating meeting response: {str(e)}")
            return {
                "response": f"Error generating meeting response: {str(e)}",
                "tone": "professional",
                "confidence": "low",
                "suggestions": []
            }
    
    def update_user_style(self, style_updates: Dict[str, Any]) -> bool:
        """
        Update user's writing style preferences
        
        Args:
            style_updates: Dictionary of style preferences to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update user style
            self.user_style.update(style_updates)
            
            # Save to file
            with open("user_style.json", 'w') as f:
                json.dump(self.user_style, f, indent=2)
            
            logger.info("User style updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user style: {str(e)}")
            return False
