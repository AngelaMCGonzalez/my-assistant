"""
Human-in-the-Loop (HITL) Manager
Handles approval workflows and user interactions
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger(__name__)

class PendingAction:
    """Represents a pending action waiting for user approval"""
    
    def __init__(self, action_type: str, data: Dict[str, Any], expires_in_minutes: int = 30):
        self.id = str(uuid.uuid4())
        self.action_type = action_type
        self.data = data
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=expires_in_minutes)
        self.status = "pending"  # pending, approved, rejected, expired
        self.user_response = None
        self.response_at = None
    
    def is_expired(self) -> bool:
        """Check if the action has expired"""
        return datetime.now() > self.expires_at
    
    def approve(self, user_response: str = None) -> bool:
        """Approve the action"""
        if self.is_expired():
            return False
        
        self.status = "approved"
        self.user_response = user_response
        self.response_at = datetime.now()
        return True
    
    def reject(self, user_response: str = None) -> bool:
        """Reject the action"""
        if self.is_expired():
            return False
        
        self.status = "rejected"
        self.user_response = user_response
        self.response_at = datetime.now()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status,
            "user_response": self.user_response,
            "response_at": self.response_at.isoformat() if self.response_at else None,
            "is_expired": self.is_expired()
        }

class HITLManager:
    """Manages human-in-the-loop workflows and approvals"""
    
    def __init__(self):
        self.pending_actions: Dict[str, PendingAction] = {}
        self.user_phone = None  # Will be set from environment or config
        self.auto_approve_patterns = []  # Patterns for auto-approval
        self.auto_reject_patterns = []  # Patterns for auto-rejection
        
        self._load_config()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the HITL manager"""
        return {
            "pending_actions_count": len(self.pending_actions),
            "user_phone": self.user_phone,
            "auto_approve_patterns": len(self.auto_approve_patterns),
            "auto_reject_patterns": len(self.auto_reject_patterns)
        }
    
    def _load_config(self):
        """Load HITL configuration"""
        try:
            config_file = "hitl_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.auto_approve_patterns = config.get("auto_approve_patterns", [])
                    self.auto_reject_patterns = config.get("auto_reject_patterns", [])
        except Exception as e:
            logger.error(f"Error loading HITL config: {str(e)}")
    
    def create_pending_action(self, action_type: str, data: Dict[str, Any], 
                            expires_in_minutes: int = 30) -> PendingAction:
        """
        Create a new pending action
        
        Args:
            action_type: Type of action (email_reply, calendar_event, etc.)
            data: Action data
            expires_in_minutes: Minutes until action expires
            
        Returns:
            Created PendingAction object
        """
        action = PendingAction(action_type, data, expires_in_minutes)
        self.pending_actions[action.id] = action
        
        logger.info(f"Created pending action: {action.id} ({action_type})")
        return action
    
    def get_pending_action(self, action_id: str) -> Optional[PendingAction]:
        """Get a pending action by ID"""
        return self.pending_actions.get(action_id)
    
    def get_pending_actions(self) -> List[PendingAction]:
        """Get all pending actions"""
        # Clean up expired actions first
        self._cleanup_expired_actions()
        
        # Return only non-expired pending actions
        return [action for action in self.pending_actions.values() 
                if action.status == "pending" and not action.is_expired()]
    
    def process_user_response(self, message: str, from_phone: str) -> Optional[Dict[str, Any]]:
        """
        Process a user response to a pending action
        
        Args:
            message: User's response message
            from_phone: Phone number the message came from
            
        Returns:
            Result of processing the response
        """
        # Check if this is a response to a pending action
        action_id = self._extract_action_id(message)
        if action_id:
            return self._handle_action_response(action_id, message)
        
        # Check for approval/rejection patterns
        approval_status = self._check_approval_patterns(message)
        if approval_status:
            # Find the most recent pending action
            recent_action = self._get_most_recent_pending_action()
            if recent_action:
                return self._handle_action_response(recent_action.id, message)
        
        return None
    
    def _extract_action_id(self, message: str) -> Optional[str]:
        """Extract action ID from message (if user references a specific action)"""
        # Look for patterns like "approve 12345" or "reject abc-def"
        import re
        patterns = [
            r'(?:approve|reject|yes|no)\s+([a-f0-9-]{8,})',
            r'action\s+([a-f0-9-]{8,})',
            r'#([a-f0-9-]{8,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _check_approval_patterns(self, message: str) -> Optional[str]:
        """Check if message matches approval/rejection patterns"""
        message_lower = message.lower().strip()
        
        # Check auto-approve patterns
        for pattern in self.auto_approve_patterns:
            if pattern.lower() in message_lower:
                return "approve"
        
        # Check auto-reject patterns
        for pattern in self.auto_reject_patterns:
            if pattern.lower() in message_lower:
                return "reject"
        
        # Check common approval/rejection patterns
        approval_words = ["✅", "yes", "y", "approve", "ok", "sí", "si", "confirm"]
        rejection_words = ["❌", "no", "n", "reject", "cancel", "no"]
        
        if any(word in message_lower for word in approval_words):
            return "approve"
        elif any(word in message_lower for word in rejection_words):
            return "reject"
        
        return None
    
    def _get_most_recent_pending_action(self) -> Optional[PendingAction]:
        """Get the most recent pending action"""
        if not self.pending_actions:
            return None
        
        # Return the most recently created action that's still pending
        pending_actions = [action for action in self.pending_actions.values() 
                          if action.status == "pending" and not action.is_expired()]
        
        if not pending_actions:
            return None
        
        return max(pending_actions, key=lambda x: x.created_at)
    
    def _handle_action_response(self, action_id: str, message: str) -> Dict[str, Any]:
        """Handle a response to a specific action"""
        action = self.get_pending_action(action_id)
        if not action:
            return {"success": False, "error": "Action not found"}
        
        if action.is_expired():
            return {"success": False, "error": "Action has expired"}
        
        # Determine approval status
        approval_status = self._check_approval_patterns(message)
        
        if approval_status == "approve":
            success = action.approve(message)
            if success:
                logger.info(f"Action {action_id} approved")
                return {
                    "success": True,
                    "action_id": action_id,
                    "status": "approved",
                    "action_type": action.action_type,
                    "data": action.data
                }
        elif approval_status == "reject":
            success = action.reject(message)
            if success:
                logger.info(f"Action {action_id} rejected")
                return {
                    "success": True,
                    "action_id": action_id,
                    "status": "rejected",
                    "action_type": action.action_type
                }
        
        return {"success": False, "error": "Could not determine approval status"}
    
    def get_pending_actions(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all pending actions, optionally filtered by status"""
        actions = list(self.pending_actions.values())
        
        if status:
            actions = [action for action in actions if action.status == status]
        
        return [action.to_dict() for action in actions]
    
    def cleanup_expired_actions(self) -> int:
        """Remove expired actions and return count of cleaned actions"""
        expired_actions = [action_id for action_id, action in self.pending_actions.items() 
                          if action.is_expired()]
        
        for action_id in expired_actions:
            del self.pending_actions[action_id]
        
        if expired_actions:
            logger.info(f"Cleaned up {len(expired_actions)} expired actions")
        
        return len(expired_actions)
    
    def get_action_summary(self, action_id: str) -> Optional[str]:
        """Get a human-readable summary of an action"""
        action = self.get_pending_action(action_id)
        if not action:
            return None
        
        if action.action_type == "email_reply":
            return f"Reply to email from {action.data.get('sender', 'Unknown')}: {action.data.get('subject', 'No subject')}"
        elif action.action_type == "calendar_event":
            return f"Create calendar event: {action.data.get('title', 'Untitled')} at {action.data.get('start_time', 'Unknown time')}"
        else:
            return f"{action.action_type}: {action.data.get('description', 'No description')}"
    
    def add_auto_approve_pattern(self, pattern: str) -> bool:
        """Add a pattern for auto-approval"""
        try:
            if pattern not in self.auto_approve_patterns:
                self.auto_approve_patterns.append(pattern)
                self._save_config()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding auto-approve pattern: {str(e)}")
            return False
    
    def add_auto_reject_pattern(self, pattern: str) -> bool:
        """Add a pattern for auto-rejection"""
        try:
            if pattern not in self.auto_reject_patterns:
                self.auto_reject_patterns.append(pattern)
                self._save_config()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding auto-reject pattern: {str(e)}")
            return False
    
    def _save_config(self):
        """Save HITL configuration"""
        try:
            config = {
                "auto_approve_patterns": self.auto_approve_patterns,
                "auto_reject_patterns": self.auto_reject_patterns
            }
            
            with open("hitl_config.json", 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving HITL config: {str(e)}")

