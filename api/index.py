import sys
import os

# Ensure parent directory is on sys.path so app, models, config, and services import seamlessly
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app
