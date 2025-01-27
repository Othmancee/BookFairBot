from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
    Filter,
    FilterExpression
)
from google.oauth2 import service_account
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tabulate import tabulate
import logging

# Load environment variables
load_dotenv()
PROPERTY_ID = os.getenv('GA4_PROPERTY_ID')

class GA4Reports:
    def __init__(self):
        """Initialize with GA4 property ID."""
        # Use the property ID from environment variables
        self.property_id = os.getenv('GA4_PROPERTY_ID')
        if not self.property_id:
            raise ValueError("GA4_PROPERTY_ID environment variable is required")
        
        # Set up credentials
        credentials = service_account.Credentials.from_service_account_file(
            'cse-bianas-49a96be4b7b5.json',
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        print("Successfully authenticated with service account")

    def run_report(self, dimensions, metrics, days=7, dimension_filter=None):
        """Run a GA4 report with specified dimensions and metrics."""
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
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
            # Filter for search events
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
            Dimension(name="eventName")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="eventValue")
        ]
        try:
            # Filter for publisher events
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

    def get_feature_usage(self):
        """Get feature usage analytics."""
        dimensions = [
            Dimension(name="eventName")
        ]
        metrics = [
            Metric(name="eventCount"),
            Metric(name="eventValue")
        ]
        try:
            # Filter for feature events
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
            # Filter for error events
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

def main():
    """Run all GA4 reports."""
    try:
        reports = GA4Reports()
        
        print(f"Fetching analytics data for the last 7 days...")
        
        # Get all reports
        reports.get_search_analytics()
        reports.get_publisher_analytics()
        reports.get_feature_usage()
        reports.get_error_analytics()
        
        print("\nGA4 reports complete!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 