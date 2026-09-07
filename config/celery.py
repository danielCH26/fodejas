"""Celery application instance for the FODEJAS platform (CHG-802).

Defines the canonical ``app`` used by both the worker (``celery -A
config worker``) and the beat scheduler (``celery -A config beat``).
The app autodiscovers ``tasks`` modules from every installed
Django app, so adding ``@shared_task`` to any
``apps/<x>/tasks.py`` is picked up automatically.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("fodejas")

# Read ``CELERY_*`` settings from Django settings (broker, result
# backend, beat schedule, time zone, etc.).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover ``tasks`` modules from every app under
# ``INSTALLED_APPS`` so each app can ship its own ``tasks.py``.
app.autodiscover_tasks()
