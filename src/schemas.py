"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"

class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class EmailCategory(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    URGENT = "urgent"
    MEETING = "meeting"
    SPAM = "spam"
    OTHER = "other"

class WhatsAppWebhookData(BaseModel):
    """Schema for WhatsApp webhook data"""
    id: Optional[str] = None
    from_number: str = Field(..., alias="from")
    to: str
    body: str
    type: MessageType = MessageType.TEXT
    timestamp: Optional[str] = None
    media: Optional[str] = None
    filename: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True

class EmailData(BaseModel):
    """Schema for email data"""
    id: str
    sender: str
    subject: str
    body: str
    date: str
    thread_id: Optional[str] = None
    labels: List[str] = Field(default_factory=list)

class EmailSummary(BaseModel):
    """Schema for email summary"""
    summary: str
    key_points: List[str] = Field(default_factory=list)
    action_required: bool = False
    urgency: UrgencyLevel = UrgencyLevel.LOW
    category: EmailCategory = EmailCategory.OTHER
    email_id: Optional[str] = None
    original_sender: Optional[str] = None
    original_subject: Optional[str] = None
    original_date: Optional[str] = None

class EmailResponse(BaseModel):
    """Schema for email response"""
    response: str
    tone: str = "professional"
    confidence: str = "medium"
    suggestions: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    original_email_id: Optional[str] = None
    original_sender: Optional[str] = None
    original_subject: Optional[str] = None

class CalendarEvent(BaseModel):
    """Schema for calendar event"""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    location: Optional[str] = None

class PendingAction(BaseModel):
    """Schema for pending action"""
    action_id: str
    action_type: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: str = "pending"

class UserStyle(BaseModel):
    """Schema for user writing style preferences"""
    tone: str = "professional"
    formality: str = "medium"
    length_preference: str = "medium"
    greeting_style: str = "Hi"
    closing_style: str = "Best regards"
    common_phrases: List[str] = Field(default_factory=list)
    avoid_phrases: List[str] = Field(default_factory=list)
    signature: str = ""

class SystemStatus(BaseModel):
    """Schema for system status"""
    whatsapp: Dict[str, Any]
    gmail: Dict[str, Any]
    calendar: Dict[str, Any]
    hitl: Dict[str, Any]
    ai: Dict[str, Any]

class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    status: str
    message: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class CommandRequest(BaseModel):
    """Schema for command requests"""
    command: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    user_phone: str

class CommandResponse(BaseModel):
    """Schema for command responses"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

