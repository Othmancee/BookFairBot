#!/usr/bin/env python3
from analytics import GA4Manager
import os
from dotenv import load_dotenv
import time

def test_ga4():
    """Test GA4 tracking with various events."""
    load_dotenv()
    
    # Initialize GA4 manager
    ga4 = GA4Manager()
    
    # Test user ID
    user_id = "test_user_123"
    
    print("Testing GA4 tracking...")
    
    # Test search tracking
    ga4.track_search(
        user_id=user_id,
        query="دار الشروق",
        success=True,
        results_count=5
    )
    print("✓ Search event tracked")
    
    # Test navigation tracking
    ga4.track_navigation(
        user_id=user_id,
        from_screen="home",
        to_screen="search"
    )
    print("✓ Navigation event tracked")
    
    # Test feature usage
    ga4.track_feature_use(
        user_id=user_id,
        feature="maps"
    )
    print("✓ Feature usage tracked")
    
    # Test map interaction
    ga4.track_map_interaction(
        user_id=user_id,
        hall_number=1,
        action="view"
    )
    print("✓ Map interaction tracked")
    
    # Test publisher interaction
    ga4.track_publisher_interaction(
        user_id=user_id,
        publisher_code="A123",
        action="view",
        publisher_name="Test Publisher"
    )
    print("✓ Publisher interaction tracked")
    
    # Test bookmark action
    ga4.track_bookmark_action(
        user_id=user_id,
        publisher_code="A123",
        action="add"
    )
    print("✓ Bookmark action tracked")
    
    # Test error tracking
    ga4.track_error(
        user_id=user_id,
        error_type="TestError",
        error_message="Test error message"
    )
    print("✓ Error event tracked")
    
    # Test performance tracking
    ga4.track_performance(
        user_id=user_id,
        operation="test_operation",
        duration_ms=1500
    )
    print("✓ Performance event tracked")
    
    print("\nAll GA4 tracking tests completed successfully!")

if __name__ == "__main__":
    test_ga4() 