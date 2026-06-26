import time

from celery import signals

from apps.core.metrics import celery_task_latency_seconds, celery_tasks_total


@signals.task_prerun.connect
def task_prerun_handler(task, **kwargs):
    task._start_time = time.time()


@signals.task_postrun.connect
def task_postrun_handler(task, **kwargs):
    if hasattr(task, "_start_time"):
        duration = time.time() - task._start_time
        celery_task_latency_seconds.labels(task_name=task.name).observe(duration)
        celery_tasks_total.labels(task_name=task.name, status="success").inc()


@signals.task_failure.connect
def task_failure_handler(task, **kwargs):
    celery_tasks_total.labels(task_name=task.name, status="failure").inc()
