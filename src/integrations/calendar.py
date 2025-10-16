"""
Google Calendar Integration using Calendar API
Handles checking availability, creating events, and managing calendar data
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    logging.warning("Google Calendar API libraries not installed. Please install google-api-python-client and google-auth-oauthlib")

logger = logging.getLogger(__name__)

class CalendarIntegration:
    def __init__(self):
        self.service = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.calendar_id = 'primary'  # Use primary calendar by default
        
        if CALENDAR_AVAILABLE:
            self._authenticate()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the Calendar integration"""
        return {
            "available": CALENDAR_AVAILABLE,
            "authenticated": self.service is not None,
            "scopes": self.scopes,
            "calendar_id": self.calendar_id
        }
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        try:
            creds = None
            
            # Try to load credentials from environment variables first
            calendar_credentials_json = os.getenv('CALENDAR_CREDENTIALS_JSON')
            calendar_token_json = os.getenv('CALENDAR_TOKEN_JSON')
            
            if calendar_credentials_json and calendar_token_json:
                # Create temporary files from environment variables
                import tempfile
                
                # Create credentials file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as creds_file:
                    creds_file.write(calendar_credentials_json)
                    credentials_file_path = creds_file.name
                
                # Create token file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as token_file:
                    token_file.write(calendar_token_json)
                    token_file_path = token_file.name
                
                # Load credentials from token file
                creds = Credentials.from_authorized_user_file(token_file_path, self.scopes)
                
                # Clean up temporary files
                os.unlink(credentials_file_path)
                os.unlink(token_file_path)
                
            else:
                # Fallback to file-based authentication
                token_file = os.getenv('CALENDAR_TOKEN_FILE', './credentials/calendar_token.json')
                credentials_file = os.getenv('CALENDAR_CREDENTIALS_FILE', './credentials/calendar_credentials.json')
                
                # Load existing credentials
                if os.path.exists(token_file):
                    creds = Credentials.from_authorized_user_file(token_file, self.scopes)
                
                # If there are no valid credentials, get new ones
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        if os.path.exists(credentials_file):
                            flow = InstalledAppFlow.from_client_secrets_file(
                                credentials_file, self.scopes)
                            creds = flow.run_local_server(port=0)
                        else:
                            logger.error(f"Calendar credentials file not found: {credentials_file}")
                            return
                    
                    # Save credentials for next run
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
            
            if creds and creds.valid:
                self.credentials = creds
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar API authenticated successfully")
            else:
                logger.error("Calendar authentication failed: Invalid credentials")
                self.service = None
            
        except Exception as e:
            logger.error(f"Calendar authentication failed: {str(e)}")
            self.service = None
    
    async def check_availability(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        Check if the calendar is available for a specific time range
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            Availability information
        """
        if not self.service:
            return {"available": False, "error": "Calendar service not available"}
        
        try:
            # Format times for API
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            # Query calendar for events in the time range
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Check for conflicts
            conflicts = []
            for event in events:
                event_start = event['start'].get('dateTime', event['start'].get('date'))
                event_end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Parse event times with proper timezone handling for Mexico City (UTC-6)
                if 'T' in event_start:  # DateTime event
                    # Handle timezone offset properly
                    if event_start.endswith('Z'):
                        event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                    else:
                        event_start_dt = datetime.fromisoformat(event_start)
                    
                    if event_end.endswith('Z'):
                        event_end_dt = datetime.fromisoformat(event_end.replace('Z', '+00:00'))
                    else:
                        event_end_dt = datetime.fromisoformat(event_end)
                    
                    # Convert to Mexico City timezone (UTC-6) and then to naive datetime
                    from datetime import timezone, timedelta
                    mexico_tz = timezone(timedelta(hours=-6))
                    
                    if event_start_dt.tzinfo is not None:
                        # Convert to Mexico City timezone
                        event_start_dt = event_start_dt.astimezone(mexico_tz).replace(tzinfo=None)
                    if event_end_dt.tzinfo is not None:
                        # Convert to Mexico City timezone
                        event_end_dt = event_end_dt.astimezone(mexico_tz).replace(tzinfo=None)
                else:  # All-day event
                    event_start_dt = datetime.fromisoformat(event_start)
                    event_end_dt = datetime.fromisoformat(event_end) + timedelta(days=1)
                
                # Check for overlap
                if (event_start_dt < end_time and event_end_dt > start_time):
                    conflicts.append({
                        'title': event.get('summary', 'No title'),
                        'start': event_start,
                        'end': event_end,
                        'description': event.get('description', '')
                    })
            
            return {
                "available": len(conflicts) == 0,
                "conflicts": conflicts,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }
            
        except HttpError as e:
            logger.error(f"Error checking availability: {str(e)}")
            return {"available": False, "error": str(e)}
    
    async def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                          description: str = "", attendees: List[str] = None, 
                          location: str = "") -> Dict[str, Any]:
        """
        Create a new calendar event
        
        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            attendees: List of attendee email addresses
            location: Event location
            
        Returns:
            Created event information
        """
        if not self.service:
            return {"success": False, "error": "Calendar service not available"}
        
        try:
            # Format times for API
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            # Build event
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time_str,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time_str,
                    'timeZone': 'UTC',
                },
            }
            
            if location:
                event['location'] = location
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"Event created: {created_event.get('htmlLink')}")
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_link": created_event.get('htmlLink'),
                "event": created_event
            }
            
        except HttpError as e:
            logger.error(f"Error creating event: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get events within a date range
        
        Args:
            start_date: Start of the date range
            end_date: End of the date range
            
        Returns:
            List of events
        """
        if not self.service:
            return []
        
        try:
            time_min = start_date.isoformat() + 'Z'
            time_max = end_date.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Format events for easier use
            formatted_events = []
            for event in events:
                formatted_event = {
                    'id': event['id'],
                    'title': event.get('summary', 'No title'),
                    'description': event.get('description', ''),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'location': event.get('location', ''),
                    'attendees': [attendee.get('email') for attendee in event.get('attendees', [])],
                    'html_link': event.get('htmlLink')
                }
                formatted_events.append(formatted_event)
            
            return formatted_events
            
        except HttpError as e:
            logger.error(f"Error fetching events: {str(e)}")
            return []
    
    async def get_today_events(self) -> List[Dict[str, Any]]:
        """Get today's events"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        return await self.get_events(today, tomorrow)
    
    async def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for the next N days"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        return await self.get_events(start_date, end_date)
    
    async def find_free_time_slots(self, date: datetime, duration_minutes: int = 60, 
                                  working_hours: tuple = (9, 17)) -> List[Dict[str, Any]]:
        """
        Find free time slots on a specific date
        
        Args:
            date: Date to check
            duration_minutes: Duration of the slot in minutes
            working_hours: Tuple of (start_hour, end_hour) for working hours
            
        Returns:
            List of available time slots
        """
        if not self.service:
            return []
        
        try:
            # Get all events for the day
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            events = await self.get_events(start_of_day, end_of_day)
            
            # Create working hours range
            work_start = date.replace(hour=working_hours[0], minute=0, second=0, microsecond=0)
            work_end = date.replace(hour=working_hours[1], minute=0, second=0, microsecond=0)
            
            # Sort events by start time
            events.sort(key=lambda x: x['start'])
            
            free_slots = []
            current_time = work_start
            
            for event in events:
                event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                
                # Check if there's a gap before this event
                if current_time < event_start:
                    gap_duration = (event_start - current_time).total_seconds() / 60
                    if gap_duration >= duration_minutes:
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': event_start.isoformat(),
                            'duration_minutes': gap_duration
                        })
                
                # Move current time to after this event
                current_time = max(current_time, event_end)
            
            # Check for free time after the last event
            if current_time < work_end:
                remaining_time = (work_end - current_time).total_seconds() / 60
                if remaining_time >= duration_minutes:
                    free_slots.append({
                        'start': current_time.isoformat(),
                        'end': work_end.isoformat(),
                        'duration_minutes': remaining_time
                    })
            
            return free_slots
            
        except Exception as e:
            logger.error(f"Error finding free time slots: {str(e)}")
            return []
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        if not self.service:
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Event deleted: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Error deleting event: {str(e)}")
            return False

