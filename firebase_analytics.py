import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FirebaseAnalytics:
    def __init__(self, measurement_id: str = None, api_secret: str = None):
        """Initialize Firebase Analytics using GA4 Measurement Protocol."""
        self.measurement_id = measurement_id or "G-YXYW98YTGK"  # Your GA4 measurement ID
        self.api_secret = api_secret or "AY5E-r5qR4avF9pu_ii_BA"  # Your GA4 API secret
        self.base_url = "https://www.google-analytics.com/mp/collect"
        logger.info("Firebase Analytics initialized with GA4 Measurement Protocol")

    def track_event(self, user_id: str, event_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Track a single event using GA4 Measurement Protocol."""
        try:
            url = f"{self.base_url}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
            
            payload = {
                "client_id": user_id,
                "user_id": user_id,
                "timestamp_micros": int(datetime.now().timestamp() * 1_000_000),
                "events": [{
                    "name": event_name,
                    "params": params or {}
                }]
            }

            response = requests.post(url, json=payload)
            if response.status_code == 204:
                logger.info(f"Successfully tracked event {event_name} for user {user_id}")
                return True
            else:
                logger.error(f"Error tracking event {event_name}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error tracking event {event_name}: {e}")
            return False

    def track_search(self, user_id: str, query: str, results_count: int, success: bool) -> bool:
        """Track search events."""
        return self.track_event(
            user_id=user_id,
            event_name="search",
            params={
                "search_term": query,
                "results_count": results_count,
                "success": success
            }
        )

    def track_publisher_view(self, user_id: str, publisher_code: str, hall_number: int) -> bool:
        """Track publisher view events."""
        return self.track_event(
            user_id=user_id,
            event_name="publisher_view",
            params={
                "publisher_code": publisher_code,
                "hall_number": hall_number
            }
        )

    def track_favorite_action(self, user_id: str, publisher_code: str, action: str) -> bool:
        """Track favorite add/remove events."""
        return self.track_event(
            user_id=user_id,
            event_name="favorite_action",
            params={
                "publisher_code": publisher_code,
                "action": action  # "add" or "remove"
            }
        )

    def track_map_view(self, user_id: str, hall_number: int, section: Optional[str] = None) -> bool:
        """Track map view events."""
        params = {"hall_number": hall_number}
        if section:
            params["section"] = section
        return self.track_event(
            user_id=user_id,
            event_name="map_view",
            params=params
        )

    def track_error(self, user_id: str, error_type: str, error_message: str) -> bool:
        """Track error events."""
        return self.track_event(
            user_id=user_id,
            event_name="error",
            params={
                "error_type": error_type,
                "error_message": error_message
            }
        )

    def track_session_start(self, user_id: str, platform: str, language: str) -> bool:
        """Track session start events."""
        return self.track_event(
            user_id=user_id,
            event_name="session_start",
            params={
                "platform": platform,
                "language": language
            }
        )

    def track_navigation(self, user_id: str, from_screen: str, to_screen: str) -> bool:
        """Track navigation between screens."""
        return self.track_event(
            user_id=user_id,
            event_name="screen_view",
            params={
                "from_screen": from_screen,
                "to_screen": to_screen
            }
        )

    def track_feature_use(self, user_id: str, feature: str) -> bool:
        """Track feature usage."""
        return self.track_event(
            user_id=user_id,
            event_name="feature_use",
            params={
                "feature_name": feature
            }
        )

    def track_user_engagement(self, user_id: str, feature: str, engagement_time_msec: int) -> bool:
        """Track user engagement time."""
        return self.track_event(
            user_id=user_id,
            event_name="user_engagement",
            params={
                "feature": feature,
                "engagement_time_msec": engagement_time_msec
            }
        )

    def track_bookmark_action(self, user_id: str, publisher_code: str, action: str) -> bool:
        """Track bookmark actions."""
        return self.track_event(
            user_id=user_id,
            event_name="bookmark_action",
            params={
                "publisher_code": publisher_code,
                "action": action
            }
        ) 