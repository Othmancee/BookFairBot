import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self):
        self.analytics_dir = "/tmp/data/analytics"
        self.today_file = f"{self.analytics_dir}/{datetime.now().strftime('%Y-%m-%d')}.json"
        self._ensure_dirs()
        self.current_data = self._load_today()
        
    def _ensure_dirs(self):
        """Ensure analytics directory exists."""
        Path(self.analytics_dir).mkdir(parents=True, exist_ok=True)
        
    def _load_today(self) -> Dict:
        """Load today's analytics data."""
        if os.path.exists(self.today_file):
            try:
                with open(self.today_file, 'r') as f:
                    data = json.load(f)
                    # Convert unique_users back to set
                    if "unique_users" in data:
                        data["unique_users"] = set(data["unique_users"])
                    return data
            except:
                return self._get_empty_data()
        return self._get_empty_data()
    
    def _get_empty_data(self) -> Dict:
        """Get empty analytics data structure."""
        return {
            "total_searches": 0,
            "total_users": 0,
            "unique_users": set(),
            "search_terms": {},
            "popular_publishers": {},
            "features_used": {
                "search": 0,
                "maps": 0,
                "favorites": 0,
                "events": 0
            },
            "errors": 0,
            "halls_viewed": {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
            },
            "user_sessions": {},  # Track user session lengths
            "peak_hours": defaultdict(int),  # Track usage by hour
            "search_success_rate": {
                "successful": 0,
                "failed": 0
            },
            "favorite_actions": {
                "added": 0,
                "removed": 0
            },
            "navigation_flows": [],  # Track user navigation patterns
            "user_retention": {
                "returning_users": set(),
                "total_returns": 0
            },
            "response_times": [],  # Track bot response times
            "user_engagement": {},  # Track time spent per feature
            "search_categories": {
                "by_name": 0,
                "by_code": 0,
                "by_hall": 0
            }
        }
    
    def _save_data(self):
        """Save analytics data to file."""
        try:
            # Convert set to list for JSON serialization
            data_to_save = self.current_data.copy()
            data_to_save["unique_users"] = list(self.current_data["unique_users"])
            data_to_save["user_retention"]["returning_users"] = list(
                self.current_data["user_retention"]["returning_users"]
            )
            
            with open(self.today_file, 'w') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving analytics: {e}")
    
    def track_search(self, user_id: int, search_term: str, success: bool = False):
        """Track a search attempt with success indicator."""
        self.current_data["total_searches"] += 1
        
        # Track unique users
        self.current_data["unique_users"].add(str(user_id))
        self.current_data["total_users"] = len(self.current_data["unique_users"])
        
        # Track search terms
        if search_term in self.current_data["search_terms"]:
            self.current_data["search_terms"][search_term] += 1
        else:
            self.current_data["search_terms"][search_term] = 1
        
        # Track search success
        if success:
            self.current_data["search_success_rate"]["successful"] += 1
        else:
            self.current_data["search_success_rate"]["failed"] += 1
        
        # Categorize search type
        if search_term.startswith(('A', 'B', 'C')) and len(search_term) <= 4:
            self.current_data["search_categories"]["by_code"] += 1
        elif "قاعة" in search_term or "hall" in search_term.lower():
            self.current_data["search_categories"]["by_hall"] += 1
        else:
            self.current_data["search_categories"]["by_name"] += 1
            
        # Track peak hours
        current_hour = datetime.now().hour
        self.current_data["peak_hours"][str(current_hour)] += 1
        
        self.current_data["features_used"]["search"] += 1
        self._save_data()
    
    def track_user_session(self, user_id: int, duration: float):
        """Track user session duration."""
        user_id_str = str(user_id)
        if user_id_str not in self.current_data["user_sessions"]:
            self.current_data["user_sessions"][user_id_str] = []
        self.current_data["user_sessions"][user_id_str].append(duration)
        self._save_data()
    
    def track_user_return(self, user_id: int):
        """Track returning users."""
        user_id_str = str(user_id)
        if user_id_str in self.current_data["unique_users"]:
            self.current_data["user_retention"]["returning_users"].add(user_id_str)
            self.current_data["user_retention"]["total_returns"] += 1
        self._save_data()
    
    def track_navigation_flow(self, user_id: int, from_feature: str, to_feature: str):
        """Track user navigation patterns."""
        self.current_data["navigation_flows"].append({
            "user_id": str(user_id),
            "from": from_feature,
            "to": to_feature,
            "timestamp": datetime.now().isoformat()
        })
        self._save_data()
    
    def track_response_time(self, duration: float):
        """Track bot response times."""
        self.current_data["response_times"].append({
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
        self._save_data()
    
    def track_feature_engagement(self, user_id: int, feature: str, duration: float):
        """Track time spent on each feature."""
        user_id_str = str(user_id)
        if user_id_str not in self.current_data["user_engagement"]:
            self.current_data["user_engagement"][user_id_str] = {}
        
        if feature not in self.current_data["user_engagement"][user_id_str]:
            self.current_data["user_engagement"][user_id_str][feature] = []
        
        self.current_data["user_engagement"][user_id_str][feature].append({
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
        self._save_data()
    
    def track_favorite_action(self, action: str):
        """Track favorite add/remove actions."""
        if action in ["added", "removed"]:
            self.current_data["favorite_actions"][action] += 1
            self._save_data()
    
    def track_publisher_view(self, publisher_code: str):
        """Track when a publisher is viewed."""
        if publisher_code in self.current_data["popular_publishers"]:
            self.current_data["popular_publishers"][publisher_code] += 1
        else:
            self.current_data["popular_publishers"][publisher_code] = 1
        self._save_data()
    
    def track_feature_use(self, feature: str):
        """Track feature usage."""
        if feature in self.current_data["features_used"]:
            self.current_data["features_used"][feature] += 1
            self._save_data()
    
    def track_hall_view(self, hall_number: str):
        """Track hall map views."""
        if hall_number in self.current_data["halls_viewed"]:
            self.current_data["halls_viewed"][hall_number] += 1
            self._save_data()
    
    def track_error(self):
        """Track error occurrence."""
        self.current_data["errors"] += 1
        self._save_data()
    
    def get_daily_stats(self) -> Dict:
        """Get comprehensive analytics for the current day."""
        stats = {
            "total_searches": self.current_data["total_searches"],
            "total_users": self.current_data["total_users"],
            "search_success_rate": {
                "successful": self.current_data["search_success_rate"]["successful"],
                "failed": self.current_data["search_success_rate"]["failed"],
                "rate": (self.current_data["search_success_rate"]["successful"] /
                        (self.current_data["total_searches"] or 1)) * 100
            },
            "most_searched": sorted(
                self.current_data["search_terms"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "most_viewed_publishers": sorted(
                self.current_data["popular_publishers"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "feature_usage": self.current_data["features_used"],
            "hall_views": self.current_data["halls_viewed"],
            "peak_hours": dict(sorted(
                self.current_data["peak_hours"].items(),
                key=lambda x: int(x[1]),
                reverse=True
            )),
            "search_categories": self.current_data["search_categories"],
            "favorite_actions": self.current_data["favorite_actions"],
            "user_retention": {
                "returning_users_count": len(self.current_data["user_retention"]["returning_users"]),
                "total_returns": self.current_data["user_retention"]["total_returns"]
            },
            "errors": self.current_data["errors"]
        }
        
        # Calculate average response time
        if self.current_data["response_times"]:
            response_times = [r["duration"] for r in self.current_data["response_times"]]
            stats["average_response_time"] = sum(response_times) / len(response_times)
        
        return stats 