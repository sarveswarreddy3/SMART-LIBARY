import sys
import os

# Add project root directory to sys.path so app, config, models, and services resolve
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app
