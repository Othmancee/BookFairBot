"""
Script to set up GA4 dashboard configuration including custom dimensions,
metrics, reports, and conversions.
"""

from analytics import GA4Setup

def main():
    """Run GA4 dashboard setup."""
    try:
        # Initialize GA4 setup
        setup = GA4Setup()
        
        # Run complete setup
        setup.setup_all()
        
    except Exception as e:
        print(f"\n❌ Error during GA4 setup: {e}")
        raise

if __name__ == "__main__":
    main() 