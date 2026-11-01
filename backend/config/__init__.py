try:
    from .celery import app as celery_app
except ImportError:  # Celery is optional for deployments using the database email queue.
    celery_app = None
