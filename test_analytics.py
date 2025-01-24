import os
from analytics import GA4Manager
import logging
from datetime import datetime
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ga4_tracking(force_production: bool = False):
    """Test all GA4 tracking events"""
    try:
        # Set environment for testing
        if force_production:
            os.environ['RAILWAY_ENVIRONMENT'] = 'production'
        else:
            os.environ['RAILWAY_ENVIRONMENT'] = 'development'
            os.environ['GA4_DEBUG'] = 'true'
        
        # Initialize GA4
        ga4 = GA4Manager()
        logger.info(f"✓ Successfully initialized GA4 Manager in {os.getenv('RAILWAY_ENVIRONMENT')} mode")
        
        # Test user ID for all events
        test_user_id = "test_user_001"
        
        # 1. Test session start
        ga4.track_session_start(test_user_id)
        logger.info("✓ Tracked session start")
        
        # 2. Test search events
        search_queries = [
            ("دار الشروق", True, 3),    # Publisher name search
            ("A123", True, 1),          # Publisher code search
            ("قاعة 1", True, 15),       # Hall search
            ("xyz123", False, 0)        # Failed search
        ]
        
        for query, success, count in search_queries:
            ga4.track_search(test_user_id, query, success, count)
        logger.info("✓ Tracked search events")
        
        # 3. Test publisher interactions
        publisher_actions = [
            ("A123", "view", "دار الشروق"),
            ("B456", "bookmark", "مكتبة مدبولي"),
            ("C789", "unbookmark", "دار المعارف")
        ]
        
        for code, action, name in publisher_actions:
            ga4.track_publisher_interaction(test_user_id, code, action, name)
        logger.info("✓ Tracked publisher interactions")
        
        # 4. Test map interactions
        map_actions = [
            (1, "view", None),
            (2, "section_select", "A"),
            (3, "zoom", None)
        ]
        
        for hall, action, section in map_actions:
            ga4.track_map_interaction(test_user_id, hall, action, section)
        logger.info("✓ Tracked map interactions")
        
        # 5. Test navigation patterns
        screens = [
            ("start", "search"),
            ("search", "publisher_view"),
            ("publisher_view", "map"),
            ("map", "favorites")
        ]
        
        for from_screen, to_screen in screens:
            ga4.track_navigation(test_user_id, from_screen, to_screen)
        logger.info("✓ Tracked navigation patterns")
        
        # 6. Test feature usage
        features = [
            ("search", "publisher_lookup"),
            ("maps", "hall_view"),
            ("favorites", None),
            ("events", "upcoming")
        ]
        
        for feature, sub_feature in features:
            ga4.track_feature_use(test_user_id, feature, sub_feature)
        logger.info("✓ Tracked feature usage")
        
        # 7. Test bookmark actions
        bookmarks = [
            ("A123", "add"),
            ("B456", "add"),
            ("A123", "remove")
        ]
        
        for code, action in bookmarks:
            ga4.track_bookmark_action(test_user_id, code, action)
        logger.info("✓ Tracked bookmark actions")
        
        # 8. Test user engagement
        engagements = [
            ("search", 5000),
            ("map_view", 12000),
            ("publisher_view", 3000)
        ]
        
        for feature, duration in engagements:
            ga4.track_user_engagement(test_user_id, feature, duration)
        logger.info("✓ Tracked user engagement")
        
        # 9. Test performance metrics
        operations = [
            ("search_operation", 150.5),
            ("map_render", 450.2),
            ("publisher_load", 80.1)
        ]
        
        for operation, duration in operations:
            ga4.track_performance(test_user_id, operation, duration)
        logger.info("✓ Tracked performance metrics")
        
        # 10. Test error tracking
        errors = [
            ("NetworkError", "Failed to connect to server"),
            ("ValidationError", "Invalid publisher code"),
            ("RenderError", "Failed to generate map")
        ]
        
        for error_type, message in errors:
            ga4.track_error(test_user_id, error_type, message)
        logger.info("✓ Tracked error events")
        
        # 11. Test language preferences
        ga4.track_language_preference(test_user_id, True)  # Arabic
        ga4.track_language_preference(test_user_id, False) # English
        logger.info("✓ Tracked language preferences")
        
        logger.info(f"\n✅ All GA4 tracking tests completed successfully in {os.getenv('RAILWAY_ENVIRONMENT')} mode")
        return True
        
    except Exception as e:
        logger.error(f"❌ GA4 tracking test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Test in development mode first
    print("\nTesting GA4 Tracking in Development Mode...")
    dev_success = test_ga4_tracking(force_production=False)
    print("\nDevelopment Mode Test:", "✓ PASSED" if dev_success else "❌ FAILED")
    
    # Test in production mode if development tests pass
    if dev_success:
        print("\nTesting GA4 Tracking in Production Mode...")
        prod_success = test_ga4_tracking(force_production=True)
        print("\nProduction Mode Test:", "✓ PASSED" if prod_success else "❌ FAILED") 