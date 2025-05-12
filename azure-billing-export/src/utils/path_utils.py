from pathlib import Path
import os

# Get the absolute path of the project root directory
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))).resolve()
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"

def ensure_dir_exists(directory_path):
    """Ensure that the directory exists, create it if it doesn't."""
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    
def get_absolute_path(relative_path):
    """Convert relative path to absolute path based on project root."""
    return PROJECT_ROOT / relative_path

def get_csv_output_path(filename):
    return get_absolute_path(f"output/{filename}.csv")