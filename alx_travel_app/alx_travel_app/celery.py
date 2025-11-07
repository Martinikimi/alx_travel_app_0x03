import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

# Create Celery app instance
app = Celery('alx_travel_app')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')