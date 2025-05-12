import logging
import sys
from colorama import init, Fore, Style

# Initialize colorama
init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages based on log level."""
    
    COLORS = {
        'DEBUG': Style.RESET_ALL,
        'INFO': Fore.BLUE,       # Blue for general information
        'SUCCESS': Fore.GREEN,   # Green for success messages
        'WARNING': Fore.YELLOW,  # Yellow for warnings
        'ERROR': Fore.RED,       # Red for errors
        'CRITICAL': Fore.RED + Style.BRIGHT  # Bright red for critical
    }

    def format(self, record):
        # Add custom SUCCESS level
        if not hasattr(logging, 'SUCCESS'):
            logging.SUCCESS = 25  # Between INFO and WARNING
            logging.addLevelName(logging.SUCCESS, 'SUCCESS')
            
            def success(self, message, *args, **kwargs):
                self.log(logging.SUCCESS, message, *args, **kwargs)
            
            logging.Logger.success = success
            
        # Get the original format
        log_message = super().format(record)
        
        # Apply color based on log level
        color = self.COLORS.get(record.levelname, Style.RESET_ALL)
        return f"{color}{log_message}{Style.RESET_ALL}"

def configure_logging(log_level=logging.INFO):
    """Configure logging with colored output."""
    # Create a custom formatter
    formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("azure_billing_export.log"),
            logging.StreamHandler()
        ]
    )

    # Set different log levels for different modules
    logging.getLogger("azure_client").setLevel(logging.DEBUG)
    logging.getLogger("data_processor").setLevel(logging.WARNING)
    logging.getLogger("export").setLevel(logging.ERROR)

setup_logging()