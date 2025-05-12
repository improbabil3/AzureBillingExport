import sys
import os
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add the project root to Python path to import modules correctly
project_root = Path(__file__).absolute().parent
sys.path.append(str(project_root))

from src.utils.logging_config import configure_logging

# Configure logging
logger = configure_logging()

def create_mock_cost_data():
    """Create mock Azure cost data for testing."""
    logger.info("Creating mock cost data for testing")
    
    mock_data = {
        "properties": {
            "columns": [
                {"name": "usageStart", "type": "DateTime"},
                {"name": "ResourceId", "type": "String"},
                {"name": "Cost", "type": "Decimal"},
                {"name": "CostUSD", "type": "Decimal"},
                {"name": "ChargeType", "type": "String"},
                {"name": "PublisherType", "type": "String"}
            ],
            "rows": [
                ["20230101T000000Z", "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-service-1", 10.50, 11.25, "Usage", "Microsoft"],
                ["20230101T000000Z", "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-service-2", 25.75, 27.50, "Usage", "Microsoft"],
                ["20230201T000000Z", "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-service-1", 12.30, 13.75, "Usage", "Microsoft"],
                ["20230201T000000Z", "/subscriptions/sub-id/resourceGroups/test-rg/providers/Microsoft.CognitiveServices/accounts/test-service-2", 28.90, 30.25, "Usage", "Microsoft"]
            ]
        }
    }
    
    return mock_data

def manual_process_data(cost_data):
    """Manually process data to identify and fix issues."""
    logger.info("Manually processing data to debug issues")
    
    if not cost_data or "properties" not in cost_data or "rows" not in cost_data["properties"]:
        logger.warning("No cost data found or invalid format")
        return None
        
    rows = cost_data["properties"]["rows"]
    if not rows:
        logger.warning("No cost data rows found")
        return None
        
    # Extract column names from the response
    columns = cost_data["properties"]["columns"]
    column_names = [col["name"] for col in columns]
    
    logger.info(f"Column names: {column_names}")
    
    # Create a DataFrame from the rows
    df = pd.DataFrame(rows, columns=column_names)
    logger.info(f"DataFrame shape: {df.shape}")
    logger.info(f"DataFrame columns: {df.columns.tolist()}")
    logger.info(f"First row: {df.iloc[0].to_dict()}")
    
    # Process the data manually
    processed_data = []
    
    for index, row in df.iterrows():
        logger.info(f"Processing row {index}")
        
        # Extract date
        date_str = row["usageStart"]
        logger.info(f"Date string: {date_str}")
        
        try:
            # Parse and format the date
            date_obj = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
            formatted_date = date_obj.strftime("%Y-%m-%d")
            logger.info(f"Parsed date: {formatted_date}")
            
            # Extract resource ID and name
            resource_id = row["ResourceId"]
            parts = resource_id.strip('/').split('/')
            resource_name = parts[-1] if parts else "unknown-resource"
            
            # Get costs
            cost_eur = float(row["Cost"])
            cost_usd = float(row["CostUSD"])
            
            # Add to processed data
            processed_data.append({
                "Date": formatted_date,
                "ResourceName": resource_name,
                "ResourceId": resource_id,
                "CostUSD": cost_usd,
                "CostEUR": cost_eur
            })
            logger.success(f"Successfully processed row {index}")
        except Exception as e:
            logger.error(f"Error processing row {index}: {str(e)}")
            logger.error(traceback.format_exc())
    
    # Create the final DataFrame
    result_df = pd.DataFrame(processed_data)
    
    if not result_df.empty:
        # Aggregate by date and resource name
        result_df = result_df.groupby(["Date", "ResourceName"], as_index=False).agg({
            "ResourceId": "first",
            "CostUSD": "sum",
            "CostEUR": "sum"
        })
        
        # Sort by date and resource name
        result_df = result_df.sort_values(["Date", "ResourceName"])
    
    return result_df

def save_to_csv(df, output_path):
    """Save DataFrame to CSV."""
    if df is None or df.empty:
        logger.warning("No data to export")
        return None
    
    try:
        # Ensure the directory exists
        output_dir = os.path.dirname(output_path)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Format numbers with comma as decimal separator for European format
        df['CostUSD'] = df['CostUSD'].apply(lambda x: f"{x:.2f}".replace('.', ','))
        df['CostEUR'] = df['CostEUR'].apply(lambda x: f"{x:.2f}".replace('.', ','))
        
        # Export to CSV with semicolon as delimiter
        df.to_csv(output_path, sep=";", index=False)
        
        logger.success(f"Successfully exported {len(df)} rows to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error exporting data to CSV: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def main():
    try:
        # Create mock data
        mock_data = create_mock_cost_data()
        
        # Manually process data to debug issues
        processed_data = manual_process_data(mock_data)
        
        if processed_data is not None:
            # Show the processed data
            logger.info(f"Processed data shape: {processed_data.shape}")
            logger.info("\nProcessed data preview:")
            print(processed_data)
            
            # Export the data
            logger.info("\nExporting data to CSV")
            output_dir = Path(project_root) / "output"
            output_dir.mkdir(exist_ok=True)
            
            output_path = output_dir / "debug_export.csv"
            csv_path = save_to_csv(processed_data, output_path)
            
            if csv_path:
                # Read and display the first few lines of the CSV
                with open(csv_path, 'r') as f:
                    logger.info("\nCSV file content (first 5 lines):")
                    for i, line in enumerate(f):
                        if i < 5:
                            print(line.strip())
                        else:
                            break
        else:
            logger.error("Failed to process data")
    
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())