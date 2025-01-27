import json
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
import logging
from dotenv import load_dotenv
import requests
import time
import pytz

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class GA4Manager:
    def __init__(self):
        """Initialize GA4 client."""
        self.measurement_id = os.getenv('GA4_MEASUREMENT_ID')
        self.api_secret = os.getenv('GA4_API_SECRET')
        self.is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
        self.debug = os.getenv('GA4_DEBUG', 'false').lower() == 'true'
        
        # Initialize session tracking
        self.user_sessions = {}  # {user_id: {'start_time': timestamp, 'depth': count, 'actions': [list]}}
        self.feature_usage = {}  # {user_id: {feature: count}}
        self.session_counts = {}  # {user_id: count}
        
        if not self.measurement_id or not self.api_secret:
            logger.error("GA4 credentials not found in environment variables")
            raise ValueError("GA4_MEASUREMENT_ID and GA4_API_SECRET environment variables are required")
        
        self.base_url = f"https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
        
        if not self.is_production:
            logger.warning("Running in development mode - events will be logged but not sent to GA4")
    
    def _log_event(self, event_name: str, params: Dict) -> None:
        """Log event details for debugging."""
        if self.debug:
            logger.info(f"GA4 Event: {event_name}")
            logger.info(f"Parameters: {json.dumps(params, ensure_ascii=False, indent=2)}")
        
        # Track the action
        if 'user_id' in params:
            self._track_user_action(params['user_id'], event_name)

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
            
            # Always log in debug mode
            if self.debug:
                logger.info(f"GA4 Event: {name}")
                logger.info(f"Event Data: {json.dumps(event_data, indent=2)}")
            
            # In production, send the event
            if self.is_production:
                response = requests.post(
                    self.base_url,
                    json=event_data
                )
                
                if response.status_code != 204:
                    logger.error(f"Failed to send event to GA4: {response.text}")
                elif self.debug:
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

    def track_session_start(self, user_id: str, source: str = 'direct') -> None:
        """Track session starts with context."""
        params = {
            'user_id': user_id,
            'session_id': self._get_session_id(user_id),
            'source': source,
            'user_type': self._get_user_type(user_id),
            'previous_session_count': self._get_previous_session_count(user_id),
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }
        self._log_event('session_start', params)

    def track_user_engagement(self, user_id: str, feature: str, engagement_time_msec: int) -> None:
        """Track detailed user engagement metrics."""
        params = {
            'user_id': user_id,
            'feature': feature,
            'engagement_time_msec': engagement_time_msec,
            'engagement_level': self._calculate_engagement_level(engagement_time_msec),
            'session_id': self._get_session_id(user_id),
            'session_engagement_count': self._get_session_engagement_count(user_id),
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }
        self._log_event('user_engagement', params)

    def _get_base_params(self, user_id: str) -> Dict:
        """Get base parameters included in all events."""
        return {
            'user_id': str(user_id),
            'session_id': self._get_session_id(user_id),
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'platform': 'telegram',
            'environment': 'production' if self.is_production else 'development',
            'user_type': self._get_user_type(user_id),
            'session_count': self._get_previous_session_count(user_id),
            'session_depth': self._get_session_depth(user_id)
        }

    def track_search(self, user_id: str, query: str, success: bool, results_count: int) -> None:
        """Track search events with enhanced parameters."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'search',
            'search_term': query,
            'search_type': self._determine_search_type(query),
            'success': success,
            'results_count': results_count,
            'query_length': len(query),
            'query_language': 'arabic' if any('\u0600' <= c <= '\u06FF' for c in query) else 'english',
            'search_category': self._determine_search_category(query)
        }
        self._log_event('search', params)

    def _determine_search_type(self, query: str) -> str:
        """Determine the type of search query."""
        query = query.strip()
        if any('\u0600' <= c <= '\u06FF' for c in query):
            return 'publisher_name_ar'
        elif query.isascii() and query.isalpha():
            return 'publisher_name_en'
        elif query.isalnum():
            return 'publisher_code'
        return 'mixed'

    def _determine_search_category(self, query: str) -> str:
        """Categorize the search query."""
        query_lower = query.lower()
        if any(x in query_lower for x in ['قاعة', 'hall', 'قاعه']):
            return 'hall_search'
        elif any(x in query_lower for x in ['جناح', 'wing', 'booth']):
            return 'booth_search'
        return 'publisher_search'

    def track_publisher_interaction(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None, hall_number: int = None) -> None:
        """Track detailed publisher interactions."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'publisher_interaction',
            'publisher_code': publisher_code,
            'publisher_name': publisher_name,
            'hall_number': hall_number,
            'action': action,
            'interaction_source': self._get_interaction_source(),
            'favorites_count': len(self._get_user_favorites(user_id)),
            'publisher_details': {
                'code': publisher_code,
                'name': publisher_name,
                'hall': hall_number,
                'section': publisher_code[0] if publisher_code else None
            }
        }
        self._log_event('publisher_interaction', params)

    def track_map_interaction(self, user_id: str, hall_number: int, action: str, section: str = None) -> None:
        """Track map viewing and navigation."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'map_interaction',
            'hall_number': hall_number,
            'section': section,
            'action': action,
            'interaction_type': 'section_view' if section else 'hall_view',
            'map_context': {
                'hall_number': hall_number,
                'section': section,
                'total_publishers': self._get_hall_publisher_count(hall_number),
                'section_publishers': self._get_section_publisher_count(hall_number, section) if section else None
            }
        }
        self._log_event('map_interaction', params)

    def track_navigation(self, user_id: str, from_screen: str, to_screen: str) -> None:
        """Track user navigation patterns."""
        params = {
            'user_id': user_id,
            'from_screen': from_screen,
            'to_screen': to_screen,
            'navigation_type': 'direct' if to_screen == 'start' else 'sequential',
            'session_depth': self._get_session_depth(user_id),
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }
        self._log_event('navigation', params)

    def track_error(self, user_id: str, error_type: str, error_message: str) -> None:
        """Track application errors with context."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'error',
            'error_type': error_type,
            'error_message': error_message,
            'error_context': {
                'error_type': error_type,
                'error_message': error_message,
                'stack_trace': self._get_error_context(),
                'user_action': self._get_current_user_action(user_id),
                'previous_action': self._get_previous_user_action(user_id)
            }
        }
        self._log_event('error', params)

    def track_language_preference(self, user_id: str, is_arabic: bool):
        """Track user language preferences."""
        self.track_event(
            name="language_preference",
            user_id=user_id,
            params={
                "language": "arabic" if is_arabic else "english"
            }
        )

    def track_feature_use(self, user_id: str, feature: str, sub_feature: str = None) -> None:
        """Track feature usage with optional sub-feature."""
        params = {
            'user_id': user_id,
            'feature': feature,
            'timestamp': datetime.now().isoformat()
        }
        if sub_feature:
            params['sub_feature'] = sub_feature
        
        self.track_event('feature_use', user_id, params)

    def track_bookmark_action(self, user_id: str, publisher_code: str, action: str) -> None:
        """Track favorite/bookmark actions with context."""
        current_favorites = self._get_user_favorites(user_id)
        params = {
            **self._get_base_params(user_id),
            'event_type': 'bookmark_action',
            'publisher_code': publisher_code,
            'action': action,
            'favorites_count': len(current_favorites),
            'source': self._get_interaction_source(),
            'bookmark_context': {
                'total_favorites': len(current_favorites),
                'favorites_by_hall': self._get_favorites_by_hall(current_favorites),
                'is_first_favorite': len(current_favorites) == 0
            }
        }
        self._log_event('bookmark_action', params)

    def track_performance(self, user_id: str, operation: str, duration_ms: float) -> None:
        """Track performance metrics."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'performance',
            'operation': operation,
            'duration_ms': duration_ms,
            'performance_category': self._get_performance_category(duration_ms),
            'performance_context': {
                'operation_type': operation,
                'duration_ms': duration_ms,
                'threshold_exceeded': duration_ms > 1000,
                'operation_category': self._get_operation_category(operation)
            }
        }
        self._log_event('performance', params)

    def track_publisher_view(self, user_id: str, publisher_code: str, hall_number: str) -> None:
        """Track when a user views a publisher's details."""
        params = {
            **self._get_base_params(user_id),
            'event_type': 'publisher_view',
            'publisher_code': publisher_code,
            'hall_number': hall_number,
            'view_source': self._get_current_user_action(user_id),
            'view_context': {
                'previous_action': self._get_previous_user_action(user_id),
                'session_depth': self._get_session_depth(user_id)
            }
        }
        self._log_event('publisher_view', params)

    def track_favorite_action(self, user_id: str, publisher_code: str, action: str) -> None:
        """Alias for track_bookmark_action for backward compatibility."""
        self.track_bookmark_action(user_id, publisher_code, action)

    # Helper methods
    def _get_feature_category(self, feature: str) -> str:
        categories = {
            'search': 'discovery',
            'maps': 'navigation',
            'favorites': 'personalization',
            'events': 'information'
        }
        return categories.get(feature, 'other')

    def _calculate_engagement_level(self, time_ms: int) -> str:
        if time_ms < 5000:  # 5 seconds
            return 'low'
        elif time_ms < 30000:  # 30 seconds
            return 'medium'
        else:
            return 'high'

    def _get_error_context(self) -> Dict:
        """Get current context for error tracking."""
        return {
            'timestamp': datetime.now(pytz.UTC).isoformat(),
            'environment': 'production' if self.is_production else 'development'
        }

    def _get_session_id(self, user_id: str) -> str:
        """Get or create a session ID for the user."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'start_time': datetime.now(pytz.UTC),
                'depth': 0,
                'actions': [],
                'session_id': f"{user_id}_{int(time.time())}"
            }
        return self.user_sessions[user_id].get('session_id', f"{user_id}_{int(time.time())}")

    def _get_session_depth(self, user_id: str) -> int:
        """Get the current session depth for the user."""
        if user_id not in self.user_sessions:
            return 0
        self.user_sessions[user_id]['depth'] += 1
        return self.user_sessions[user_id]['depth']

    def _get_feature_usage_count(self, user_id: str, feature: str) -> int:
        """Track how many times a user has used a feature."""
        user_id = str(user_id)
        if user_id not in self.feature_usage:
            self.feature_usage[user_id] = {}
        self.feature_usage[user_id][feature] = self.feature_usage[user_id].get(feature, 0) + 1
        return self.feature_usage[user_id][feature]

    def _get_session_engagement_count(self, user_id: str) -> int:
        """Get the number of engagement events in the current session."""
        if user_id not in self.user_sessions:
            return 0
        return len(self.user_sessions[user_id]['actions'])

    def _get_user_type(self, user_id: str) -> str:
        """Determine the user type based on session count."""
        session_count = self.session_counts.get(user_id, 0)
        if session_count == 0:
            return 'new'
        elif session_count < 5:
            return 'returning'
        return 'frequent'

    def _get_previous_session_count(self, user_id: str) -> int:
        """Get the number of previous sessions for the user."""
        return self.session_counts.get(user_id, 0)

    def _get_user_favorites(self, user_id: str) -> List[str]:
        """Get the user's favorite publishers."""
        try:
            with open('data/favorites.json', 'r') as f:
                favorites = json.load(f)
                return favorites.get(str(user_id), [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _get_interaction_source(self) -> str:
        """Determine the source of interaction."""
        return 'telegram'

    def _get_hall_publisher_count(self, hall_number: int) -> int:
        """Get the number of publishers in a hall."""
        try:
            with open(f'data/hall_{hall_number}.json', 'r') as f:
                publishers = json.load(f)
                return len(publishers)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def _get_section_publisher_count(self, hall_number: int, section: str) -> int:
        """Get the number of publishers in a section."""
        try:
            with open(f'data/hall_{hall_number}.json', 'r') as f:
                publishers = json.load(f)
                return len([p for p in publishers if p.get('section') == section])
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def _get_favorites_by_hall(self, favorites: List[str]) -> Dict[int, int]:
        """Get distribution of favorites by hall."""
        distribution = {}
        for fav in favorites:
            try:
                hall_number = int(fav.split('_')[0])
                distribution[hall_number] = distribution.get(hall_number, 0) + 1
            except (ValueError, IndexError):
                continue
        return distribution

    def _get_performance_category(self, duration_ms: float) -> str:
        if duration_ms < 500:
            return 'fast'
        elif duration_ms < 1000:
            return 'normal'
        elif duration_ms < 2000:
            return 'slow'
        return 'very_slow'

    def _get_operation_category(self, operation: str) -> str:
        categories = {
            'search': 'data_operation',
            'map': 'rendering',
            'favorite': 'data_operation',
            'navigation': 'ui_operation'
        }
        return next((v for k, v in categories.items() if k in operation.lower()), 'other')

    def _get_current_user_action(self, user_id: str) -> str:
        """Get the user's current action."""
        if user_id in self.user_sessions and self.user_sessions[user_id]['actions']:
            return self.user_sessions[user_id]['actions'][-1]
        return 'unknown'

    def _get_previous_user_action(self, user_id: str) -> str:
        """Get the user's previous action."""
        if user_id in self.user_sessions and len(self.user_sessions[user_id]['actions']) > 1:
            return self.user_sessions[user_id]['actions'][-2]
        return 'unknown'

    def _track_user_action(self, user_id: str, action: str) -> None:
        """Track user actions in their session."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'start_time': datetime.now(pytz.UTC),
                'depth': 0,
                'actions': []
            }
        self.user_sessions[user_id]['actions'].append(action) 