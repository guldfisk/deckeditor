import queue
import typing as t
from concurrent.futures.thread import ThreadPoolExecutor


class LIFOExecutor(ThreadPoolExecutor):
    def __init__(
        self,
        max_workers: t.Optional[int] = None,
        thread_name_prefix: str = "",
        initializer: t.Optional[t.Callable[..., None]] = None,
        initargs: t.Tuple[t.Any, ...] = (),
    ) -> None:
        super().__init__(max_workers, thread_name_prefix, initializer, initargs)
        self._work_queue = queue.LifoQueue()
