import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, date
from ..utils.path_utils import PROJECT_ROOT, ensure_dir_exists

# Load environment variables from .env file
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

# Ensure output directory exists
OUTPUT_DIR = PROJECT_ROOT / "output"
ensure_dir_exists(OUTPUT_DIR)

# Azure settings
AZURE_BASE_URL = "https://management.azure.com"
AZURE_API_VERSION = "2021-10-01"
DEFAULT_TOP_VALUE = "5000"

# Authentication settings
# Set AUTH_TYPE to either "bearer_token" or "client_credentials"
AUTH_TYPE = os.getenv("AUTH_TYPE", "bearer_token") 
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_BEARER_TOKEN = os.getenv("AZURE_BEARER_TOKEN")
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
AZURE_RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP")

# Default CSV export path
DEFAULT_EXPORT_PATH = os.getenv("DEFAULT_EXPORT_PATH", str(OUTPUT_DIR / "azure_costs.csv"))

# Date filtering settings
def _get_default_date(date_str, default_function):
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return default_function()
    return default_function()

# Default date range - today if not specified or invalid
def _default_from_date():
    return date(date.today().year, 1, 1)  # January 1st of current year

def _default_to_date():
    return date.today()  # Today

# Parse from environment or use defaults
DEFAULT_FROM_DATE = _get_default_date(os.getenv("DEFAULT_FROM_DATE"), _default_from_date)
DEFAULT_TO_DATE = _get_default_date(os.getenv("DEFAULT_TO_DATE"), _default_to_date)

# Service filtering settings
DEFAULT_SERVICES = [s.strip() for s in os.getenv("DEFAULT_SERVICES", "").split(",") if s.strip()]
COST_THRESHOLD = float(os.getenv("COST_THRESHOLD", "0.0"))
MAX_DAYS_PER_REQUEST = int(os.getenv("MAX_DAYS_PER_REQUEST", "366"))

# CSV Settings
CSV_DELIMITER = ";"
DECIMAL_SEPARATOR = ","  # European format

# Request timeout in seconds
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))

# Maximum retries for API calls
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# Retry delay in seconds
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 2))