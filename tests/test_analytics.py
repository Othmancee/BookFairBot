import unittest
import json
import os
import time
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
from analytics import GA4Manager

class TestGA4Manager(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'GA4_MEASUREMENT_ID': 'test_id',
            'GA4_API_SECRET': 'test_secret',
            'GA4_DEBUG': 'true',
            'RAILWAY_ENVIRONMENT': 'development'
        })
        self.env_patcher.start()
        self.ga4 = GA4Manager()
        self.test_user_id = "test_user_123"

    def tearDown(self):
        self.env_patcher.stop()

    def test_search_tracking(self):
        # Test Arabic search
        self.ga4.track_search(self.test_user_id, "دار الشروق", True, 3)
        self.assertEqual(
            self.ga4.user_sessions[self.test_user_id]['actions'][-1],
            'search'
        )
        
        # Test English search
        self.ga4.track_search(self.test_user_id, "ABC Publishers", True, 1)
        
        # Test code search
        self.ga4.track_search(self.test_user_id, "A21", True, 1)
        
        # Test failed search
        self.ga4.track_search(self.test_user_id, "nonexistent", False, 0)

    def test_publisher_interaction(self):
        self.ga4.track_publisher_interaction(
            self.test_user_id,
            "1_A21",
            "view",
            "Test Publisher",
            1
        )
        
        last_action = self.ga4.user_sessions[self.test_user_id]['actions'][-1]
        self.assertEqual(last_action, 'publisher_interaction')

    @patch('builtins.open', new_callable=mock_open, read_data='{"test_user_123": ["1_A21", "2_B22"]}')
    def test_favorites_tracking(self, mock_file):
        # Test adding favorite
        self.ga4.track_bookmark_action(self.test_user_id, "1_A21", "add")
        
        # Test removing favorite
        self.ga4.track_bookmark_action(self.test_user_id, "1_A21", "remove")
        
        # Verify file operations
        mock_file.assert_called_with('data/favorites.json', 'r')

    def test_session_management(self):
        # Test session creation
        session_id = self.ga4._get_session_id(self.test_user_id)
        self.assertIn(self.test_user_id, self.ga4.user_sessions)
        
        # Test session depth
        depth1 = self.ga4._get_session_depth(self.test_user_id)
        depth2 = self.ga4._get_session_depth(self.test_user_id)
        self.assertEqual(depth2, depth1 + 1)

    def test_user_type_classification(self):
        # New user
        user_type = self.ga4._get_user_type("new_user")
        self.assertEqual(user_type, "new")
        
        # Returning user
        self.ga4.session_counts["returning_user"] = 3
        user_type = self.ga4._get_user_type("returning_user")
        self.assertEqual(user_type, "returning")
        
        # Frequent user
        self.ga4.session_counts["frequent_user"] = 10
        user_type = self.ga4._get_user_type("frequent_user")
        self.assertEqual(user_type, "frequent")

    @patch('builtins.open', new_callable=mock_open, read_data='[{"code": "A21"}, {"code": "B22"}]')
    def test_publisher_counting(self, mock_file):
        count = self.ga4._get_hall_publisher_count(1)
        self.assertEqual(count, 2)
        
        # Test section counting
        mock_file.return_value.read.return_value = json.dumps([
            {"code": "A21", "section": "A"},
            {"code": "A22", "section": "A"},
            {"code": "B21", "section": "B"}
        ])
        count = self.ga4._get_section_publisher_count(1, "A")
        self.assertEqual(count, 2)

    def test_performance_tracking(self):
        # Test fast operation
        self.ga4.track_performance(self.test_user_id, "quick_search", 200)
        
        # Test slow operation
        self.ga4.track_performance(self.test_user_id, "complex_search", 1500)
        
        # Verify performance categorization
        self.assertEqual(self.ga4._get_performance_category(200), "fast")
        self.assertEqual(self.ga4._get_performance_category(1500), "slow")

    def test_error_tracking(self):
        self.ga4.track_error(
            self.test_user_id,
            "SearchError",
            "Invalid search query"
        )
        
        last_action = self.ga4.user_sessions[self.test_user_id]['actions'][-1]
        self.assertEqual(last_action, 'error')

    def test_engagement_tracking(self):
        # Test low engagement
        self.ga4.track_user_engagement(self.test_user_id, "search", 3000)
        
        # Test high engagement
        self.ga4.track_user_engagement(self.test_user_id, "map", 35000)
        
        # Verify engagement levels
        self.assertEqual(self.ga4._calculate_engagement_level(3000), "low")
        self.assertEqual(self.ga4._calculate_engagement_level(35000), "high")

    def test_search_categorization(self):
        # Test Arabic publisher name
        self.assertEqual(
            self.ga4._determine_search_type("دار الشروق"),
            "publisher_name_ar"
        )
        
        # Test English publisher name
        self.assertEqual(
            self.ga4._determine_search_type("ABC"),
            "publisher_name_en"
        )
        
        # Test publisher code
        self.assertEqual(
            self.ga4._determine_search_type("A21"),
            "publisher_code"
        )
        
        # Test mixed input
        self.assertEqual(
            self.ga4._determine_search_type("ABC123!"),
            "mixed"
        )

    def test_action_tracking(self):
        # Simulate a sequence of actions
        actions = ['search', 'publisher_interaction', 'bookmark_action']
        for action in actions:
            self.ga4._track_user_action(self.test_user_id, action)
        
        # Test current action
        self.assertEqual(
            self.ga4._get_current_user_action(self.test_user_id),
            'bookmark_action'
        )
        
        # Test previous action
        self.assertEqual(
            self.ga4._get_previous_user_action(self.test_user_id),
            'publisher_interaction'
        )

if __name__ == '__main__':
    unittest.main() 