from prometheus_client import Counter, Histogram

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total number of Celery tasks",
    ["task_name", "status"],
)

celery_task_latency_seconds = Histogram(
    "celery_task_latency_seconds",
    "Celery task latency in seconds",
    ["task_name"],
)
