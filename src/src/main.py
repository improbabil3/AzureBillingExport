import argparse
import logging
import sys
from pathlib import Path
import os
from datetime import datetime, timedelta

from .api.azure_client import AzureCostManagementClient, AzureAuthenticationError, AzureRequestError
from .core.data_processor import AzureCostDataProcessor
from .core.export import CostDataExporter
from .utils.logging_config import configure_logging
from .config.settings import (
    AZURE_SUBSCRIPTION_ID,
    AZURE_RESOURCE_GROUP,
    AUTH_TYPE,
    AZURE_TENANT_ID,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_BEARER_TOKEN,
    DEFAULT_EXPORT_PATH,
    DEFAULT_FROM_DATE,
    DEFAULT_TO_DATE,
    DEFAULT_SERVICES,
    COST_THRESHOLD,
    MAX_DAYS_PER_REQUEST
)

# Configure logging
logger = configure_logging()

def parse_arguments():
    """Parse command line arguments with defaults from .env file."""
    parser = argparse.ArgumentParser(
        description="Azure Cost Management Billing Export Tool",
        epilog="Tutti i parametri possono essere configurati nel file .env invece che specificati da riga di comando."
    )
    
    # Authentication parameters
    auth_group = parser.add_argument_group('Authentication')
    auth_group.add_argument('--auth-type', choices=['bearer_token', 'client_credentials'], 
                           default=AUTH_TYPE, help=f'Authentication type to use (default: {AUTH_TYPE})')
    auth_group.add_argument('--tenant-id', default=AZURE_TENANT_ID,
                           help='Azure tenant ID for client credentials auth')
    auth_group.add_argument('--client-id', default=AZURE_CLIENT_ID,
                           help='Azure client ID for client credentials auth')
    auth_group.add_argument('--client-secret', default=AZURE_CLIENT_SECRET,
                           help='Azure client secret for client credentials auth')
    auth_group.add_argument('--bearer-token', default=AZURE_BEARER_TOKEN,
                           help='Azure bearer token for direct authentication')
    
    # Azure resource parameters
    azure_group = parser.add_argument_group('Azure Resources')
    azure_group.add_argument('--subscription-id', default=AZURE_SUBSCRIPTION_ID, 
                           help=f'Azure subscription ID (default: {AZURE_SUBSCRIPTION_ID})')
    azure_group.add_argument('--resource-group', default=AZURE_RESOURCE_GROUP, 
                           help=f'Azure resource group name (default: {AZURE_RESOURCE_GROUP})')
    azure_group.add_argument('--services', nargs='+', 
                           default=DEFAULT_SERVICES, 
                           help=f'List of service resource IDs to filter by (default: {", ".join(DEFAULT_SERVICES) if DEFAULT_SERVICES else "none"})')
    
    # Date range parameters
    date_group = parser.add_argument_group('Date Range')
    date_group.add_argument('--from-date', 
                          default=DEFAULT_FROM_DATE.strftime('%Y-%m-%d') if DEFAULT_FROM_DATE else None, 
                          help=f'Start date in format YYYY-MM-DD (default: {DEFAULT_FROM_DATE.strftime("%Y-%m-%d") if DEFAULT_FROM_DATE else "none"})')
    date_group.add_argument('--to-date', 
                          default=DEFAULT_TO_DATE.strftime('%Y-%m-%d') if DEFAULT_TO_DATE else None,
                          help=f'End date in format YYYY-MM-DD (default: {DEFAULT_TO_DATE.strftime("%Y-%m-%d") if DEFAULT_TO_DATE else "none"})')
    date_group.add_argument('--max-days', type=int, default=MAX_DAYS_PER_REQUEST,
                          help=f'Maximum number of days per request (default: {MAX_DAYS_PER_REQUEST})')
    
    # Cost filtering
    filter_group = parser.add_argument_group('Filtering')
    filter_group.add_argument('--cost-threshold', type=float, default=COST_THRESHOLD,
                             help=f'Include only resources with cost above this threshold in USD (default: {COST_THRESHOLD})')
    
    # Output parameters
    output_group = parser.add_argument_group('Output')
    output_group.add_argument('--output', default=DEFAULT_EXPORT_PATH, 
                            help=f'Output CSV file path (default: {DEFAULT_EXPORT_PATH})')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Validate authentication parameters based on auth type
    if args.auth_type == 'bearer_token' and not args.bearer_token:
        parser.error("Per l'autenticazione con bearer_token è necessario specificare --bearer-token o configurare AZURE_BEARER_TOKEN nel file .env")
    
    if args.auth_type == 'client_credentials' and not all([args.tenant_id, args.client_id, args.client_secret]):
        parser.error("Per l'autenticazione con client_credentials è necessario specificare --tenant-id, --client-id e --client-secret o configurarli nel file .env")
    
    # Validate required parameters
    if not args.subscription_id:
        parser.error("È necessario specificare --subscription-id o configurare AZURE_SUBSCRIPTION_ID nel file .env")
    
    if not args.resource_group:
        parser.error("È necessario specificare --resource-group o configurare AZURE_RESOURCE_GROUP nel file .env")
    
    if not args.services:
        parser.error("È necessario specificare --services o configurare DEFAULT_SERVICES nel file .env")
    
    # Validate date parameters
    if not args.from_date or not args.to_date:
        parser.error("È necessario specificare --from-date e --to-date o configurare DEFAULT_FROM_DATE e DEFAULT_TO_DATE nel file .env")
    
    # Validate date format
    try:
        datetime.strptime(args.from_date, '%Y-%m-%d')
        datetime.strptime(args.to_date, '%Y-%m-%d')
    except ValueError:
        parser.error("Le date devono essere nel formato YYYY-MM-DD")
    
    return args

