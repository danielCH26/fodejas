import logging
import sys
from contextvars import ContextVar
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

from pythonjsonlogger import jsonlogger

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)


def get_user_id() -> str:
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    user_id_var.set(user_id)


class JSONFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["module"] = record.module
        log_record["process"] = record.process
        log_record["thread"] = record.thread
        log_record["request_id"] = get_request_id()
        user_id = get_user_id()
        if user_id:
            log_record["user_id"] = user_id

        if hasattr(record, "request") and record.request:
            redacted_path = getattr(record.request, "_redacted_path", None)
            redacted_query = getattr(record.request, "_redacted_query", None)
            if redacted_path:
                log_record["path"] = redacted_path
            if redacted_query:
                log_record["query_string"] = redacted_query


def setup_logging(is_production: bool = False) -> None:
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)

    if is_production:
        formatter = JSONFormatter(
            "%(timestamp)s %(level)s %(name)s %(module)s %(process)d %(thread)d %(message)s"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    else:
        formatter = logging.Formatter(
            "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)


def setup_async_logging(is_production: bool = False) -> None:
    log_queue = Queue(-1)
    queue_handler = QueueHandler(log_queue)

    if is_production:
        formatter = JSONFormatter(
            "%(timestamp)s %(level)s %(name)s %(module)s %(process)d %(thread)d %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    queue_listener = QueueListener(log_queue, stream_handler, respect_handler_level=True)
    queue_listener.start()

    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)
    root_logger.setLevel(logging.DEBUG if not is_production else logging.INFO)

    return queue_listener
