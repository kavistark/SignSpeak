"""
WSGI config for signspeak project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'signspeak.settings')

application = get_wsgi_application()
