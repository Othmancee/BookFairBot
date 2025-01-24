import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
import logging
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class GA4Manager:
    def __init__(self):
        """Initialize GA4 client."""
        self.measurement_id = os.getenv('GA4_MEASUREMENT_ID')
        self.api_secret = os.getenv('GA4_API_SECRET')
        self.is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
        self.debug_mode = os.getenv('GA4_DEBUG', 'false').lower() == 'true'
        
        if not self.measurement_id or not self.api_secret:
            logger.error("GA4 credentials not found in environment variables")
            raise ValueError("GA4_MEASUREMENT_ID and GA4_API_SECRET environment variables are required")
        
        self.base_url = f"https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
        
        if not self.is_production:
            logger.warning("Running in development mode - events will be logged but not sent to GA4")
    
    def track_event(self, name: str, user_id: str, params: Optional[Dict[str, Any]] = None):
        """Send event to GA4."""
        try:
            event_data = {
                "client_id": user_id,
                "events": [{
                    "name": name,
                    "params": {
                        **(params or {}),
                        "timestamp_micros": int(datetime.now().timestamp() * 1000000),
                        "environment": "production" if self.is_production else "development"
                    }
                }]
            }
            
            # In development, just log the event
            if not self.is_production:
                if self.debug_mode:
                    logger.info(f"[DEV] Would send event to GA4: {json.dumps(event_data, indent=2)}")
                return
            
            response = requests.post(
                self.base_url,
                json=event_data
            )
            
            if response.status_code != 204:
                logger.error(f"Failed to send event to GA4: {response.text}")
            elif self.debug_mode:
                logger.debug(f"Successfully sent event {name} to GA4")
                
        except Exception as e:
            logger.error(f"Error sending event to GA4: {e}")
            if self.is_production:
                # In production, we might want to handle this more gracefully
                self._handle_production_error(e)
    
    def _handle_production_error(self, error: Exception):
        """Handle production errors more gracefully."""
        try:
            # Track the error itself
            error_event = {
                "name": "analytics_error",
                "params": {
                    "error_type": error.__class__.__name__,
                    "error_message": str(error),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Try to send error event with basic request
            requests.post(
                self.base_url,
                json={"client_id": "system", "events": [error_event]}
            )
        except:
            # If even error tracking fails, just log it
            logger.exception("Failed to track analytics error")

    def track_session_start(self, user_id: str, platform: str = "telegram"):
        """Track session start."""
        self.track_event(
            name="session_start",
            user_id=user_id,
            params={
                "platform": platform,
                "session_id": f"{user_id}_{int(datetime.now().timestamp())}"
            }
        )

    def track_user_engagement(self, user_id: str, feature: str, engagement_time_msec: int):
        """Track user engagement time with specific features."""
        self.track_event(
            name="user_engagement",
            user_id=user_id,
            params={
                "feature": feature,
                "engagement_time_msec": engagement_time_msec
            }
        )

    def track_search(self, user_id: str, query: str, success: bool, results_count: int = 0):
        """Track search events with enhanced parameters."""
        self.track_event(
            name="search",
            user_id=user_id,
            params={
                "search_term": query,
                "success": success,
                "results_count": results_count,
                "search_type": self._determine_search_type(query)
            }
        )

    def _determine_search_type(self, query: str) -> str:
        """Determine the type of search query."""
        query = query.strip().upper()
        if any(query.startswith(prefix) for prefix in ['A', 'B', 'C']) and len(query) <= 4:
            return "publisher_code"
        elif any(x in query.lower() for x in ['قاعة', 'hall']):
            return "hall_number"
        return "publisher_name"

    def track_publisher_interaction(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None):
        """Track publisher-related interactions."""
        self.track_event(
            name="publisher_interaction",
            user_id=user_id,
            params={
                "publisher_code": publisher_code,
                "publisher_name": publisher_name,
                "action": action  # view, bookmark, unbookmark
            }
        )

    def track_map_interaction(self, user_id: str, hall_number: int, action: str, section: str = None):
        """Track map-related interactions."""
        params = {
            "hall_number": hall_number,
            "action": action  # view, zoom, section_select
        }
        if section:
            params["section"] = section
            
        self.track_event(
            name="map_interaction",
            user_id=user_id,
            params=params
        )

    def track_navigation(self, user_id: str, from_screen: str, to_screen: str):
        """Track user navigation patterns."""
        self.track_event(
            name="screen_navigation",
            user_id=user_id,
            params={
                "from_screen": from_screen,
                "to_screen": to_screen
            }
        )

    def track_error(self, user_id: str, error_type: str, error_message: str):
        """Track error occurrences."""
        self.track_event(
            name="error",
            user_id=user_id,
            params={
                "error_type": error_type,
                "error_message": error_message
            }
        )

    def track_language_preference(self, user_id: str, is_arabic: bool):
        """Track user language preferences."""
        self.track_event(
            name="language_preference",
            user_id=user_id,
            params={
                "language": "arabic" if is_arabic else "english"
            }
        )

    def track_feature_use(self, user_id: str, feature: str, sub_feature: str = None):
        """Track feature usage."""
        params = {"feature": feature}
        if sub_feature:
            params["sub_feature"] = sub_feature
            
        self.track_event(
            name="feature_use",
            user_id=user_id,
            params=params
        )

    def track_bookmark_action(self, user_id: str, publisher_code: str, action: str):
        """Track bookmark-related actions."""
        self.track_event(
            name="bookmark_action",
            user_id=user_id,
            params={
                "publisher_code": publisher_code,
                "action": action  # add, remove
            }
        )

    def track_performance(self, user_id: str, operation: str, duration_ms: float):
        """Track performance metrics."""
        self.track_event(
            name="performance",
            user_id=user_id,
            params={
                "operation": operation,
                "duration_ms": duration_ms
            }
        ) 