"""
Google Analytics 4 (GA4) integration for the Book Fair Bot.
This module provides analytics tracking, reporting, and setup functionality.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
import logging
from dotenv import load_dotenv
import requests
import time
import pytz
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
    Filter,
    FilterExpression
)
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import (
    CustomDimension,
    CustomMetric,
    ConversionEvent
)
from google.oauth2 import service_account
import base64
import ast
import tempfile

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class GA4Setup:
    """Setup and configuration for GA4 custom dimensions and metrics."""
    
    def __init__(self):
        """Initialize GA4 setup with property ID."""
        self.property_id = os.getenv('GA4_PROPERTY_ID')
        if not self.property_id:
            raise ValueError("GA4_PROPERTY_ID environment variable is required")
        
        # Set up credentials
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if not credentials_json:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is required")
        
        try:
            self.credentials_info = json.loads(credentials_json)
            self.credentials = service_account.Credentials.from_service_account_info(
                self.credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/analytics.edit',
                    'https://www.googleapis.com/auth/analytics.readonly'
                ]
            )
            self.admin_client = AnalyticsAdminServiceClient(credentials=self.credentials)
            self.property_path = f"properties/{self.property_id}"
            print(f"Initialized GA4 setup for property {self.property_id}")
        except Exception as e:
            print(f"Error initializing GA4 setup: {e}")
            raise

    def setup_custom_dimensions(self):
        """Set up custom dimensions in GA4."""
        print("\nSetting up custom dimensions...")
        
        dimensions = [
            ("Publisher Code", "publisher_code", "Publisher unique identifier"),
            ("Publisher Name", "publisher_name", "Name of the publisher"),
            ("Hall Number", "hall_number", "Exhibition hall number"),
            ("Search Success", "search_success", "Whether search returned results"),
            ("Feature Name", "feature_name", "Name of the feature used")
        ]
        
        for display_name, param_name, description in dimensions:
            try:
                dimension = CustomDimension(
                    display_name=display_name,
                    parameter_name=param_name,
                    description=description,
                    scope=CustomDimension.DimensionScope.EVENT
                )
                self.admin_client.create_custom_dimension(
                    parent=self.property_path,
                    custom_dimension=dimension
                )
                print(f"✓ Created custom dimension: {display_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"ℹ Dimension already exists: {display_name}")
                else:
                    print(f"✗ Error creating dimension {display_name}: {e}")

    def setup_custom_metrics(self):
        """Set up custom metrics in GA4."""
        print("\nSetting up custom metrics...")
        
        metrics = [
            ("Search Results Count", "search_results_count", "Number of results returned by search", "STANDARD"),
            ("Engagement Duration", "engagement_duration", "Time spent using a feature", "MILLISECONDS")
        ]
        
        for display_name, param_name, description, unit in metrics:
            try:
                metric = CustomMetric(
                    display_name=display_name,
                    parameter_name=param_name,
                    description=description,
                    measurement_unit=CustomMetric.MeasurementUnit[unit],
                    scope=CustomMetric.MetricScope.EVENT
                )
                self.admin_client.create_custom_metric(
                    parent=self.property_path,
                    custom_metric=metric
                )
                print(f"✓ Created custom metric: {display_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"ℹ Metric already exists: {display_name}")
                else:
                    print(f"✗ Error creating metric {display_name}: {e}")

    def setup_conversions(self):
        """Set up event conversions in GA4."""
        print("\nSetting up event conversions...")
        
        conversions = [
            ("bookmark_action", "Bookmark actions"),
            ("publisher_interaction", "Publisher interactions"),
            ("search", "Successful searches")
        ]
        
        for event_name, description in conversions:
            try:
                conversion_event = ConversionEvent(
                    event_name=event_name,
                    custom=True
                )
                self.admin_client.create_conversion_event(
                    parent=self.property_path,
                    conversion_event=conversion_event
                )
                print(f"✓ Marked as conversion: {event_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"ℹ Conversion already exists: {event_name}")
                else:
                    print(f"✗ Error setting up conversion {event_name}: {e}")

    def setup_all(self):
        """Run complete GA4 setup."""
        print("Starting complete GA4 setup...")
        
        self.setup_custom_dimensions()
        self.setup_custom_metrics()
        self.setup_conversions()
        
        print("\nGA4 setup complete! You can now use these in the GA4 dashboard:")
        print("\nCustom Dimensions:")
        print("- Publisher Code (customEvent:publisher_code)")
        print("- Publisher Name (customEvent:publisher_name)")
        print("- Hall Number (customEvent:hall_number)")
        print("- Search Success (customEvent:search_success)")
        print("- Feature Name (customEvent:feature_name)")
        
        print("\nCustom Metrics:")
        print("- Search Results Count (customEvent:search_results_count)")
        print("- Engagement Duration (customEvent:engagement_duration)")
        
        print("\nConversion Events:")
        print("- bookmark_action")
        print("- publisher_interaction")
        print("- search")
        
        print("\nRecommended Reports to Create:")
        print("1. Publisher Interactions Report")
        print("   - Dimensions: publisher_name, publisher_code, hall_number")
        print("   - Metrics: eventCount, engagement_duration")
        print("   - Filter: eventName = publisher_interaction")
        
        print("\n2. Search Analytics Report")
        print("   - Dimensions: searchTerm, search_success")
        print("   - Metrics: eventCount, search_results_count")
        print("   - Filter: eventName = search")
        
        print("\n3. Bookmark Actions Report")
        print("   - Dimensions: publisher_name, publisher_code, action")
        print("   - Metrics: eventCount")
        print("   - Filter: eventName = bookmark_action")
        
        print("\n4. Feature Usage Report")
        print("   - Dimensions: feature_name")
        print("   - Metrics: eventCount, engagement_duration")
        print("   - Filter: eventName = feature_use")
        
        print("\nPlease create these reports manually in the GA4 dashboard.")

class GA4Reports:
    """GA4 reporting functionality for retrieving analytics data."""
    
    def __init__(self):
        """Initialize GA4 client with service account credentials."""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
            
        if not os.path.exists(credentials_path):
            raise ValueError(f"Credentials file not found at {credentials_path}")
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        property_id = os.getenv('GA4_PROPERTY_ID')
        if not property_id:
            raise ValueError("GA4_PROPERTY_ID environment variable not set")
            
        self.property = f"properties/{property_id}"
        self.client = BetaAnalyticsDataClient(credentials=credentials)

    def run_report(self, dimensions, metrics, days=7, dimension_filter=None):
        """Run a GA4 report with specified dimensions and metrics."""
        request = RunReportRequest(
            property=self.property,
            dimensions=dimensions,
            metrics=metrics,
            date_ranges=[DateRange(
                start_date=f"{days}daysAgo",
                end_date="today"
            )],
            dimension_filter=dimension_filter
        )
        return self.client.run_report(request)

    def print_report_data(self, response, report_name):
        """Print the report data in a readable format."""
        print(f"\n{report_name} Results:")
        print("-" * 50)
        
        if not response.rows:
            print("No data available for this period")
            return
            
        # Print header
        header = []
        for dimension in response.dimension_headers:
            header.append(dimension.name)
        for metric in response.metric_headers:
            header.append(metric.name)
        print(" | ".join(header))
        print("-" * 50)
        
        # Print data rows
        for row in response.rows:
            row_values = []
            for dimension_value in row.dimension_values:
                row_values.append(dimension_value.value or "(unknown)")
            for metric_value in row.metric_values:
                row_values.append(metric_value.value)
            print(" | ".join(row_values))

    def get_search_analytics(self):
        """Get search analytics data."""
        dimensions = [
            Dimension(name="eventName"),
            Dimension(name="searchTerm")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="eventValue")
        ]
        try:
            dimension_filter = FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter={"value": "search"}
                )
            )
            response = self.run_report(dimensions, metrics, dimension_filter=dimension_filter)
            self.print_report_data(response, "Search Analytics")
            return response
        except Exception as e:
            print(f"Error getting search analytics: {str(e)}")

    def get_publisher_analytics(self):
        """Get publisher interaction analytics."""
        dimensions = [
            Dimension(name="eventName"),
            Dimension(name="customEvent:publisher_code"),
            Dimension(name="customEvent:publisher_name"),
            Dimension(name="customEvent:hall_number"),
            Dimension(name="customEvent:feature_name"),
            Dimension(name="platform")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="customEvent:engagement_duration")
        ]
        try:
            dimension_filter = FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter={"value": "publisher_interaction"}
                )
            )
            response = self.run_report(dimensions, metrics, dimension_filter=dimension_filter)
            self.print_report_data(response, "Publisher Analytics")
            return response
        except Exception as e:
            print(f"Error getting publisher analytics: {str(e)}")

    def get_bookmark_analytics(self):
        """Get bookmark action analytics."""
        dimensions = [
            Dimension(name="eventName"),
            Dimension(name="customEvent:publisher_code"),
            Dimension(name="customEvent:publisher_name"),
            Dimension(name="platform")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="customEvent:engagement_duration")
        ]
        try:
            dimension_filter = FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter={"value": "bookmark_action"}
                )
            )
            response = self.run_report(dimensions, metrics, dimension_filter=dimension_filter)
            self.print_report_data(response, "Bookmark Analytics")
            return response
        except Exception as e:
            print(f"Error getting bookmark analytics: {str(e)}")

    def get_feature_usage(self):
        """Get feature usage analytics."""
        dimensions = [
            Dimension(name="eventName"),
            Dimension(name="customEvent:feature_name"),
            Dimension(name="platform")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="customEvent:engagement_duration")
        ]
        try:
            dimension_filter = FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter={"value": "feature_use"}
                )
            )
            response = self.run_report(dimensions, metrics, dimension_filter=dimension_filter)
            self.print_report_data(response, "Feature Usage")
            return response
        except Exception as e:
            print(f"Error getting feature usage: {str(e)}")

    def get_error_analytics(self):
        """Get error analytics data."""
        dimensions = [
            Dimension(name="eventName")
        ]
        metrics = [
            Metric(name="eventCount")
        ]
        try:
            dimension_filter = FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter={"value": "error"}
                )
            )
            response = self.run_report(dimensions, metrics, dimension_filter=dimension_filter)
            self.print_report_data(response, "Error Analytics")
            return response
        except Exception as e:
            print(f"Error getting error analytics: {str(e)}")

class GA4Analytics:
    def __init__(self):
        """Initialize GA4 Analytics using Measurement Protocol."""
        self.measurement_id = os.getenv('GA4_MEASUREMENT_ID')
        self.api_secret = os.getenv('GA4_API_SECRET')
        if not self.measurement_id or not self.api_secret:
            raise ValueError("GA4_MEASUREMENT_ID and GA4_API_SECRET environment variables are required")
        
        self.base_url = "https://www.google-analytics.com/mp/collect"
        self.is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
        self.debug = os.getenv('GA4_DEBUG', 'false').lower() == 'true'
        logger.info("GA4 Analytics initialized with Measurement Protocol")

    def track_event(self, name: str, user_id: str, params: Optional[Dict[str, Any]] = None):
        """Send event to GA4."""
        try:
            event_params = params or {}
            
            # Format custom dimensions and metrics with customEvent: prefix
            custom_params = {}
            
            # List of known custom dimensions and metrics
            custom_fields = {
                'feature_name': 'customEvent:feature_name',
                'publisher_code': 'customEvent:publisher_code',
                'publisher_name': 'customEvent:publisher_name',
                'hall_number': 'customEvent:hall_number',
                'engagement_duration': 'customEvent:engagement_duration',
                'search_results_count': 'customEvent:search_results_count',
                'search_success': 'customEvent:search_success'
            }
            
            # First, handle custom dimensions and metrics
            for key, value in event_params.items():
                if key in custom_fields:
                    if value is not None:  # Only include non-None values
                        custom_params[custom_fields[key]] = value
                else:
                    custom_params[key] = value

            # Ensure feature_name is always set
            if 'feature_name' not in event_params:
                custom_params['customEvent:feature_name'] = name

            # Add standard parameters
            custom_params.update({
                "timestamp_micros": int(datetime.now().timestamp() * 1000000),
                "environment": "production" if self.is_production else "development"
            })

            # Add session context
            session_params = self._get_base_params(user_id)
            custom_params.update(session_params)

            event_data = {
                "client_id": user_id,
                "user_id": user_id,
                "events": [{
                    "name": name,
                    "params": custom_params
                }]
            }
            
            # Always log in debug mode
            if self.debug:
                logger.info(f"GA4 Event: {name}")
                logger.info(f"Event Data: {json.dumps(event_data, ensure_ascii=False, indent=2)}")
            
            # In production, send the event
            if self.is_production:
                response = requests.post(
                    self.base_url,
                    json=event_data
                )
                
                if response.status_code != 204:
                    logger.error(f"Error sending event to GA4: {response.status_code} - {response.text}")
                    return False
                elif self.debug:
                    logger.debug(f"Successfully sent event {name} to GA4")
                return True
            
            return True
                
        except Exception as e:
            logger.error(f"Error sending event to GA4: {e}")
            if self.is_production:
                self._handle_production_error(e)
            return False

    def track_search(self, user_id: str, query: str, results_count: int, success: bool) -> bool:
        """Track search events."""
        return self.track_event(
            name="search",
            user_id=user_id,
            params={
                "feature_name": "search",
                "search_term": query,
                "search_results_count": results_count,
                "search_success": success,
                "query_type": self._determine_search_type(query),
                "search_category": self._determine_search_category(query)
            }
        )

    def track_publisher_interaction(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None, hall_number: int = None) -> bool:
        """Track publisher interaction events."""
        params = {
            "feature_name": "publisher_info",
            "publisher_code": publisher_code,
            "action": action
        }
        if publisher_name:
            params["publisher_name"] = publisher_name
        if hall_number:
            params["hall_number"] = hall_number
        return self.track_event(
            name="publisher_interaction",
            user_id=user_id,
            params=params
        )

    def track_map_interaction(self, user_id: str, hall_number: int, section: Optional[str] = None) -> bool:
        """Track map interaction events."""
        params = {
            "feature_name": "map_view",
            "hall_number": hall_number
        }
        if section:
            params["section"] = section
        return self.track_event(
            name="map_interaction",
            user_id=user_id,
            params=params
        )

    def track_error(self, user_id: str, error_type: str, error_message: str) -> bool:
        """Track error events."""
        return self.track_event(
            name="error",
            user_id=user_id,
            params={
                "feature_name": "error_handling",
                "error_type": error_type,
                "error_message": error_message
            }
        )

    def track_session_start(self, user_id: str, platform: str, language: str) -> bool:
        """Track session start events."""
        return self.track_event(
            name="session_start",
            user_id=user_id,
            params={
                "feature_name": "session",
                "platform": platform,
                "language": language
            }
        )

    def track_navigation(self, user_id: str, from_screen: str, to_screen: str) -> bool:
        """Track navigation between screens."""
        return self.track_event(
            name="screen_navigation",
            user_id=user_id,
            params={
                "feature_name": "navigation",
                "from_screen": from_screen,
                "to_screen": to_screen
            }
        )

    def track_bookmark_action(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None) -> None:
        """Track bookmark actions."""
        params = {
            "feature_name": "bookmarks",
            "publisher_code": publisher_code,
            "action": action
        }
        if publisher_name:
            params["publisher_name"] = publisher_name
        self.track_event(
            name="bookmark_action",
            user_id=user_id,
            params=params
        )

    def track_feature_use(self, user_id: str, feature: str) -> None:
        """Track feature usage events."""
        params = {
            "feature_name": feature
        }
        self.track_event(
            name="feature_use",
            user_id=user_id,
            params=params
        )

    def track_user_engagement(self, user_id: str, feature: str, engagement_time_msec: int) -> bool:
        """Track user engagement time."""
        return self.track_event(
            name="user_engagement",
            user_id=user_id,
            params={
                "feature_name": feature,
                "engagement_duration": engagement_time_msec
            }
        )

    def track_performance(self, user_id: str, metric_name: str, value: float) -> bool:
        """Track performance metrics."""
        return self.track_event(
            name="performance",
            user_id=user_id,
            params={
                "feature_name": "performance",
                "metric_name": metric_name,
                "value": value
            }
        )

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
            event_params = params or {}
            
            # Format custom dimensions and metrics with customEvent: prefix
            custom_params = {}
            
            # List of known custom dimensions and metrics
            custom_fields = {
                'feature_name': 'customEvent:feature_name',
                'publisher_code': 'customEvent:publisher_code',
                'publisher_name': 'customEvent:publisher_name',
                'hall_number': 'customEvent:hall_number',
                'engagement_duration': 'customEvent:engagement_duration',
                'search_results_count': 'customEvent:search_results_count',
                'search_success': 'customEvent:search_success'
            }
            
            # First, handle custom dimensions and metrics
            for key, value in event_params.items():
                if key in custom_fields:
                    if value is not None:  # Only include non-None values
                        custom_params[custom_fields[key]] = value
                else:
                    custom_params[key] = value

            # Ensure feature_name is always set
            if 'feature_name' not in event_params:
                custom_params['customEvent:feature_name'] = name

            # Add standard parameters
            custom_params.update({
                "timestamp_micros": int(datetime.now().timestamp() * 1000000),
                "environment": "production" if self.is_production else "development"
            })

            # Add session context
            session_params = self._get_base_params(user_id)
            custom_params.update(session_params)

            event_data = {
                "client_id": user_id,
                "user_id": user_id,
                "events": [{
                    "name": name,
                    "params": custom_params
                }]
            }
            
            # Always log in debug mode
            if self.debug:
                logger.info(f"GA4 Event: {name}")
                logger.info(f"Event Data: {json.dumps(event_data, ensure_ascii=False, indent=2)}")
            
            # In production, send the event
            if self.is_production:
                response = requests.post(
                    self.base_url,
                    json=event_data
                )
                
                if response.status_code != 204:
                    logger.error(f"Error sending event to GA4: {response.status_code} - {response.text}")
                    return False
                elif self.debug:
                    logger.debug(f"Successfully sent event {name} to GA4")
                return True
            
            return True
                
        except Exception as e:
            logger.error(f"Error sending event to GA4: {e}")
            if self.is_production:
                self._handle_production_error(e)
            return False

    def track_search(self, user_id: str, query: str, results_count: int, success: bool) -> None:
        """Track search events with enhanced parameters."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'search',  # Custom dimension
            'search_term': query,  # Custom dimension
            'search_results_count': results_count,  # Custom metric
            'search_success': success,  # Custom dimension
            'query_length': len(query),
            'query_language': 'arabic' if any('\u0600' <= c <= '\u06FF' for c in query) else 'english'
        }
        self.track_event('search', user_id, params)

    def track_publisher_interaction(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None, hall_number: int = None) -> None:
        """Track detailed publisher interactions."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'publisher_info',  # Custom dimension
            'publisher_code': publisher_code,  # Custom dimension
            'hall_number': hall_number,  # Custom dimension
            'action': action
        }
        if publisher_name:
            params['publisher_name'] = publisher_name
        self.track_event('publisher_interaction', user_id, params)

    def track_map_interaction(self, user_id: str, hall_number: int, action: str, section: str = None) -> None:
        """Track map viewing and navigation."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'map_view',  # Custom dimension
            'hall_number': hall_number,  # Custom dimension
            'action': action
        }
        if section:
            params['section'] = section
        self.track_event('map_interaction', user_id, params)

    def track_navigation(self, user_id: str, from_screen: str, to_screen: str) -> None:
        """Track user navigation patterns."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'navigation',  # Custom dimension
            'from_screen': from_screen,
            'to_screen': to_screen
        }
        self.track_event('screen_navigation', user_id, params)

    def track_bookmark_action(self, user_id: str, publisher_code: str, action: str, publisher_name: str = None) -> None:
        """Track bookmark actions."""
        params = {
            "feature_name": "bookmarks",
            "publisher_code": publisher_code,
            "action": action
        }
        if publisher_name:
            params["publisher_name"] = publisher_name
        self.track_event(
            name="bookmark_action",
            user_id=user_id,
            params=params
        )

    def track_feature_use(self, user_id: str, feature: str) -> None:
        """Track feature usage events."""
        params = {
            "feature_name": feature
        }
        self.track_event(
            name="feature_use",
            user_id=user_id,
            params=params
        )

    def track_user_engagement(self, user_id: str, feature: str, engagement_time_msec: int) -> bool:
        """Track user engagement time."""
        return self.track_event(
            name="user_engagement",
            user_id=user_id,
            params={
                "feature_name": feature,
                "engagement_duration": engagement_time_msec
            }
        )

    def track_performance(self, user_id: str, operation: str, duration_ms: float) -> None:
        """Track performance metrics."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'performance',  # Custom dimension
            'operation': operation,
            'duration_ms': duration_ms,
            'performance_category': self._get_performance_category(duration_ms)
        }
        self.track_event('performance', user_id, params)

    def track_error(self, user_id: str, error_type: str, error_message: str) -> None:
        """Track application errors with context."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'error_handling',  # Custom dimension
            'error_type': error_type,
            'error_message': error_message
        }
        self.track_event('error', user_id, params)

    def track_session_start(self, user_id: str, platform: str, language: str) -> None:
        """Track session start events."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'session',  # Custom dimension
            'platform': platform,
            'language': language
        }
        self.track_event('session_start', user_id, params)

    def track_language_preference(self, user_id: str, is_arabic: bool) -> None:
        """Track user language preferences."""
        params = {
            **self._get_base_params(user_id),
            'feature_name': 'language',  # Custom dimension
            'language': 'arabic' if is_arabic else 'english'
        }
        self.track_event('language_preference', user_id, params)

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

    def _calculate_engagement_level(self, time_ms: int) -> str:
        if time_ms < 5000:  # 5 seconds
            return 'low'
        elif time_ms < 30000:  # 30 seconds
            return 'medium'
        else:
            return 'high'

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