import atexit
import json
import logging
import os
import queue
import threading
import re
from datetime import datetime, timezone

import pymongo


class MongoHandler(logging.Handler):
    """Asynchronous logging handler that writes to MongoDB in batches.

    Usage:
        handler = MongoHandler()
        handler.set_service("web-flask")
        handler.setLevel(logging.WARNING)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, uri=None, database="smart_campus_logs",
                 collection="logs", batch_size=50, flush_interval=1.0):
        super().__init__()
        self._queue = queue.Queue()
        uri = uri or os.environ.get(
            "MONGODB_LOG_URI", "mongodb://localhost:27017/smart_campus_logs"
        )
        self._client = pymongo.MongoClient(uri)
        self._col = self._client[database][collection]
        self._batch_size = batch_size
        self._running = True
        self._service = "python"

        # Output sanitization patterns
        self._phone_re = re.compile(r"1[3-9]\d{9}")
        self._idcard_re = re.compile(r"\d{17}[\dXx]")
        self._jwt_re = re.compile(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+")

        self._worker = threading.Thread(target=self._batch_loop, daemon=True)
        self._worker.start()
        atexit.register(self._flush_on_exit)

    def set_service(self, service: str):
        self._service = service

    def emit(self, record: logging.LogRecord):
        try:
            doc = self._build_doc(record)
            self._queue.put_nowait(doc)
        except Exception:
            self.handleError(record)

    def _build_doc(self, record: logging.LogRecord) -> dict:
        msg = self.format(record)

        # Sensitive data masking
        msg = self._phone_re.sub("138****1234", msg)
        msg = self._idcard_re.sub("****************", msg)
        msg = self._jwt_re.sub("***JWT***", msg)

        doc = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
            "service": self._service,
        }

        # Extract trace_id, user_id, endpoint from log record extras
        if hasattr(record, "trace_id") and record.trace_id:
            doc["trace_id"] = record.trace_id
        if hasattr(record, "user_id") and record.user_id:
            doc["user_id"] = record.user_id
        if hasattr(record, "endpoint") and record.endpoint:
            doc["endpoint"] = record.endpoint

        # Metadata for service-specific context
        if hasattr(record, "metadata") and record.metadata:
            doc["metadata"] = record.metadata

        # Stack trace for ERROR level
        if record.exc_info and record.exc_info[1]:
            doc["stack_trace"] = f"{type(record.exc_info[1]).__name__}: {record.exc_info[1]}"

        return doc

    def _batch_loop(self):
        while self._running:
            try:
                batch = []
                batch.append(self._queue.get())
                for _ in range(self._batch_size - 1):
                    try:
                        batch.append(self._queue.get_nowait())
                    except queue.Empty:
                        break
                self._flush(batch)
            except Exception:
                pass

    def _flush(self, batch: list):
        if not batch:
            return
        try:
            self._col.insert_many(batch, ordered=False)
        except pymongo.errors.BulkWriteError:
            pass
        except Exception:
            pass

    def _flush_on_exit(self):
        self._running = False
        remaining = []
        while not self._queue.empty():
            try:
                remaining.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if remaining:
            self._flush(remaining)
        self._client.close()
