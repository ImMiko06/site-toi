#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir))
    vendor = base_dir / ".vendor"
    if vendor.exists():
        sys.path.insert(0, str(vendor))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