def validate_service_ids(services, subscription_id, resource_group):
    """Ensure service IDs are correctly formatted."""
    validated = []
    for service in services:
        if not service.startswith('/subscriptions/'):
            # Format as a full resource ID if just a service name is provided
            service = f"/subscriptions/{subscription_id}/resourcegroups/{resource_group}/providers/microsoft.cognitiveservices/accounts/{service}"
        validated.append(service)
    return validated

def main():
    """Main entry point for the application."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        logger.info("Starting Azure Cost Management Billing Export Tool")
        logger.info(f"Authentication type: {args.auth_type}")
        logger.info(f"Period: from {args.from_date} to {args.to_date}")
        logger.info(f"Subscription ID: {args.subscription_id}")
        logger.info(f"Resource group: {args.resource_group}")
        logger.info(f"Services: {', '.join(args.services)}")
        logger.info(f"Cost threshold: ${args.cost_threshold}")
        logger.info(f"Output path: {args.output}")
        
        # Validate and format service IDs
        services = validate_service_ids(args.services, args.subscription_id, args.resource_group)
        
        # Create Azure client
        try:
            client = AzureCostManagementClient(
                subscription_id=args.subscription_id,
                resource_group_name=args.resource_group,
                bearer_token=args.bearer_token if args.auth_type == 'bearer_token' else None,
                tenant_id=args.tenant_id if args.auth_type == 'client_credentials' else None,
                client_id=args.client_id if args.auth_type == 'client_credentials' else None,
                client_secret=args.client_secret if args.auth_type == 'client_credentials' else None
            )
        except AzureAuthenticationError as e:
            logger.error(f"Errore di autenticazione: {str(e)}")
            return 1
        except ValueError as e:
            logger.error(f"Errore di configurazione: {str(e)}")
            return 1
        
        # Get cost data
        logger.info(f"Fetching cost data from {args.from_date} to {args.to_date}")
        cost_data = client.get_cost_data(services, args.from_date, args.to_date)
        
        # Check for API errors
        if cost_data.get("error"):
            error_info = cost_data.get("error", {})
            error_code = error_info.get("code", "Unknown")
            error_message = error_info.get("message", "No error message provided")
            logger.error(f"API Error ({error_code}): {error_message}")
            return 1
            
        # Process data
        processor = AzureCostDataProcessor()
        processed_data = processor.process_cost_data(cost_data)
        
        # Apply cost threshold filtering if specified
        if args.cost_threshold > 0:
            original_count = len(processed_data)
            processed_data = processed_data[processed_data['CostUSD'] >= args.cost_threshold]
            filtered_count = original_count - len(processed_data)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} entries below cost threshold of ${args.cost_threshold}")
        
        # Export data
        exporter = CostDataExporter(args.output)
        output_file = exporter.to_csv(processed_data)
        
        if output_file:
            logger.success(f"CSV file exported successfully to: {output_file}")
            logger.info(f"Total entries exported: {len(processed_data)}")
            
            # Correzione per assicurarci che i valori siano numeri prima di formattare
            try:
                # Estrai i valori totali dai costi
                if not processed_data.empty:
                    # Converti esplicitamente in float per evitare problemi di formattazione
                    total_cost_usd = float(processed_data['CostUSD'].sum())
                    total_cost_eur = float(processed_data['CostEUR'].sum())
                else:
                    total_cost_usd = 0.0
                    total_cost_eur = 0.0
                    
                logger.info(f"Total cost: ${total_cost_usd:.2f} USD / €{total_cost_eur:.2f} EUR")
            except Exception as e:
                # Se c'è un errore nella formattazione, mostra i valori senza formattazione
                if not processed_data.empty:
                    total_cost_usd = processed_data['CostUSD'].sum()
                    total_cost_eur = processed_data['CostEUR'].sum()
                else:
                    total_cost_usd = 0
                    total_cost_eur = 0
                logger.info(f"Total cost: ${total_cost_usd} USD / €{total_cost_eur} EUR")
        else:
            logger.warning("No data was exported")
        
        return 0
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())