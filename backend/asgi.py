import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application


base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))
vendor = base_dir / ".vendor"
if vendor.exists():
    sys.path.insert(0, str(vendor))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_asgi_application()
