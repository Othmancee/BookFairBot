import boto3
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS credentials and region
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Function name and API name
FUNCTION_NAME = 'BookfairBot'
API_NAME = 'BookfairBotAPI'

def create_lambda_function(lambda_client):
    """Create or update Lambda function"""
    try:
        with open('deployment.zip', 'rb') as zip_file:
            zip_bytes = zip_file.read()
        
        try:
            # Try to update existing function
            response = lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_bytes
            )
            print(f"Updated Lambda function: {FUNCTION_NAME}")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function if it doesn't exist
            response = lambda_client.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime='python3.9',
                Role=os.getenv('LAMBDA_ROLE_ARN'),  # IAM role ARN
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_bytes},
                Timeout=30,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'BOT_TOKEN': BOT_TOKEN
                    }
                }
            )
            print(f"Created Lambda function: {FUNCTION_NAME}")
        
        return response['FunctionArn']
    
    except Exception as e:
        print(f"Error creating/updating Lambda function: {str(e)}")
        raise

def create_api_gateway(api_client, lambda_client, function_arn):
    """Create or get API Gateway"""
    try:
        # Try to find existing API
        apis = api_client.get_rest_apis()
        api_id = None
        for api in apis['items']:
            if api['name'] == API_NAME:
                api_id = api['id']
                print(f"Found existing API: {API_NAME}")
                break
        
        if not api_id:
            # Create new API
            api = api_client.create_rest_api(
                name=API_NAME,
                description='Telegram Bot Webhook API'
            )
            api_id = api['id']
            print(f"Created new API: {API_NAME}")
        
        # Get root resource id
        resources = api_client.get_resources(restApiId=api_id)
        root_id = [r['id'] for r in resources['items'] if r['path'] == '/'][0]
        
        # Create resource and method
        try:
            resource = api_client.create_resource(
                restApiId=api_id,
                parentId=root_id,
                pathPart='webhook'
            )
            resource_id = resource['id']
        except api_client.exceptions.ConflictException:
            # Resource already exists
            resource_id = [r['id'] for r in resources['items'] if r['path'] == '/webhook'][0]
        
        # Set up POST method
        try:
            api_client.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='POST',
                authorizationType='NONE'
            )
        except api_client.exceptions.ConflictException:
            pass  # Method already exists
        
        # Set up integration
        integration_uri = f'arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{function_arn}/invocations'
        try:
            api_client.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='POST',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=integration_uri
            )
        except api_client.exceptions.ConflictException:
            pass  # Integration already exists
        
        # Deploy API
        deployment = api_client.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        # Get the invoke URL
        invoke_url = f'https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/webhook'
        print(f"API Gateway URL: {invoke_url}")
        
        # Add Lambda permission for API Gateway
        try:
            lambda_client.add_permission(
                FunctionName=FUNCTION_NAME,
                StatementId='AllowAPIGateway',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws:execute-api:{AWS_REGION}:{os.getenv("AWS_ACCOUNT_ID")}:{api_id}/*/*/webhook'
            )
        except lambda_client.exceptions.ResourceConflictException:
            pass  # Permission already exists
        
        return invoke_url
    
    except Exception as e:
        print(f"Error setting up API Gateway: {str(e)}")
        raise

def set_webhook(webhook_url):
    """Set Telegram webhook URL"""
    try:
        api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook'
        response = requests.post(api_url, json={'url': webhook_url})
        if response.status_code == 200 and response.json().get('ok'):
            print("Successfully set Telegram webhook")
        else:
            print(f"Error setting webhook: {response.text}")
    except Exception as e:
        print(f"Error setting webhook: {str(e)}")
        raise

def main():
    # Check required environment variables
    required_vars = ['AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'BOT_TOKEN', 'LAMBDA_ROLE_ARN', 'AWS_ACCOUNT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        return
    
    # Initialize AWS clients
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )
    lambda_client = session.client('lambda')
    api_client = session.client('apigateway')
    
    try:
        # Create/update Lambda function
        print("Creating/updating Lambda function...")
        function_arn = create_lambda_function(lambda_client)
        
        # Set up API Gateway
        print("Setting up API Gateway...")
        webhook_url = create_api_gateway(api_client, lambda_client, function_arn)
        
        # Set Telegram webhook
        print("Setting Telegram webhook...")
        set_webhook(webhook_url)
        
        print("\nDeployment completed successfully!")
        print(f"Webhook URL: {webhook_url}")
    
    except Exception as e:
        print(f"\nDeployment failed: {str(e)}")

if __name__ == '__main__':
    main() 