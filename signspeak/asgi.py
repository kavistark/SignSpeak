"""
ASGI config for signspeak project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'signspeak.settings')

application = get_asgi_application()
