"""
Enhanced AI Conversation using OpenAI
Handles open-ended questions, general chat, and intelligent responses
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

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
        self.conversation_history = []  # Store conversation context
        self.user_preferences = self._load_user_preferences()
        self.personality_traits = {
            "tone": "friendly",
            "formality": "casual",
            "humor": "light",
            "language": "spanish",
            "response_length": "medium"
        }
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
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Load user conversation preferences"""
        try:
            prefs_file = "user_conversation_prefs.json"
            if os.path.exists(prefs_file):
                with open(prefs_file, 'r') as f:
                    return json.load(f)
            else:
                # Default preferences
                return {
                    "favorite_topics": [],
                    "communication_style": "friendly",
                    "interests": [],
                    "conversation_memory": True
                }
        except Exception as e:
            logger.error(f"Error loading user preferences: {str(e)}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the conversation AI"""
        return {
            "available": OPENAI_AVAILABLE,
            "configured": self.client is not None,
            "api_key_set": bool(os.getenv('OPENAI_API_KEY')),
            "conversation_history_length": len(self.conversation_history),
            "personality_traits": self.personality_traits
        }
    
    async def generate_response(self, message: str, context: str = "", user_phone: str = None) -> str:
        """
        Generate a conversational response using OpenAI with enhanced features
        
        Args:
            message: User's message
            context: Optional context about the conversation
            user_phone: User's phone number for personalization
            
        Returns:
            AI-generated response
        """
        if not self.client:
            return "Lo siento, no tengo acceso a la inteligencia artificial en este momento. ¿Puedo ayudarte con algo más?"
        
        try:
            # Add to conversation history
            self._add_to_history("user", message)
            
            # Build enhanced system prompt
            system_prompt = self._build_enhanced_system_prompt(context, user_phone)
            
            # Prepare conversation context
            conversation_context = self._build_conversation_context()
            
            # Generate response
            response = await self.client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=conversation_context + [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Add to conversation history
            self._add_to_history("assistant", ai_response)
            
            # Update user preferences based on conversation
            self._update_user_preferences(message, ai_response)
            
            logger.info(f"Generated AI response: {ai_response[:100]}...")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "Lo siento, estoy teniendo problemas para procesar tu mensaje. ¿Puedo ayudarte con algo más?"
    
    def _build_enhanced_system_prompt(self, context: str, user_phone: str = None) -> str:
        """Build an enhanced system prompt with personality and context"""
        current_time = datetime.now().strftime("%H:%M")
        current_date = datetime.now().strftime("%A, %d de %B de %Y")
        
        personality = self.personality_traits
        user_prefs = self.user_preferences
        
        system_prompt = f"""Eres un asistente de WhatsApp muy amigable y útil. Tu personalidad es {personality['tone']} y {personality['formality']}.

PERSONALIDAD:
- Tono: {personality['tone']}
- Formalidad: {personality['formality']}
- Humor: {personality['humor']}
- Idioma: {personality['language']}
- Longitud de respuesta: {personality['response_length']}

CONTEXTO ACTUAL:
- Hora: {current_time}
- Fecha: {current_date}
- Contexto: {context}

PREFERENCIAS DEL USUARIO:
- Estilo de comunicación: {user_prefs.get('communication_style', 'friendly')}
- Temas favoritos: {', '.join(user_prefs.get('favorite_topics', []))}
- Intereses: {', '.join(user_prefs.get('interests', []))}

INSTRUCCIONES:
- Responde en español de manera natural y amigable
- Sé conciso pero útil (máximo 2-3 oraciones para WhatsApp)
- Usa emojis apropiados ocasionalmente
- Si no sabes algo, admítelo honestamente
- Mantén un tono conversacional y personal
- Recuerda el contexto de la conversación anterior

Responde de manera natural y amigable:"""
        
        return system_prompt
    
    def _build_conversation_context(self) -> List[Dict[str, str]]:
        """Build conversation context from history"""
        # Keep only last 6 messages to avoid token limits
        recent_history = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
        
        context = []
        for msg in recent_history:
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return context
    
    def _add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 messages to manage memory
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def _update_user_preferences(self, user_message: str, ai_response: str):
        """Update user preferences based on conversation"""
        try:
            # Simple topic extraction (can be enhanced)
            topics = self._extract_topics(user_message)
            if topics:
                current_topics = self.user_preferences.get("favorite_topics", [])
                for topic in topics:
                    if topic not in current_topics:
                        current_topics.append(topic)
                self.user_preferences["favorite_topics"] = current_topics[:10]  # Keep top 10
            
            # Save preferences
            self._save_user_preferences()
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {str(e)}")
    
    def _extract_topics(self, message: str) -> List[str]:
        """Extract topics from user message"""
        # Simple keyword-based topic extraction
        topic_keywords = {
            "tecnología": ["tecnología", "tech", "computadora", "internet", "app", "software"],
            "trabajo": ["trabajo", "trabajar", "oficina", "empleo", "negocio"],
            "salud": ["salud", "médico", "ejercicio", "fitness", "bienestar"],
            "entretenimiento": ["película", "música", "juego", "deporte", "fiesta"],
            "viajes": ["viaje", "vacaciones", "turismo", "avión", "hotel"],
            "comida": ["comida", "restaurante", "cocinar", "receta", "cena"]
        }
        
        message_lower = message.lower()
        topics = []
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _save_user_preferences(self):
        """Save user preferences to file"""
        try:
            with open("user_conversation_prefs.json", 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def update_personality(self, traits: Dict[str, Any]):
        """Update AI personality traits"""
        self.personality_traits.update(traits)
        logger.info(f"Personality updated: {traits}")
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation"""
        if not self.conversation_history:
            return "No hay conversación previa."
        
        recent_messages = self.conversation_history[-5:]  # Last 5 messages
        summary = "Conversación reciente:\n"
        
        for msg in recent_messages:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
            summary += f"- {role}: {content}\n"
        
        return summary
