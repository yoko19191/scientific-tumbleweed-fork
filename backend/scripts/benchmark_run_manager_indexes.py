"""Local benchmark for RunManager indexed hot paths.

Run from backend:
    PYTHONPATH=. uv run python scripts/benchmark_run_manager_indexes.py
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from collections.abc import Awaitable, Callable

from deerflow.runtime.runs.manager import ConflictError, RunManager
from deerflow.runtime.runs.schemas import RunStatus


async def _measure(label: str, fn: Callable[[], Awaitable[object]], *, iterations: int) -> tuple[str, float]:
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await fn()
        samples.append(time.perf_counter() - start)
    return label, statistics.mean(samples) * 1_000


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark RunManager indexed paths against naive full scans.")
    parser.add_argument("--runs", type=int, default=10_000)
    parser.add_argument("--threads", type=int, default=100)
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()

    manager = RunManager()
    thread_ids = [f"thread-{idx}" for idx in range(args.threads)]
    target_thread = thread_ids[args.threads // 2]

    for idx in range(args.runs):
        record = await manager.create(thread_ids[idx % args.threads])
        await manager.set_status(record.run_id, RunStatus.success)

    inflight = await manager.create(target_thread)
    await manager.set_status(inflight.run_id, RunStatus.running)

    async def indexed_has_inflight() -> bool:
        return await manager.has_inflight(target_thread)

    async def naive_has_inflight() -> bool:
        return any(
            record.thread_id == target_thread and record.status in (RunStatus.pending, RunStatus.running)
            for record in manager._runs.values()
        )

    async def indexed_list_by_thread() -> list:
        return await manager.list_by_thread(target_thread)

    async def naive_list_by_thread() -> list:
        records = [record for record in manager._runs.values() if record.thread_id == target_thread]
        return sorted(reversed(records), key=lambda record: record.created_at, reverse=True)[:100]

    async def indexed_create_or_reject_conflict() -> None:
        try:
            await manager.create_or_reject(target_thread)
        except ConflictError:
            return
        raise AssertionError("expected conflict")

    async def naive_create_or_reject_conflict() -> None:
        if await naive_has_inflight():
            return
        raise AssertionError("expected conflict")

    measurements = [
        await _measure("has_inflight indexed", indexed_has_inflight, iterations=args.iterations),
        await _measure("has_inflight naive", naive_has_inflight, iterations=args.iterations),
        await _measure("list_by_thread indexed", indexed_list_by_thread, iterations=args.iterations),
        await _measure("list_by_thread naive", naive_list_by_thread, iterations=args.iterations),
        await _measure("create_or_reject conflict indexed", indexed_create_or_reject_conflict, iterations=args.iterations),
        await _measure("create_or_reject conflict naive-check", naive_create_or_reject_conflict, iterations=args.iterations),
    ]

    print(f"dataset: runs={args.runs} threads={args.threads} iterations={args.iterations} target={target_thread}")
    for label, mean_ms in measurements:
        print(f"{label}: {mean_ms:.4f} ms/op")


if __name__ == "__main__":
    asyncio.run(_main())
