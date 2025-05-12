import logging
import pandas as pd
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class AzureCostDataProcessor:
    """Process and transform Azure cost management data."""
    
    def __init__(self):
        """Initialize the data processor."""
        pass
        
    def extract_resource_name(self, resource_id):
        """
        Extract the resource name from the resource ID.
        
        Args:
            resource_id (str): Azure resource ID
            
        Returns:
            str: The extracted resource name
        """
        # Extract the last part of the resource ID which is typically the resource name
        if not resource_id:
            return "unknown-resource"
            
        # Match the resource name pattern in Azure resource IDs
        match = re.search(r'/providers/[^/]+/[^/]+/([^/]+)$', resource_id)
        if match:
            return match.group(1)
            
        # If no match is found, return the last segment
        parts = resource_id.strip('/').split('/')
        return parts[-1] if parts else "unknown-resource"
        
    def process_cost_data(self, cost_data):
        """
        Process and transform Azure cost data into a structured format.
        
        Args:
            cost_data (dict): Azure cost management API response
            
        Returns:
            pd.DataFrame: Processed cost data as a DataFrame
        """
        # Validation di input
        if not isinstance(cost_data, dict):
            logger.error("Errore 400: I dati di costo forniti non sono in formato valido (dizionario)")
            return pd.DataFrame(columns=["Date", "ResourceName", "ResourceId", "CostUSD", "CostEUR"])
            
        # Controllo per errori di autenticazione nell'API
        if cost_data.get("error"):
            error_info = cost_data.get("error", {})
            error_code = error_info.get("code", "Sconosciuto")
            error_message = error_info.get("message", "Nessun messaggio di errore")
            
            if "401" in str(error_code):
                logger.error(f"Errore 401: Autenticazione fallita - {error_message}")
            elif "403" in str(error_code):
                logger.error(f"Errore 403: Accesso vietato - {error_message}")
            else:
                logger.error(f"Errore API: {error_code} - {error_message}")
            
            return pd.DataFrame(columns=["Date", "ResourceName", "ResourceId", "CostUSD", "CostEUR"])
        
        if not cost_data or "properties" not in cost_data or "rows" not in cost_data["properties"]:
            logger.warning("No cost data found or invalid format")
            return pd.DataFrame(columns=["Date", "ResourceName", "ResourceId", "CostUSD", "CostEUR"])
            
        rows = cost_data["properties"]["rows"]
        if not rows:
            logger.warning("No cost data rows found")
            return pd.DataFrame(columns=["Date", "ResourceName", "ResourceId", "CostUSD", "CostEUR"])
            
        # Extract column names from the response
        columns = cost_data["properties"]["columns"]
        column_names = [col["name"] for col in columns]
        
        logger.info(f"Processing {len(rows)} cost data entries")
        logger.debug(f"Available columns: {', '.join(column_names)}")
        
        # Create a DataFrame from the rows
        df = pd.DataFrame(rows, columns=column_names)
        
        # Process the data
        processed_data = []
        error_rows = 0
        
        for idx, row in df.iterrows():
            try:
                # Extract date from BillingMonth column instead of usageStart
                date_str = None
                date_column_found = False
                
                # Prima cerca BillingMonth, che è il nome corretto
                if any("billingmonth" in col.lower() for col in column_names):
                    for col in column_names:
                        if "billingmonth" in col.lower():
                            date_str = row[col]
                            date_column_found = True
                            logger.debug(f"Data trovata nella colonna {col}: {date_str}")
                            break
                
                # Se non trova BillingMonth, prova con altre colonne potenziali di data
                if not date_column_found:
                    date_columns = ["usagestart", "date", "timestamp", "period", "month"]
                    for date_col in date_columns:
                        for col in column_names:
                            if date_col in col.lower():
                                date_str = row[col]
                                date_column_found = True
                                logger.warning(f"BillingMonth non trovato, utilizzando colonna alternativa {col}: {date_str}")
                                break
                        if date_column_found:
                            break
                
                if not date_column_found:
                    logger.warning(f"Attenzione: Nessuna colonna data trovata nei dati. Colonne disponibili: {', '.join(column_names)}")
                    continue
                
                if not date_str:
                    logger.warning(f"Riga {idx}: Valore data mancante")
                    continue
                
                # Parse and format the date - gestione più formati di data possibili
                formatted_date = None
                date_formats = [
                    # Formato ISO 8601 (YYYY-MM-DDT00:00:00) - Aggiunto per risolvere l'errore
                    ("%Y-%m-%dT%H:%M:%S", lambda dt: dt.strftime("%Y-%m-%d")),
                    # Formato BillingMonth comune: "202302" (YYYYMM)
                    ("%Y%m", lambda dt: dt.strftime("%Y-%m-%d")),
                    # Altri formati possibili
                    ("%Y%m%dT%H%M%SZ", lambda dt: dt.strftime("%Y-%m-%d")),
                    ("%Y%m%dT%H%M%S%z", lambda dt: dt.strftime("%Y-%m-%d")),
                    ("%Y%m%dT%H%M%S", lambda dt: dt.strftime("%Y-%m-%d")),
                    ("%Y-%m-%d", lambda dt: dt.strftime("%Y-%m-%d")),
                    ("%Y/%m/%d", lambda dt: dt.strftime("%Y-%m-%d"))
                ]
                
                for date_format, formatter in date_formats:
                    try:
                        date_obj = datetime.strptime(str(date_str), date_format)
                        formatted_date = formatter(date_obj)
                        logger.debug(f"Data parsata con formato {date_format}: {formatted_date}")
                        break
                    except ValueError:
                        continue
                
                if not formatted_date:
                    logger.error(f"Riga {idx}: Formato data non riconosciuto: {date_str}")
                    error_rows += 1
                    continue
                
                # Find resource ID column
                resource_id = None
                for col in column_names:
                    if "resourceid" in col.lower():
                        resource_id = row[col]
                        break
                
                if not resource_id:
                    logger.warning(f"Riga {idx}: ResourceId mancante")
                    continue
                
                # Extract resource name
                resource_name = self.extract_resource_name(resource_id)
                
                # Find cost columns
                cost_usd = None
                cost_eur = None
                
                for col in column_names:
                    if "costusd" in col.lower():
                        cost_usd = row[col] if row[col] is not None else 0
                    elif "cost" in col.lower() and "usd" not in col.lower():
                        cost_eur = row[col] if row[col] is not None else 0
                
                # Validazione dei valori di costo
                try:
                    cost_usd = float(cost_usd) if cost_usd is not None else 0.0
                    cost_eur = float(cost_eur) if cost_eur is not None else 0.0
                except (ValueError, TypeError):
                    logger.warning(f"Riga {idx}: Valore di costo non valido. USD: {cost_usd}, EUR: {cost_eur}")
                    # Usa 0 come fallback
                    cost_usd = 0.0
                    cost_eur = 0.0
                
                # Append processed row
                processed_data.append({
                    "Date": formatted_date,
                    "ResourceName": resource_name,
                    "ResourceId": resource_id,
                    "CostUSD": cost_usd,
                    "CostEUR": cost_eur
                })
                
            except Exception as e:
                logger.error(f"Errore processando riga {idx}: {str(e)}")
                error_rows += 1
                continue
        
        # Report processamento
        if error_rows > 0:
            logger.warning(f"{error_rows} righe non sono state processate a causa di errori")
        
        # Create the final DataFrame
        result_df = pd.DataFrame(processed_data)
        
        # Aggregate by date and resource name
        if not result_df.empty:
            result_df = result_df.groupby(["Date", "ResourceName"], as_index=False).agg({
                "ResourceId": "first",
                "CostUSD": "sum",
                "CostEUR": "sum"
            })
            
            # Sort by date and resource name
            result_df = result_df.sort_values(["Date", "ResourceName"])
            
        logger.success(f"Successfully processed {len(result_df)} cost data entries")
        return result_df