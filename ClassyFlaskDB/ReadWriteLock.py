import threading
from contextlib import contextmanager

class ReaderWriterLock:
    def __init__(self):
        self._condition = threading.Condition(threading.Lock())
        self._readers = {}  # Dict to store reader count per thread
        self._writer = None
        self._writer_refcount = 0
        self._writer_queue = []

    @contextmanager
    def read_lock(self):
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write_lock(self):
        if self.acquire_write():
            try:
                yield
            finally:
                self.release_write()
        else:
            raise RuntimeError("Failed to acquire write lock")

    def acquire_read(self):
        current_thread = threading.current_thread()
        with self._condition:
            if self._writer == current_thread:
                # Writer can always read
                self._readers.setdefault(current_thread, 0)
                self._readers[current_thread] += 1
            else:
                while self._writer is not None:
                    self._condition.wait()
                self._readers.setdefault(current_thread, 0)
                self._readers[current_thread] += 1

    def release_read(self):
        current_thread = threading.current_thread()
        with self._condition:
            self._readers[current_thread] -= 1
            if self._readers[current_thread] == 0:
                del self._readers[current_thread]
            if len(self._readers) == 0:
                self._condition.notify_all()

    def acquire_write(self):
        current_thread = threading.current_thread()
        with self._condition:
            if self._writer == current_thread:
                self._writer_refcount += 1
                return True
            elif self._writer is None and len(self._readers) == 0:
                self._writer = current_thread
                self._writer_refcount = 1
                return True
            else:
                self._writer_queue.append(current_thread)
                while self._writer != current_thread:
                    self._condition.wait()
                self._writer_queue.remove(current_thread)
                self._writer_refcount = 1
                return True

    def release_write(self):
        with self._condition:
            if self._writer != threading.current_thread():
                raise RuntimeError("Cannot release a write lock that you don't own")
            self._writer_refcount -= 1
            if self._writer_refcount == 0:
                self._writer = None
                if self._writer_queue:
                    self._writer = self._writer_queue[0]
                    self._condition.notify_all()
                else:
                    self._condition.notify_all()