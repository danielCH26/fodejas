"""FODEJAS Django project package.

Importing the Celery app here ensures it is loaded whenever
Django starts so that ``@shared_task`` decorators and beat
schedules register correctly (CHG-802 / AUD-016).
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
