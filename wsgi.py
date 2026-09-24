"""
WSGI Configuration for PythonAnywhere & Production Deployments.

On PythonAnywhere, configure your WSGI configuration file in the 'Web' tab
to point to your project directory and import this application.
"""

import sys
import os

# Ensure the project root directory is in the Python path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the Flask application object for WSGI servers
from app import application

if __name__ == "__main__":
    application.run()
