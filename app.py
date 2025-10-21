"""
Personal WhatsApp Assistant - Main FastAPI Application
Handles webhooks and coordinates all integrations
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import Dict, Any
import json
from contextlib import asynccontextmanager

from src.core.router import MessageRouter
from src.integrations.whatsapp import WhatsAppIntegration
# from src.integrations.gmail import GmailIntegration
from src.integrations.calendar import CalendarIntegration
from src.core.hitl import HITLManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for dependency injection
whatsapp = None
# gmail = None
calendar = None
hitl_manager = None
router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    global whatsapp, calendar, hitl_manager, router
    
    # Startup
    logger.info("Starting Personal WhatsApp Assistant...")
    
    try:
        # Initialize integrations
        whatsapp = WhatsAppIntegration()
        # gmail = GmailIntegration()
        calendar = CalendarIntegration()
        hitl_manager = HITLManager()
        
        # Initialize message router
        router = MessageRouter(whatsapp, None, calendar, hitl_manager)
        
        # Start background tasks
        await router.start_background_tasks_async()
        
        logger.info("All integrations initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize integrations: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Personal WhatsApp Assistant...")

app = FastAPI(
    title="Personal WhatsApp Assistant",
    description="AI-powered personal assistant for WhatsApp with email and calendar integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Personal WhatsApp Assistant is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {"status": "healthy", "service": "whatsapp-assistant"}

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    """
    Main webhook endpoint for receiving WhatsApp messages from UltraMsg
    """
    if router is None:
        raise HTTPException(status_code=503, detail="Router not initialized")
    
    try:
        # Get the raw body
        body = await request.body()
        data = json.loads(body)
        
        logger.info(f"Received WhatsApp webhook: {data}")
        
        # Process the message through the router
        response = await router.process_message(data)
        
        return {"status": "success", "response": response}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# @app.post("/gmail-webhook")
# async def gmail_webhook(request: Request):
#     """
#     Webhook endpoint for Gmail notifications (if using Gmail push notifications)
#     """
#     if router is None:
#         raise HTTPException(status_code=503, detail="Router not initialized")
#     
#     try:
#         body = await request.body()
#         data = json.loads(body)
#         
#         logger.info(f"Received Gmail webhook: {data}")
#         
#         # Process new email
#         response = await router.process_new_email(data)
#         
#         return {"status": "success", "response": response}
#         
#     except Exception as e:
#         logger.error(f"Error processing Gmail webhook: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")

# @app.post("/calendar-webhook")
# async def calendar_webhook(request: Request):
#     """
#     Webhook endpoint for Google Calendar notifications
#     """
#     if router is None:
#         raise HTTPException(status_code=503, detail="Router not initialized")
#     
#     try:
#         body = await request.body()
#         data = json.loads(body)
#         
#         logger.info(f"Received Calendar webhook: {data}")
#         
#         # Process calendar event
#         response = await router.process_calendar_event(data)
#         
#         return {"status": "success", "response": response}
#         
#     except Exception as e:
#         logger.error(f"Error processing Calendar webhook: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/status")
async def get_status():
    """Get status of all integrations"""
    if not all([whatsapp, calendar, hitl_manager]):
        return {"error": "Integrations not initialized"}
    
    return {
        "whatsapp": whatsapp.get_status(),
        # "gmail": gmail.get_status(),
        "calendar": calendar.get_status(),
        "hitl": hitl_manager.get_status()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

