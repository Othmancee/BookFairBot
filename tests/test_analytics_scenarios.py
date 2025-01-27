import os
import json
import time
from analytics import GA4Manager

def simulate_user_session(ga4: GA4Manager, user_id: str):
    """Simulate a complete user session with various interactions."""
    print(f"\nSimulating session for user {user_id}")
    
    # Start session
    ga4.track_session_start(user_id, source='telegram')
    
    # Simulate search sequence
    print("\n1. Search Sequence:")
    searches = [
        ("دار الشروق", True, 2),
        ("A21", True, 1),
        ("nonexistent", False, 0),
        ("قاعة 1", True, 45),
        ("جناح B", True, 12)
    ]
    
    for query, success, count in searches:
        ga4.track_search(user_id, query, success, count)
        print(f"  - Search: {query} (Success: {success}, Results: {count})")
        time.sleep(0.5)  # Simulate real-world timing
    
    # Simulate publisher interactions
    print("\n2. Publisher Interactions:")
    publishers = [
        ("1_A21", "view", "دار الشروق", 1),
        ("2_B22", "view", "مكتبة النور", 2),
        ("1_A21", "favorite", "دار الشروق", 1)
    ]
    
    for code, action, name, hall in publishers:
        ga4.track_publisher_interaction(user_id, code, action, name, hall)
        print(f"  - {action.title()}: {name} ({code})")
        time.sleep(1)
    
    # Simulate map navigation
    print("\n3. Map Navigation:")
    map_actions = [
        (1, "view", None),
        (1, "section_select", "A"),
        (2, "view", None),
        (2, "section_select", "B")
    ]
    
    for hall, action, section in map_actions:
        ga4.track_map_interaction(user_id, hall, action, section)
        print(f"  - {action.title()}: Hall {hall}" + (f" Section {section}" if section else ""))
        time.sleep(0.8)
    
    # Simulate bookmark actions
    print("\n4. Bookmark Actions:")
    bookmarks = [
        ("1_A21", "add"),
        ("2_B22", "add"),
        ("1_A21", "remove")
    ]
    
    for code, action in bookmarks:
        ga4.track_bookmark_action(user_id, code, action)
        print(f"  - {action.title()}: {code}")
        time.sleep(0.5)
    
    # Simulate performance tracking
    print("\n5. Performance Metrics:")
    operations = [
        ("quick_search", 200),
        ("map_render", 800),
        ("complex_search", 1500),
        ("heavy_operation", 2500)
    ]
    
    for op, duration in operations:
        ga4.track_performance(user_id, op, duration)
        category = ga4._get_performance_category(duration)
        print(f"  - {op}: {duration}ms ({category})")
    
    # Simulate error
    print("\n6. Error Simulation:")
    ga4.track_error(user_id, "DataError", "Failed to load publisher data")
    print("  - Tracked error: DataError")
    
    # Print session summary
    print("\nSession Summary:")
    session = ga4.user_sessions.get(user_id, {})
    print(f"  - Session ID: {session.get('session_id')}")
    print(f"  - Actions: {len(session.get('actions', []))}")
    print(f"  - Session Depth: {session.get('depth')}")
    
    return session

def main():
    # Initialize GA4 with debug mode
    os.environ['GA4_DEBUG'] = 'true'
    os.environ['GA4_MEASUREMENT_ID'] = 'test_id'
    os.environ['GA4_API_SECRET'] = 'test_secret'
    
    ga4 = GA4Manager()
    
    # Simulate multiple users
    users = [
        "user_123",  # New user
        "user_456",  # Returning user
        "user_789"   # Frequent user
    ]
    
    # Set up session counts for different user types
    ga4.session_counts["user_456"] = 3
    ga4.session_counts["user_789"] = 10
    
    # Run simulations
    for user_id in users:
        session = simulate_user_session(ga4, user_id)
        time.sleep(1)  # Pause between sessions
    
    # Print overall analytics
    print("\nOverall Analytics:")
    print(f"Total Users: {len(ga4.user_sessions)}")
    print(f"Total Sessions: {sum(ga4.session_counts.values())}")
    
    # Print feature usage statistics
    print("\nFeature Usage Statistics:")
    for user_id, features in ga4.feature_usage.items():
        print(f"\nUser {user_id}:")
        for feature, count in features.items():
            print(f"  - {feature}: {count} times")

if __name__ == "__main__":
    main() 