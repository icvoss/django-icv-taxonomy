#!/usr/bin/env python
"""Django's command-line utility for the icv-taxonomy consumer smoke-test
harness (ADR-027).

Mirrors a real installing project: a throwaway Django project that installs
icv_taxonomy as a built wheel (per CI's smoke-test job) and configures the
swappable Vocabulary/Term models via a small local app, exactly as a real
consumer would. Not used for feature testing; only for `makemigrations
--check` and `migrate`.
"""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "consumer_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
