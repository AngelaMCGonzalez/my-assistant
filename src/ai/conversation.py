"""
General AI Conversation using OpenAI
Handles open-ended questions and general chat
"""

import os
import logging
from typing import Dict, Any, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not installed. Please install openai")

logger = logging.getLogger(__name__)

class ConversationAI:
    def __init__(self):
        self.client = None
        if OPENAI_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                openai.api_key = api_key
                self.client = openai
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not found in environment variables")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the conversation AI"""
        return {
            "available": OPENAI_AVAILABLE,
            "configured": self.client is not None,
            "api_key_set": bool(os.getenv('OPENAI_API_KEY'))
        }
    
    async def generate_response(self, message: str, context: str = "") -> str:
        """
        Generate a conversational response using OpenAI
        
        Args:
            message: User's message
            context: Optional context about the conversation
            
        Returns:
            AI-generated response
        """
        if not self.client:
            return "Lo siento, no tengo acceso a la inteligencia artificial en este momento. ¿Puedo ayudarte con tus correos o calendario?"
        
        try:
            # Create a conversational prompt
            system_prompt = """Eres un asistente de WhatsApp muy amigable y útil. Responde en español de manera casual y amigable. 

INSTRUCCIONES:
- Usa un tono casual y amigable
- Responde en español
- Sé conciso pero útil
- Si no sabes algo, admítelo honestamente
- Mantén las respuestas apropiadas para WhatsApp (no muy largas)

CONTEXTO: {context}

Responde a la siguiente pregunta o comentario:"""

            user_prompt = f"{message}"
            
            response = await self.client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt.format(context=context)},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"Generated AI response: {ai_response[:100]}...")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "Lo siento, estoy teniendo problemas para procesar tu mensaje. ¿Puedo ayudarte con algo más específico como tus correos o calendario?"
