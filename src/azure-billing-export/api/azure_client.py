import requests
import logging
import time
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ..config.settings import (
    AZURE_BASE_URL, 
    AZURE_API_VERSION,
    AUTH_TYPE,
    AZURE_TENANT_ID, 
    AZURE_CLIENT_ID, 
    AZURE_CLIENT_SECRET,
    AZURE_BEARER_TOKEN,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    DEFAULT_TOP_VALUE
)

logger = logging.getLogger(__name__)

class AzureAuthenticationError(Exception):
    """Eccezione sollevata per errori di autenticazione con Azure."""
    pass

class AzureRequestError(Exception):
    """Eccezione sollevata per errori nelle richieste API di Azure."""
    pass

class AzureCostManagementClient:
    """Client for interacting with Azure Cost Management API."""
    
    def __init__(self, subscription_id, resource_group_name, bearer_token=None, tenant_id=None, client_id=None, client_secret=None):
        """
        Initialize the Azure Cost Management client.
        
        Args:
            subscription_id (str): Azure subscription ID
            resource_group_name (str): Azure resource group name
            bearer_token (str, optional): Bearer token for authentication. If not provided,
                                          the token will be fetched using client credentials
                                          if AUTH_TYPE is set to "client_credentials"
            tenant_id (str, optional): Azure tenant ID for client credentials auth
            client_id (str, optional): Azure client ID for client credentials auth
            client_secret (str, optional): Azure client secret for client credentials auth
        """
        self.subscription_id = subscription_id
        self.resource_group_name = resource_group_name
        self.bearer_token = bearer_token
        self.tenant_id = tenant_id or AZURE_TENANT_ID
        self.client_id = client_id or AZURE_CLIENT_ID
        self.client_secret = client_secret or AZURE_CLIENT_SECRET
        self.base_url = AZURE_BASE_URL
        self.auth_type = AUTH_TYPE
        
        # Validate authentication configuration
        self._validate_authentication_config()
        
        # Get token if not provided and using client credentials auth
        if not self.bearer_token and self.auth_type == "client_credentials":
            logger.info("Retrieving Azure bearer token using client credentials...")
            try:
                self.bearer_token = self._get_token_from_client_credentials()
                if self.bearer_token:
                    logger.success("Successfully retrieved Azure bearer token")
            except AzureAuthenticationError as e:
                logger.error(f"Errore di autenticazione: {str(e)}")
                # Non sollevare l'eccezione qui, permettiamo al client di continuare
                # ma le chiamate API falliranno se non viene fornito un token valido successivamente
    
    def _validate_authentication_config(self):
        """Validate that the required authentication configuration is present."""
        if self.auth_type == "bearer_token" and not self.bearer_token:
            if AZURE_BEARER_TOKEN:
                logger.info("Using bearer token from environment variables")
                self.bearer_token = AZURE_BEARER_TOKEN
            else:
                raise ValueError("Bearer token must be provided for token authentication")
        
        if self.auth_type == "client_credentials":
            missing = []
            if not self.tenant_id:
                missing.append("tenant_id")
            if not self.client_id:
                missing.append("client_id")
            if not self.client_secret:
                missing.append("client_secret")
                
            if missing:
                raise ValueError(f"Errore di configurazione: {', '.join(missing)} devono essere forniti per l'autenticazione client credentials")
            
            logger.info("Using client credentials for authentication")
    
    def _get_token_from_client_credentials(self):
        """
        Get an Azure AD token using client credentials flow.
        
        Returns:
            str: The access token
        
        Raises:
            AzureAuthenticationError: If authentication fails
        """
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/token"
        
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'resource': 'https://management.azure.com/'
        }
        
        try:
            response = requests.post(token_url, data=token_data, timeout=REQUEST_TIMEOUT)
            
            # Verifica lo status code
            if response.status_code == 401:
                error_msg = "Autenticazione fallita: credenziali non valide"
                logger.error(error_msg)
                raise AzureAuthenticationError(error_msg)
            elif response.status_code == 403:
                error_msg = "Autenticazione fallita: accesso negato"
                logger.error(error_msg)
                raise AzureAuthenticationError(error_msg)
            elif response.status_code != 200:
                error_msg = f"Autenticazione fallita con status code: {response.status_code}"
                logger.error(f"{error_msg}. Response: {response.text}")
                raise AzureAuthenticationError(error_msg)
            
            token_json = response.json()
            return token_json.get('access_token')
        except requests.exceptions.ConnectionError:
            error_msg = "Impossibile connettersi al server di autenticazione Azure."
            logger.error(error_msg)
            raise AzureAuthenticationError(error_msg)
        except requests.exceptions.Timeout:
            error_msg = "Timeout durante la richiesta del token."
            logger.error(error_msg)
            raise AzureAuthenticationError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Errore durante la richiesta del token: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise AzureAuthenticationError(error_msg)
        except ValueError as e:
            error_msg = f"Risposta non valida dal server: {str(e)}"
            logger.error(error_msg)
            raise AzureAuthenticationError(error_msg)
    
    def _get_headers(self):
        """
        Get headers for API requests including authorization.
        
        Returns:
            dict: Headers to use in requests
        
        Raises:
            AzureAuthenticationError: If bearer token is not available
        """
        if not self.bearer_token:
            error_msg = "Bearer token non disponibile. Controlla le impostazioni di autenticazione."
            logger.error(error_msg)
            raise AzureAuthenticationError(error_msg)
            
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method, url, headers=None, json=None, params=None):
        """
        Make an HTTP request with retry logic.
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            url (str): Request URL
            headers (dict, optional): Request headers
            json (dict, optional): JSON body
            params (dict, optional): Query parameters
            
        Returns:
            requests.Response: Response object
        
        Raises:
            AzureRequestError: If the request fails after all retries
        """
        try:
            headers = headers or self._get_headers()
        except AzureAuthenticationError as e:
            raise AzureRequestError(f"Errore di autenticazione: {str(e)}")
            
        retries = 0
        last_exception = None
        
        while retries < MAX_RETRIES:
            try:
                logger.debug(f"Making {method} request to {url}")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Gestione esplicita degli errori comuni
                if response.status_code == 401:
                    # Token scaduto o non valido
                    error_msg = "Accesso non autorizzato (401): token non valido o scaduto"
                    logger.error(error_msg)
                    
                    # Prova a rinnovare il token se usiamo client credentials
                    if self.auth_type == "client_credentials" and retries < MAX_RETRIES - 1:
                        logger.info("Tentativo di rinnovare il token...")
                        try:
                            self.bearer_token = self._get_token_from_client_credentials()
                            headers = self._get_headers()  # Aggiorna gli headers con il nuovo token
                            retries += 1
                            logger.info(f"Token rinnovato, nuovo tentativo ({retries}/{MAX_RETRIES})...")
                            time.sleep(RETRY_DELAY)
                            continue
                        except AzureAuthenticationError as e:
                            logger.error(f"Impossibile rinnovare il token: {str(e)}")
                    
                    # Se non usiamo client credentials o il rinnovo è fallito
                    raise AzureRequestError(error_msg)
                
                elif response.status_code == 403:
                    error_msg = "Accesso vietato (403): non hai i permessi necessari per questa operazione"
                    logger.error(error_msg)
                    raise AzureRequestError(error_msg)
                
                elif response.status_code == 404:
                    error_msg = f"Risorsa non trovata (404): {url}"
                    logger.error(error_msg)
                    raise AzureRequestError(error_msg)
                
                elif response.status_code == 429:
                    # Troppe richieste, rispetta i limiti di throttling
                    retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                    logger.warning(f"Troppe richieste (429), attesa di {retry_after} secondi...")
                    
                    if retries < MAX_RETRIES - 1:
                        time.sleep(retry_after)
                        retries += 1
                        logger.info(f"Riprovando ({retries}/{MAX_RETRIES})...")
                        continue
                    else:
                        raise AzureRequestError("Troppe richieste (429): limite di tentativi raggiunto")
                
                elif response.status_code >= 500:
                    error_msg = f"Errore del server Azure ({response.status_code})"
                    
                    if retries < MAX_RETRIES - 1:
                        retries += 1
                        wait_time = RETRY_DELAY * (2 ** retries)  # Exponential backoff
                        logger.warning(f"{error_msg}, ritentativo {retries}/{MAX_RETRIES} tra {wait_time} secondi...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"{error_msg}: {response.text}")
                        raise AzureRequestError(error_msg)
                
                # Controlla lo status code per altri errori
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                last_exception = "Timeout della richiesta"
                logger.warning(f"{last_exception} (tentativo {retries+1}/{MAX_RETRIES})")
                
            except requests.exceptions.ConnectionError:
                last_exception = "Errore di connessione"
                logger.warning(f"{last_exception} (tentativo {retries+1}/{MAX_RETRIES})")
                
            except requests.exceptions.RequestException as e:
                last_exception = str(e)
                logger.warning(f"Richiesta fallita (tentativo {retries+1}/{MAX_RETRIES}): {last_exception}")
            
            # Incrementa il numero di tentativi e attendi prima di riprovare
            retries += 1
            
            if retries < MAX_RETRIES:
                wait_time = RETRY_DELAY * (2 ** (retries - 1))  # Exponential backoff
                logger.info(f"Ritentativo tra {wait_time} secondi...")
                time.sleep(wait_time)
            else:
                logger.error(f"Numero massimo di tentativi raggiunto per {url}")
                detailed_error = last_exception or "Errore sconosciuto"
                raise AzureRequestError(f"La richiesta è fallita dopo {MAX_RETRIES} tentativi: {detailed_error}")
    
    def get_cost_data(self, services, from_date, to_date):
        """
        Get cost data for the specified services and timeframe.
        If the time period is longer than a year, multiple requests will be made
        and the results will be aggregated.
        
        Args:
            services (list): List of service resource IDs to filter by
            from_date (str): Start date in format YYYY-MM-DD
            to_date (str): End date in format YYYY-MM-DD
            
        Returns:
            dict: Cost data response from Azure
        """
        # Validazione delle date
        try:
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
            
            # Verifica che la data di inizio sia precedente alla data di fine
            if from_date_obj > to_date_obj:
                error_msg = f"Errore: La data di inizio ({from_date}) è successiva alla data di fine ({to_date})"
                logger.error(error_msg)
                return {"error": {"code": "InvalidDateRange", "message": error_msg}}
            
            # Verifica che la data di fine non sia nel futuro
            if to_date_obj > datetime.now():
                logger.warning(f"Attenzione: La data di fine ({to_date}) è nel futuro, questo potrebbe restituire dati incompleti")
        
        except ValueError:
            error_msg = "Formato data non valido. Usa il formato YYYY-MM-DD"
            logger.error(error_msg)
            return {"error": {"code": "InvalidDateFormat", "message": error_msg}}
        
        # Validazione dei servizi
        if not services or not isinstance(services, list) or len(services) == 0:
            error_msg = "Nessun servizio specificato o formato non valido"
            logger.error(error_msg)
            return {"error": {"code": "InvalidServices", "message": error_msg}}
        
        # Check if date range is more than 1 year
        if (to_date_obj - from_date_obj).days > 366:
            logger.info(f"Date range is more than a year, splitting into multiple requests")
            return self._get_cost_data_in_chunks(services, from_date_obj, to_date_obj)
        
        # For shorter periods, make a single request
        return self._get_cost_data_for_period(services, from_date, to_date)
    
    def _get_cost_data_in_chunks(self, services, from_date_obj, to_date_obj):
        """
        Split cost data requests into yearly chunks.
        
        Args:
            services (list): List of service resource IDs to filter by
            from_date_obj (datetime): Start date
            to_date_obj (datetime): End date
            
        Returns:
            dict: Aggregated cost data
        """
        all_results = []
        current_from = from_date_obj
        
        while current_from < to_date_obj:
            # Calculate the end of this chunk (1 year later or the end date, whichever comes first)
            current_to = min(current_from + relativedelta(years=1, days=-1), to_date_obj)
            
            from_str = current_from.strftime("%Y-%m-%d")
            to_str = current_to.strftime("%Y-%m-%d")
            
            logger.info(f"Getting cost data for period {from_str} to {to_str}")
            chunk_result = self._get_cost_data_for_period(services, from_str, to_str)
            
            # Verifica se ci sono errori nella risposta
            if "error" in chunk_result:
                logger.error(f"Errore nell'ottenere i dati per il periodo {from_str} to {to_str}: {chunk_result['error'].get('message', 'Errore sconosciuto')}")
                return chunk_result  # Propagate the error
            
            if "properties" in chunk_result and "rows" in chunk_result["properties"]:
                all_results.extend(chunk_result["properties"]["rows"])
            
            # Move to the next chunk start
            current_from = current_to + timedelta(days=1)
        
        # Combine results into a single response structure
        if all_results:
            # Get the structure from the first result and replace the rows
            sample_result = self._get_cost_data_for_period(services, 
                                                          from_date_obj.strftime("%Y-%m-%d"), 
                                                          from_date_obj.strftime("%Y-%m-%d"))
            
            # Verifica se ci sono errori nella risposta
            if "error" in sample_result:
                logger.error(f"Errore nell'ottenere la struttura dei dati: {sample_result['error'].get('message', 'Errore sconosciuto')}")
                return sample_result
            
            sample_result["properties"]["rows"] = all_results
            return sample_result
        
        return {"properties": {"rows": []}}
    
    def _get_cost_data_for_period(self, services, from_date, to_date):
        """
        Get cost data for a specific time period (within a year).
        
        Args:
            services (list): List of service resource IDs to filter by
            from_date (str): Start date in format YYYY-MM-DD
            to_date (str): End date in format YYYY-MM-DD
            
        Returns:
            dict: Cost data response from Azure
        """
        url = (f"{self.base_url}/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}"
               f"/providers/Microsoft.CostManagement/query")
        
        params = {
            "api-version": AZURE_API_VERSION,
            "$top": DEFAULT_TOP_VALUE
        }
        
        # Create the request body
        data = {
            "type": "ActualCost",
            "dataSet": {
                "granularity": "Monthly",
                "aggregation": {
                    "totalCost": {
                        "name": "Cost",
                        "function": "Sum"
                    },
                    "totalCostUSD": {
                        "name": "CostUSD",
                        "function": "Sum"
                    }
                },
                "grouping": [
                    {
                        "type": "Dimension",
                        "name": "ResourceId"
                    },
                    {
                        "type": "Dimension",
                        "name": "ChargeType"
                    },
                    {
                        "type": "Dimension",
                        "name": "PublisherType"
                    }
                ]
            },
            "timeframe": "Custom",
            "timePeriod": {
                "from": from_date,
                "to": to_date
            }
        }
        
        # Add filter for specific services if provided
        if services and len(services) > 0:
            data["dataSet"]["filter"] = {
                "Dimensions": {
                    "Name": "ResourceId",
                    "Operator": "In",
                    "Values": services
                }
            }
        
        try:
            logger.info(f"Requesting cost data from {from_date} to {to_date} for {len(services)} services")
            response = self._make_request("POST", url, json=data, params=params)
            cost_data = response.json()
            
            row_count = len(cost_data["properties"]["rows"]) if "properties" in cost_data and "rows" in cost_data["properties"] else 0
            logger.success(f"Retrieved {row_count} cost data entries")
            
            return cost_data
            
        except AzureRequestError as e:
            error_msg = f"Errore nella richiesta dei dati di costo: {str(e)}"
            logger.error(error_msg)
            return {"error": {"code": "RequestError", "message": error_msg}}
            
        except AzureAuthenticationError as e:
            error_msg = f"Errore di autenticazione: {str(e)}"
            logger.error(error_msg)
            return {"error": {"code": "AuthenticationError", "message": error_msg}}
            
        except json.JSONDecodeError:
            error_msg = "Errore nella decodifica della risposta JSON"
            logger.error(error_msg)
            return {"error": {"code": "JSONDecodeError", "message": error_msg}}
            
        except Exception as e:
            error_msg = f"Errore imprevisto: {str(e)}"
            logger.error(error_msg)
            return {"error": {"code": "UnexpectedError", "message": error_msg}}