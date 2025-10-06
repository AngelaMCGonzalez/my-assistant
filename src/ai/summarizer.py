"""
AI Email Summarizer using LangChain and OpenAI
Handles email summarization and content analysis
"""

import os
import logging
from typing import Dict, Any, Optional
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

class EmailSummaryOutputParser(BaseOutputParser):
    """Custom parser for email summary output"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse the LLM output into structured data"""
        try:
            # Try to parse as JSON first (fallback for old format)
            if text.strip().startswith('{'):
                return json.loads(text)
            
            # Parse the new plain text format
            lines = text.strip().split('\n')
            summary_data = {
                "summary": "",
                "key_points": [],
                "action_required": False,
                "urgency": "low",
                "category": "general"
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Handle Spanish format
                if line.lower().startswith("resumen:"):
                    summary_data["summary"] = line[8:].strip()
                elif line.lower().startswith("puntos clave:"):
                    current_section = "key_points"
                elif line.lower().startswith("acción requerida:"):
                    action_text = line[17:].strip().lower()
                    summary_data["action_required"] = action_text in ["sí", "si", "yes", "true", "1"]
                elif line.lower().startswith("urgencia:"):
                    summary_data["urgency"] = line[9:].strip().lower()
                elif line.lower().startswith("categoría:"):
                    summary_data["category"] = line[10:].strip().lower()
                elif current_section == "key_points" and line.startswith("-"):
                    summary_data["key_points"].append(line[1:].strip())
                # Fallback for English format
                elif line.lower().startswith("summary:"):
                    summary_data["summary"] = line[8:].strip()
                elif line.lower().startswith("key points:"):
                    current_section = "key_points"
                elif line.lower().startswith("action required:"):
                    summary_data["action_required"] = line[15:].strip().lower() in ["yes", "true", "1"]
                elif line.lower().startswith("urgency:"):
                    summary_data["urgency"] = line[8:].strip().lower()
                elif line.lower().startswith("category:"):
                    summary_data["category"] = line[9:].strip().lower()
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error parsing summary output: {str(e)}")
            return {
                "summary": text,
                "key_points": [],
                "action_required": False,
                "urgency": "low",
                "category": "general"
            }

class EmailSummarizer:
    def __init__(self):
        self.llm = None
        self.summary_chain = None
        self.analysis_chain = None
        
        if LANGCHAIN_AVAILABLE:
            self._initialize_llm()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the summarizer"""
        return {
            "available": LANGCHAIN_AVAILABLE,
            "initialized": self.llm is not None,
            "api_key_set": bool(os.getenv("OPENAI_API_KEY"))
        }
    
    def _initialize_llm(self):
        """Initialize the OpenAI LLM"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set")
                return
            
            self.llm = OpenAI(
                temperature=0.3,
                max_tokens=500,
                openai_api_key=api_key
            )
            
            # Create summary prompt template
            summary_template = """
            Analiza el siguiente correo electrónico y proporciona un resumen estructurado en español:
            
            De: {sender}
            Asunto: {subject}
            Fecha: {date}
            
            Contenido del correo:
            {body}
            
            Proporciona tu respuesta en el siguiente formato:
            
            Resumen: [Resumen breve del contenido del correo en español]
            
            Puntos clave:
            - [Punto 1]
            - [Punto 2]
            - [Punto 3]
            
            Acción requerida: [Sí/No]
            Urgencia: [baja/media/alta]
            Categoría: [trabajo/personal/urgente/reunión/otro]
            """
            
            summary_prompt = PromptTemplate(
                input_variables=["sender", "subject", "date", "body"],
                template=summary_template
            )
            
            self.summary_chain = LLMChain(
                llm=self.llm,
                prompt=summary_prompt,
                output_parser=EmailSummaryOutputParser()
            )
            
            # Create analysis prompt template
            analysis_template = """
            Analiza este correo electrónico para obtener detalles importantes y contexto:
            
            De: {sender}
            Asunto: {subject}
            Contenido: {body}
            
            Proporciona información sobre:
            1. La intención y tono del remitente
            2. Cualquier fecha límite o información sensible al tiempo
            3. Acciones o respuestas requeridas
            4. Contexto de la relación (profesional, personal, etc.)
            5. Cualquier archivo adjunto o contexto adicional necesario
            
            Mantén el análisis conciso pero completo. Responde en español.
            """
            
            analysis_prompt = PromptTemplate(
                input_variables=["sender", "subject", "body"],
                template=analysis_template
            )
            
            self.analysis_chain = LLMChain(
                llm=self.llm,
                prompt=analysis_prompt
            )
            
            logger.info("Email summarizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing summarizer: {str(e)}")
            self.llm = None
    
    async def summarize_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize an email
        
        Args:
            email_data: Email data from Gmail integration
            
        Returns:
            Structured summary of the email
        """
        if not self.summary_chain:
            return {
                "summary": "AI summarization not available",
                "key_points": [],
                "action_required": False,
                "urgency": "low",
                "category": "general",
                "error": "Summarizer not initialized"
            }
        
        try:
            # Extract email information
            sender = email_data.get("sender", "Unknown")
            subject = email_data.get("subject", "No subject")
            date = email_data.get("date", "Unknown date")
            body = email_data.get("body", "")
            
            # Truncate body if too long
            if len(body) > 3000:
                body = body[:3000] + "..."
            
            # Generate summary
            with get_openai_callback() as cb:
                result = self.summary_chain.run(
                    sender=sender,
                    subject=subject,
                    date=date,
                    body=body
                )
                
                logger.info(f"Summary generated - Tokens used: {cb.total_tokens}")
            
            # Add metadata
            result["email_id"] = email_data.get("id")
            result["original_sender"] = sender
            result["original_subject"] = subject
            result["original_date"] = date
            
            return result
            
        except Exception as e:
            logger.error(f"Error summarizing email: {str(e)}")
            return {
                "summary": f"Error summarizing email: {str(e)}",
                "key_points": [],
                "action_required": False,
                "urgency": "low",
                "category": "general",
                "error": str(e)
            }
    
    async def analyze_email_context(self, email_data: Dict[str, Any]) -> str:
        """
        Analyze email for context and insights
        
        Args:
            email_data: Email data from Gmail integration
            
        Returns:
            Analysis text
        """
        if not self.analysis_chain:
            return "AI analysis not available"
        
        try:
            sender = email_data.get("sender", "Unknown")
            subject = email_data.get("subject", "No subject")
            body = email_data.get("body", "")
            
            # Truncate body if too long
            if len(body) > 2000:
                body = body[:2000] + "..."
            
            result = self.analysis_chain.run(
                sender=sender,
                subject=subject,
                body=body
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing email: {str(e)}")
            return f"Error analyzing email: {str(e)}"
    
    async def extract_action_items(self, email_data: Dict[str, Any]) -> list:
        """
        Extract action items from an email
        
        Args:
            email_data: Email data from Gmail integration
            
        Returns:
            List of action items
        """
        if not self.llm:
            return []
        
        try:
            prompt = f"""
            Extract specific action items from this email:
            
            From: {email_data.get('sender', 'Unknown')}
            Subject: {email_data.get('subject', 'No subject')}
            Content: {email_data.get('body', '')[:1000]}
            
            Return a JSON array of action items, each with:
            - action: description of what needs to be done
            - deadline: when it needs to be done (if mentioned)
            - priority: low/medium/high
            
            Example: [{{"action": "Review proposal", "deadline": "Friday", "priority": "high"}}]
            """
            
            response = self.llm(prompt)
            
            # Try to parse as JSON
            try:
                action_items = json.loads(response)
                return action_items if isinstance(action_items, list) else []
            except json.JSONDecodeError:
                # If not JSON, return a simple list
                lines = response.strip().split('\n')
                return [{"action": line.strip(), "deadline": "", "priority": "medium"} 
                       for line in lines if line.strip()]
            
        except Exception as e:
            logger.error(f"Error extracting action items: {str(e)}")
            return []
    
    async def categorize_email(self, email_data: Dict[str, Any]) -> str:
        """
        Categorize an email by type and importance
        
        Args:
            email_data: Email data from Gmail integration
            
        Returns:
            Category string
        """
        if not self.llm:
            return "general"
        
        try:
            prompt = f"""
            Categorize this email:
            
            From: {email_data.get('sender', 'Unknown')}
            Subject: {email_data.get('subject', 'No subject')}
            Content: {email_data.get('body', '')[:500]}
            
            Choose the most appropriate category:
            - urgent: requires immediate attention
            - meeting: meeting request or scheduling
            - work: work-related but not urgent
            - personal: personal communication
            - spam: likely spam or promotional
            - other: doesn't fit other categories
            
            Return only the category name.
            """
            
            response = self.llm(prompt)
            category = response.strip().lower()
            
            valid_categories = ["urgent", "meeting", "work", "personal", "spam", "other"]
            return category if category in valid_categories else "other"
            
        except Exception as e:
            logger.error(f"Error categorizing email: {str(e)}")
            return "other"
