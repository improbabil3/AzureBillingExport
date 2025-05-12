import logging
import pandas as pd
import os
from pathlib import Path
from ..config.settings import CSV_DELIMITER, DECIMAL_SEPARATOR, DEFAULT_EXPORT_PATH
from ..utils.path_utils import ensure_dir_exists

logger = logging.getLogger(__name__)

class CostDataExporter:
    """Export cost data to various formats."""
    
    def __init__(self, output_path=None):
        """
        Initialize the data exporter.
        
        Args:
            output_path (str, optional): Path to save the exported file
        """
        self.output_path = output_path or DEFAULT_EXPORT_PATH
        
    def to_csv(self, df, output_path=None):
        """
        Export the data to a CSV file.
        
        Args:
            df (pd.DataFrame): Data to export
            output_path (str, optional): Path to save the CSV file
            
        Returns:
            str: Path to the exported CSV file
        """
        if df.empty:
            logger.warning("No data to export")
            return None
        
        # Use the provided path or the default path
        output_path = output_path or self.output_path
        
        # Ensure the directory exists
        output_dir = os.path.dirname(output_path)
        ensure_dir_exists(output_dir)
        
        logger.info(f"Exporting data to CSV: {output_path}")
        
        try:
            # Format numbers with comma as decimal separator for European format
            df['CostUSD'] = df['CostUSD'].apply(lambda x: f"{x:.2f}".replace('.', DECIMAL_SEPARATOR))
            df['CostEUR'] = df['CostEUR'].apply(lambda x: f"{x:.2f}".replace('.', DECIMAL_SEPARATOR))
            
            # Select only the columns needed for the CSV
            csv_df = df[['Date', 'ResourceName', 'CostUSD', 'CostEUR']]
            
            # Export to CSV with semicolon as delimiter
            csv_df.to_csv(output_path, sep=CSV_DELIMITER, index=False)
            
            logger.success(f"Successfully exported {len(df)} rows to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting data to CSV: {str(e)}")
            raise