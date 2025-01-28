from ga4_reports import GA4Reports
from google.analytics.data_v1beta.types import Dimension, Metric
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_report():
    """Test basic GA4 reporting functionality."""
    try:
        # Initialize GA4 Reports
        ga4 = GA4Reports()
        logger.info("✓ Successfully initialized GA4Reports")

        # Set up a simple report request
        dimensions = [
            Dimension(name="eventName"),  # Standard dimension
            Dimension(name="customEvent:feature_name")  # Custom dimension
        ]
        metrics = [
            Metric(name="eventCount"),  # Standard metric
            Metric(name="customEvent:engagement_duration")  # Custom metric
        ]

        # Run the report for last 30 days to get more data
        logger.info("Fetching report for the last 30 days...")
        response = ga4.run_report(dimensions, metrics, days=30)
        
        # Process and display results
        logger.info("\nReport Results:")
        print("\nDimensions:", [dim.name for dim in response.dimension_headers])
        print("Metrics:", [metric.name for metric in response.metric_headers])
        print("\nRows:")
        
        if not response.rows:
            print("No data found in the last 30 days")
        else:
            for row in response.rows:
                dimensions = [value.value for value in row.dimension_values]
                metrics = [value.value for value in row.metric_values]
                print(f"Dimensions: {dimensions}, Metrics: {metrics}")

        logger.info("✓ Successfully retrieved and displayed report")
        return True

    except Exception as e:
        logger.error(f"❌ Error running GA4 report test: {e}")
        return False

if __name__ == "__main__":
    print("Testing GA4 Reporting...")
    success = test_basic_report()
    if success:
        print("\n✅ GA4 reporting test completed successfully!")
    else:
        print("\n❌ GA4 reporting test failed!") 