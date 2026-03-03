"""
Example distributed tasks for the WiFi-based framework.
Includes task generation, execution, and aggregation helpers.
"""

from typing import Callable, Dict, List
import time

from typing import Union

TaskPayload = Dict[str, Union[int, list]]


def generate_range_sum_tasks(start: int, end: int, chunk_size: int = 10000) -> List[Dict]:
    """Split a numeric range into chunked sum tasks."""
    tasks = []
    current = start
    task_id = 1
    while current <= end:
        chunk_end = min(current + chunk_size - 1, end)
        tasks.append({
            "task_id": f"range-{task_id}",
            "task_name": "range_sum",
            "payload": {"start": current, "end": chunk_end}
        })
        task_id += 1
        current = chunk_end + 1
    return tasks


def generate_array_sum_tasks(numbers: List[int], chunk_size: int = 5000) -> List[Dict]:
    """Split a list of numbers into chunked array_sum tasks."""
    tasks = []
    task_id = 1
    for i in range(0, len(numbers), chunk_size):
        chunk = numbers[i:i+chunk_size]
        tasks.append({
            "task_id": f"array-{task_id}",
            "task_name": "array_sum",
            "payload": {"numbers": chunk}
        })
        task_id += 1
    return tasks


def execute_task(task_name: str, payload: TaskPayload, progress_cb: Callable[[float], None]) -> Dict:
    """Execute a supported task and return its result dict."""
    if task_name == "range_sum":
        return _execute_range_sum(payload, progress_cb)
    if task_name == "array_sum":
        return _execute_array_sum(payload, progress_cb)
    else:
        raise ValueError(f"Unsupported task: {task_name}")


def _execute_range_sum(payload: TaskPayload, progress_cb: Callable[[float], None]) -> Dict:
    start = int(payload.get("start", 0))
    end = int(payload.get("end", -1))
    if end < start:
        raise ValueError("Invalid range: end must be >= start")

    total = 0
    count = end - start + 1
    report_every = max(1, count // 10)  # report ~10 times

    for idx, value in enumerate(range(start, end + 1), start=1):
        total += value
        if progress_cb and (idx % report_every == 0 or idx == count):
            progress_cb(idx / count)

    return {
        "partial_sum": total,
        "count": count,
        "range": [start, end]
    }


def _execute_array_sum(payload: TaskPayload, progress_cb: Callable[[float], None]) -> Dict:
    numbers = payload.get("numbers", []) or []
    if not isinstance(numbers, list):
        raise ValueError("numbers must be a list")

    total = 0
    count = len(numbers)
    if count == 0:
        return {"partial_sum": 0, "count": 0, "range": None}

    report_every = max(1, count // 10)
    for idx, value in enumerate(numbers, start=1):
        total += value
        if progress_cb and (idx % report_every == 0 or idx == count):
            progress_cb(idx / count)

    return {
        "partial_sum": total,
        "count": count,
        "range": None
    }


def aggregate_range_sum(results: List[Dict]) -> Dict:
    """Aggregate partial range_sum results into a final total."""
    total_sum = 0
    total_count = 0
    ranges = []

    for res in results:
        total_sum += res.get("partial_sum", 0)
        total_count += res.get("count", 0)
        if "range" in res:
            ranges.append(res["range"])

    return {
        "task": "range_sum",
        "total_sum": total_sum,
        "total_numbers": total_count,
        "ranges": ranges
    }


def aggregate_array_sum(results: List[Dict]) -> Dict:
    total_sum = 0
    total_count = 0
    for res in results:
        total_sum += res.get("partial_sum", 0)
        total_count += res.get("count", 0)
    return {
        "task": "array_sum",
        "total_sum": total_sum,
        "total_numbers": total_count,
    }


SUPPORTED_TASKS = {
    "range_sum": {
        "description": "Sum all integers in a range [start, end]",
        "generator": generate_range_sum_tasks,
        "aggregator": aggregate_range_sum,
    },
    "array_sum": {
        "description": "Sum all numbers in an array (optionally chunked)",
        "generator": generate_array_sum_tasks,
        "aggregator": aggregate_array_sum,
    }
}
