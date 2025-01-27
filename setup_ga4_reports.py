from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import (
    CustomDimension,
    CustomMetric
)
from google.analytics.data_v1beta.types import (
    Dimension,
    Metric
)
from google.oauth2 import service_account
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PROPERTY_ID = os.getenv('GA4_PROPERTY_ID')

def setup_ga4_reports():
    """Set up custom dimensions and metrics in GA4."""
    try:
        # Initialize the GA4 Admin client with service account
        credentials = service_account.Credentials.from_service_account_file(
            'cse-bianas-49a96be4b7b5.json',
            scopes=['https://www.googleapis.com/auth/analytics.edit']
        )
        client = AnalyticsAdminServiceClient(credentials=credentials)
        property_path = f"properties/{PROPERTY_ID}"
        
        print(f"Setting up GA4 custom dimensions and metrics for property {PROPERTY_ID}")
        
        # Create custom dimensions
        dimensions = [
            ("Publisher Code", "publisher_code", "Publisher unique identifier"),
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
                client.create_custom_dimension(
                    parent=property_path,
                    custom_dimension=dimension
                )
                print(f"Created custom dimension: {display_name}")
            except Exception as e:
                print(f"Error creating dimension {display_name}: {e}")
            
        # Create custom metrics
        metrics = [
            ("Search Results Count", "search_results_count", "Number of results returned by search"),
            ("Engagement Duration", "engagement_duration", "Time spent using a feature")
        ]
        
        for display_name, param_name, description in metrics:
            try:
                metric = CustomMetric(
                    display_name=display_name,
                    parameter_name=param_name,
                    description=description,
                    measurement_unit=CustomMetric.MeasurementUnit.STANDARD,
                    scope=CustomMetric.MetricScope.EVENT
                )
                client.create_custom_metric(
                    parent=property_path,
                    custom_metric=metric
                )
                print(f"Created custom metric: {display_name}")
            except Exception as e:
                print(f"Error creating metric {display_name}: {e}")
        
        print("\nGA4 setup complete! Custom dimensions and metrics have been created.")
        print("\nYou can now create custom reports in the GA4 dashboard using these dimensions and metrics:")
        print("\nCustom Dimensions:")
        for display_name, param_name, _ in dimensions:
            print(f"- {display_name} (customEvent:{param_name})")
        print("\nCustom Metrics:")
        for display_name, param_name, _ in metrics:
            print(f"- {display_name} (customEvent:{param_name})")
        
    except Exception as e:
        print(f"Error setting up GA4: {e}")
        raise

if __name__ == "__main__":
    setup_ga4_reports() 