"""Implements a closable Queue class for passing around SAXS commands."""
import threading
import sys
import queue


class Closed(Exception):
    """Not sure why this is a special Exception."""

    pass


class CQueue(queue.Queue):
    """Extension of a Queue that can be temporarily locked."""

    def __init__(self, maxsize=0):
        """Initialize the queue and set to an open state."""
        queue.Queue.__init__(self, maxsize)

        self.use_put = threading.Lock()
        self._can_put = True

    def open(self):
        """Reopen the queue."""
        self.use_put.acquire()
        self._can_put = True
        self.use_put.release()

    def close(self, empty=False):
        """Close and the queue, forbidding subsequent 'put'.

        If 'empty' is true, empty the queue, and return the queue items
        """
        self.use_put.acquire()
        self._can_put = False
        self.use_put.release()

        items = []

        if empty:

            try:
                while True:
                    items.append(self.get_nowait())
            except queue.Empty:
                pass

            return items

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until a free slot is available. If 'timeout' is a positive number, it blocks at
        most 'timeout' seconds and raises the Full exception if no free slot was available within that time.
        Otherwise ('block' is false), put an item on the queue if a free slot is immediately available,
        else raise the Full exception ('timeout') is ignored in that case).
        """
        self.not_full.acquire()

        try:

            if self.maxsize > 0:
                if not block:
                    if self._qsize() == self.maxsize:
                        raise queue.Full

                elif timeout is None:
                    while self._qsize() == self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                else:
                    endtime = _time() + timeout

                    while self._qsize() == self.maxsize:
                        remaining = endtime - _time()
                        if remaining <= 0.0:
                            raise queue.Full

                        self.not_full.wait(remaining)

            self.use_put.acquire()

            try:
                if self._can_put:
                    self._put(item)
                    self.unfinished_tasks += 1
                    self.not_empty.notify()
                else:
                    raise Closed

            finally:
                self.use_put.release()
        finally:
            self.not_full.release()


if __name__ == "__main__":
    pass
