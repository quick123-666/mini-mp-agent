"""asyncio.TaskQueue + WorkerPool for concurrent task execution.

Phase 3 ship (2026-07-17 23:30).

Design (M-TaskQueue-001 [imp=0.7]):
  - asyncio.Queue (max_size=100) holds tasks
  - N workers (default 3) consume queue concurrently
  - each worker: get → execute (sync or coroutine) → record result with duration
  - backpressure: queue full → submit raises asyncio.QueueFull

Usage:
    async with TaskQueueContext(workers=3) as queue:
        queue.submit("task-1", lambda: "hello")
        queue.submit("task-2", lambda: time.sleep(0.1))
        await queue.join()
        results = queue.results

    # Or sync batch:
    results = run_batch([("t1", fn1), ("t2", fn2)])
"""
from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union

DEFAULT_WORKERS = 3
DEFAULT_MAX_SIZE = 100
DEFAULT_TIMEOUT_S = 30.0


@dataclass
class QueueResult:
    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_s": self.duration_s,
        }


@dataclass
class _Task:
    task_id: str
    fn: Callable[[], Any]
    timeout_s: float


class TaskQueue:
    """asyncio task queue with worker pool. Phase 3 ship."""

    def __init__(self, workers: int = DEFAULT_WORKERS, max_size: int = DEFAULT_MAX_SIZE):
        self.workers_n = workers
        self.max_size = max_size
        self.queue: Optional[asyncio.Queue] = None
        self.results: dict[str, QueueResult] = {}
        self._worker_tasks: list[asyncio.Task] = []
        self._started = False

    async def start(self):
        """Initialize queue and spawn workers. Idempotent."""
        if self._started:
            return
        self.queue = asyncio.Queue(maxsize=self.max_size)
        for i in range(self.workers_n):
            t = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(t)
        self._started = True

    async def _worker_loop(self, name: str):
        """Worker: get task → execute → record result."""
        while True:
            try:
                qt: _Task = await self.queue.get()
            except asyncio.CancelledError:
                return
            start = time.time()
            try:
                result = await self._run_task(qt, start)
                self.results[qt.task_id] = QueueResult(
                    task_id=qt.task_id, success=True, result=result,
                    duration_s=time.time() - start,
                )
            except asyncio.TimeoutError:
                self.results[qt.task_id] = QueueResult(
                    task_id=qt.task_id, success=False,
                    error=f"timeout after {qt.timeout_s}s",
                    duration_s=time.time() - start,
                )
            except Exception as e:
                self.results[qt.task_id] = QueueResult(
                    task_id=qt.task_id, success=False, error=str(e),
                    duration_s=time.time() - start,
                )
            finally:
                self.queue.task_done()

    def submit(self, task_id: str, fn: Callable, timeout_s: float = DEFAULT_TIMEOUT_S) -> str:
        """Submit a task. Returns task_id. Raises asyncio.QueueFull if queue full."""
        if not self._started:
            raise RuntimeError("TaskQueue not started; call await start() first")
        qt = _Task(task_id=task_id, fn=fn, timeout_s=timeout_s)
        self.queue.put_nowait(qt)  # may raise asyncio.QueueFull
        return task_id

    async def _run_task(self, qt: "_Task", start: float) -> Any:
        """Run a single task, supporting both sync (executor) and async (direct).

        - sync fns run in ThreadPoolExecutor via run_in_executor for true parallelism
        - lambdas that return coroutines: run_in_executor returns the coroutine object,
          then we await it directly
        - proper async def functions: detected by iscoroutinefunction, awaited directly
        """
        if inspect.iscoroutinefunction(qt.fn):
            return await asyncio.wait_for(qt.fn(), timeout=qt.timeout_s)

        # Run sync / lambda in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, qt.fn)
        ret = await asyncio.wait_for(fut, timeout=qt.timeout_s)

        if inspect.iscoroutine(ret):
            # lambda returned a coroutine — await with remaining time
            elapsed = time.time() - start
            remaining = max(0.001, qt.timeout_s - elapsed)
            return await asyncio.wait_for(ret, timeout=remaining)
        return ret

    async def join(self):
        """Wait for all tasks to complete."""
        if self.queue:
            await self.queue.join()

    async def stop(self):
        """Cancel workers and wait."""
        for t in self._worker_tasks:
            t.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks = []
        self._started = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


def run_batch(
    tasks: list[tuple[str, Callable]],
    workers: int = DEFAULT_WORKERS,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, QueueResult]:
    """Sync convenience: run batch and return results.

    Args:
        tasks: list of (task_id, callable) tuples
        workers: number of concurrent workers
        timeout_s: per-task timeout

    Returns:
        dict of task_id → QueueResult
    """
    async def main():
        async with TaskQueue(workers=workers) as q:
            for tid, fn in tasks:
                q.submit(tid, fn, timeout_s=timeout_s)
            await q.join()
            return dict(q.results)

    return asyncio.run(main())


if __name__ == "__main__":
    # Demo: 5 tasks, 3 workers, mixed sync/async
    import time as _time

    def slow(n):
        _time.sleep(0.05)
        return f"sync-{n}"

    async def fast(n):
        await asyncio.sleep(0.01)
        return f"async-{n}"

    tasks = [(f"t{i}", (lambda n=i: slow(n)) if i % 2 == 0 else (lambda n=i: fast(n))) for i in range(5)]
    print("Submitting 5 tasks to 3 workers...")
    results = run_batch(tasks, workers=3)
    for tid, r in sorted(results.items()):
        print(f"  {tid}: success={r.success} result={r.result!r} duration={r.duration_s:.3f}s")
