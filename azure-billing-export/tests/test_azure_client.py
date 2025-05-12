import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
from src.api.azure_client import AzureCostManagementClient

class TestAzureCostManagementClient(unittest.TestCase):
    """Test case for the Azure Cost Management Client."""
    
    def setUp(self):
        """Set up test fixtures, if any."""
        self.subscription_id = "test-subscription-id"
        self.resource_group = "test-resource-group"
        self.bearer_token = "test-bearer-token"
        self.tenant_id = "test-tenant-id"
        self.client_id = "test-client-id"
        self.client_secret = "test-client-secret"
        
    @patch('src.api.azure_client.requests.request')
    def test_get_cost_data_for_period(self, mock_request):
        """Test getting cost data for a specific period."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "properties": {
                "columns": [
                    {"name": "UsageStart"},
                    {"name": "ResourceId"},
                    {"name": "CostUSD"},
                    {"name": "Cost"}
                ],
                "rows": [
                    ["20240301T000000Z", "/subscriptions/test/resourcegroups/test/providers/microsoft.cognitiveservices/accounts/test-service", 100.50, 90.25]
                ]
            }
        }
        mock_request.return_value = mock_response
        
        # Create client with bearer token
        client = AzureCostManagementClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group,
            bearer_token=self.bearer_token
        )
        
        # Define services and dates
        services = ["/subscriptions/test/resourcegroups/test/providers/microsoft.cognitiveservices/accounts/test-service"]
        from_date = "2024-03-01"
        to_date = "2024-03-31"
        
        # Call the method
        result = client._get_cost_data_for_period(services, from_date, to_date)
        
        # Verify results
        self.assertEqual(result, mock_response.json.return_value)
        mock_request.assert_called_once()
        
        # Verify request parameters
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['method'], 'POST')
        self.assertTrue('/subscriptions/test-subscription-id/resourceGroups/test-resource-group/providers/Microsoft.CostManagement/query' in call_args[1]['url'])
        self.assertEqual(call_args[1]['headers']['Authorization'], f'Bearer {self.bearer_token}')
        
        # Verify request body
        request_body = call_args[1]['json']
        self.assertEqual(request_body['type'], 'ActualCost')
        self.assertEqual(request_body['dataSet']['granularity'], 'Monthly')
        self.assertEqual(request_body['timePeriod']['from'], from_date)
        self.assertEqual(request_body['timePeriod']['to'], to_date)
        self.assertEqual(request_body['dataSet']['filter']['Dimensions']['Values'], services)
        
    @patch('src.api.azure_client.requests.post')
    def test_get_token_from_client_credentials(self, mock_post):
        """Test token retrieval using client credentials."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_type": "Bearer",
            "expires_in": 3600,
            "ext_expires_in": 3600,
            "access_token": "mock-access-token"
        }
        mock_post.return_value = mock_response
        
        # Create client with client credentials
        client = AzureCostManagementClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group,
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Override auth type for testing
        client.auth_type = "client_credentials"
        
        # Call the method
        token = client._get_token_from_client_credentials()
        
        # Verify results
        self.assertEqual(token, "mock-access-token")
        mock_post.assert_called_once()
        
        # Verify request parameters
        call_args = mock_post.call_args
        self.assertTrue(f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/token' in call_args[0][0])
        self.assertEqual(call_args[1]['data']['grant_type'], 'client_credentials')
        self.assertEqual(call_args[1]['data']['client_id'], self.client_id)
        self.assertEqual(call_args[1]['data']['client_secret'], self.client_secret)
        
    @patch('src.api.azure_client.AzureCostManagementClient._get_cost_data_for_period')
    def test_get_cost_data_chunks(self, mock_get_cost_data):
        """Test handling of data retrieval for periods longer than a year."""
        # Mock the individual period responses
        mock_get_cost_data.side_effect = [
            {
                "properties": {
                    "columns": [{"name": "UsageStart"}, {"name": "ResourceId"}, {"name": "CostUSD"}, {"name": "Cost"}],
                    "rows": [["20240301T000000Z", "test-resource", 100.0, 90.0]]
                }
            },
            {
                "properties": {
                    "columns": [{"name": "UsageStart"}, {"name": "ResourceId"}, {"name": "CostUSD"}, {"name": "Cost"}],
                    "rows": [["20250301T000000Z", "test-resource", 200.0, 180.0]]
                }
            }
        ]
        
        # Create client
        client = AzureCostManagementClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group,
            bearer_token=self.bearer_token
        )
        
        # Define services and dates (more than a year apart)
        services = ["test-service"]
        from_date = "2024-03-01"
        to_date = "2025-03-31"
        
        # Convert to datetime for the test
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
        
        # Call the method
        result = client._get_cost_data_in_chunks(services, from_date_obj, to_date_obj)
        
        # Verify the method was called for each period
        self.assertEqual(mock_get_cost_data.call_count, 2)
        
        # Verify results were combined
        self.assertEqual(len(result["properties"]["rows"]), 2)
        
if __name__ == "__main__":
    unittest.main()