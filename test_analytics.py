"""
Tests for GA4 analytics functionality.
Includes both unit tests and live integration tests.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
from datetime import datetime, timedelta
import pytz
from analytics import GA4Manager, GA4Reports, GA4Setup

class TestGA4Analytics(unittest.TestCase):
    """Unit tests for GA4 analytics functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.analytics = GA4Manager()
        self.test_user_id = "test_user_123"
        
    def test_get_session_id(self):
        """Test session ID generation."""
        session_id1 = self.analytics._get_session_id(self.test_user_id)
        session_id2 = self.analytics._get_session_id(self.test_user_id)
        self.assertEqual(session_id1, session_id2)  # Same user should get same session ID
        self.assertTrue(isinstance(session_id1, str))
        
    @patch('requests.post')
    def test_track_search(self, mock_post):
        """Test search event tracking."""
        mock_post.return_value.status_code = 204
        
        self.analytics.track_search(
            user_id=self.test_user_id,
            query="test query",
            results_count=5,
            success=True
        )
        
        # Verify the POST request
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        
        # Verify payload
        payload = call_args['json']
        self.assertEqual(payload['events'][0]['name'], 'search')
        self.assertEqual(payload['events'][0]['params']['search_term'], 'test query')
        self.assertEqual(payload['events'][0]['params']['customEvent:search_results_count'], 5)
        self.assertEqual(payload['events'][0]['params']['customEvent:search_success'], True)
        self.assertEqual(payload['events'][0]['params']['customEvent:feature_name'], 'search')
        
    @patch('requests.post')
    def test_track_publisher_interaction(self, mock_post):
        """Test publisher interaction event tracking."""
        mock_post.return_value.status_code = 204
        
        self.analytics.track_publisher_interaction(
            user_id=self.test_user_id,
            publisher_code="PUB123",
            action="view",
            publisher_name="Test Publisher",
            hall_number=1
        )
        
        # Verify the POST request
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        
        # Verify payload
        payload = call_args['json']
        self.assertEqual(payload['events'][0]['name'], 'publisher_interaction')
        self.assertEqual(payload['events'][0]['params']['customEvent:publisher_code'], 'PUB123')
        self.assertEqual(payload['events'][0]['params']['customEvent:publisher_name'], 'Test Publisher')
        self.assertEqual(payload['events'][0]['params']['customEvent:hall_number'], 1)
        self.assertEqual(payload['events'][0]['params']['action'], 'view')
        self.assertEqual(payload['events'][0]['params']['customEvent:feature_name'], 'publisher_info')
        
    @patch('requests.post')
    def test_track_bookmark_action(self, mock_post):
        """Test bookmark action event tracking."""
        mock_post.return_value.status_code = 204
        
        self.analytics.track_bookmark_action(
            user_id=self.test_user_id,
            action="add",
            publisher_code="PUB123",
            publisher_name="Test Publisher"
        )
        
        # Verify the POST request
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        
        # Verify payload
        payload = call_args['json']
        self.assertEqual(payload['events'][0]['name'], 'bookmark_action')
        self.assertEqual(payload['events'][0]['params']['action'], 'add')
        self.assertEqual(payload['events'][0]['params']['customEvent:publisher_code'], 'PUB123')
        self.assertEqual(payload['events'][0]['params']['customEvent:publisher_name'], 'Test Publisher')
        self.assertEqual(payload['events'][0]['params']['customEvent:feature_name'], 'bookmarks')

class TestGA4Live(unittest.TestCase):
    """Live integration tests for GA4 functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment for live tests."""
        # Initialize analytics
        cls.analytics = GA4Manager()
        cls.reports = GA4Reports()
        
        # Generate unique identifiers for test data
        cls.test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.test_user_id = f"test_user_{cls.test_id}"
        cls.test_publisher_code = f"TEST_PUB_{cls.test_id}"
        cls.test_publisher_name = f"Test Publisher {cls.test_id}"
        
    def test_1_send_events(self):
        """Test sending various events to GA4."""
        print("\nSending test events to GA4...")
        
        # Track search event
        self.analytics.track_search(
            user_id=self.test_user_id,
            query=f"test_query_{self.test_id}",
            results_count=5,
            success=True
        )
        
        # Track publisher interaction
        self.analytics.track_publisher_interaction(
            user_id=self.test_user_id,
            publisher_code=self.test_publisher_code,
            action="view",
            publisher_name=self.test_publisher_name,
            hall_number=1
        )
        
        # Track bookmark action
        self.analytics.track_bookmark_action(
            user_id=self.test_user_id,
            action="add",
            publisher_code=self.test_publisher_code,
            publisher_name=self.test_publisher_name
        )
        
        # Track user engagement
        self.analytics.track_user_engagement(
            user_id=self.test_user_id,
            feature="map_view",
            engagement_time_msec=1500
        )
        
        print("Test events sent successfully")
        
    def test_2_fetch_reports(self):
        """Test fetching various analytics reports."""
        print("\nFetching analytics reports...")
        
        # Wait a few seconds for events to process
        import time
        time.sleep(5)
        
        # Fetch and print various reports
        self.reports.get_search_analytics()
        self.reports.get_publisher_analytics()
        self.reports.get_bookmark_analytics()
        self.reports.get_feature_usage()
        self.reports.get_error_analytics()
        
        print("Reports fetched successfully")

def run_live_tests():
    """Run live integration tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGA4Live)
    unittest.TextTestRunner(verbosity=2).run(suite)

def run_unit_tests():
    """Run unit tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGA4Analytics)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run GA4 analytics tests')
    parser.add_argument('--live', action='store_true', help='Run live integration tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    args = parser.parse_args()
    
    if args.live:
        run_live_tests()
    elif args.unit:
        run_unit_tests()
    else:
        print("Please specify --live or --unit to run tests") 