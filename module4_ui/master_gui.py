"""
Master GUI for distributing tasks across worker nodes.
Full integration with Module 1 (Discovery) and Module 3 (Execution).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import json
import sys
import socket
import inspect
import time
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import builtins
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "module1_discovery"))

from module3_execution.tasks import (
    get_all_tasks, register_custom_task, validate_file_attachments,
    aggregate_range_sum, aggregate_array_sum, get_task_info,
    generate_range_sum_tasks, generate_array_sum_tasks, SUPPORTED_TASKS
)
from custom_task_registry import (
    save_custom_task, load_custom_task, delete_custom_task, 
    clear_registry, distribute_task_to_workers, get_all_custom_tasks
)
from module4_ui.discovery_service import NodeDiscoveryService, AdvertiseService
from network_communication import MasterClient
from module1_discovery.discovery_service import DiscoveryService as Module1DiscoveryService
from module1_discovery.node_info import NodeInfoCollector

try:
    from module2_distribution.distribution_service import DistributionService
    from module2_distribution.task_manager import (
        SchedulingPolicy,
        LoadBalanceStrategy,
        Task as DistributionTask,
    )
except Exception:
    DistributionService = None
    SchedulingPolicy = None
    LoadBalanceStrategy = None
    DistributionTask = None


def extract_parameters_from_code(code: str) -> List[str]:
    """Extract parameter names from executor function code."""
    try:
        namespace = {}
        exec(code, namespace)
        executor_func = namespace.get("executor")
        
        if not executor_func:
            return []
        
        # Get function signature
        sig = inspect.signature(executor_func)
        params = list(sig.parameters.keys())
        
        # Remove 'payload' and 'progress_cb' (these are standard)
        required_params = [p for p in params if p not in ['payload', 'progress_cb']]
        
        # Try to extract from payload keys in docstring or code
        extracted_from_code = extract_payload_keys(code)
        return extracted_from_code if extracted_from_code else required_params
    except Exception as e:
        return []


def extract_payload_keys(code: str) -> List[str]:
    """Extract payload parameter keys from executor code."""
    import re
    keys = set()
    
    # Pattern 1: payload.get("key_name") or payload.get('key_name')
    # Handles whitespace variations
    pattern1 = r'payload\s*\.\s*get\s*\(\s*["\']([^"\']+)["\']\s*[,\)]'
    matches = re.findall(pattern1, code)
    keys.update(matches)
    
    # Pattern 2: payload["key_name"] or payload['key_name']
    pattern2 = r'payload\s*\[\s*["\']([^"\']+)["\']\s*\]'
    matches = re.findall(pattern2, code)
    keys.update(matches)
    
    # Pattern 3: In comments like # dataset_files, numbers, etc.
    pattern3 = r'#.*?([a-z_][a-z0-9_]*)'
    matches = re.findall(pattern3, code.lower())
    # Filter to reasonable looking parameter names (length > 2)
    keys.update([m for m in matches if len(m) > 2 and not m.isdigit()])
    
    return sorted(list(keys))


def resolve_task_parameters(task_info: Optional[Dict]) -> Tuple[List[str], Dict[str, str]]:
    """Resolve task parameter names and defaults from task metadata safely.

    Supports legacy/custom registry formats where `parameters` may be either:
    - list[str]: parameter names only
    - dict[str, Any]: parameter -> default value
    """
    if not task_info:
        return [], {}

    params: List[str] = []
    defaults: Dict[str, str] = {}

    stored_parameters = task_info.get("parameters", [])

    if isinstance(stored_parameters, dict):
        defaults = {str(k): v for k, v in stored_parameters.items()}
        params = list(defaults.keys())
    elif isinstance(stored_parameters, list):
        params = [str(p) for p in stored_parameters if p]

    executor_code = task_info.get("executor_code", "")
    extracted = extract_payload_keys(executor_code) if executor_code else []

    # Prefer code-based extraction when available; fallback to stored metadata.
    if extracted:
        params = extracted

    # Preserve order while removing duplicates
    seen = set()
    ordered_unique_params = []
    for p in params:
        if p not in seen:
            seen.add(p)
            ordered_unique_params.append(p)

    return ordered_unique_params, defaults


def summarize_payload(payload: Dict[str, Any], max_list_preview: int = 5) -> str:
    """Create a compact payload summary for logs."""
    compact = {}
    for key, value in payload.items():
        if isinstance(value, list):
            compact[key] = {
                "type": "list",
                "count": len(value),
                "preview": value[:max_list_preview]
            }
        else:
            compact[key] = value
    return json.dumps(compact, ensure_ascii=False)


def summarize_result(result: Dict[str, Any]) -> str:
    """Create short worker result summary for logs."""
    if not isinstance(result, dict):
        return str(result)

    if result.get("status") == "error":
        return f"error={result.get('message', 'unknown')}"

    keys = list(result.keys())
    key_info = f"keys={keys}"

    if "partial_sum" in result or "count" in result:
        return f"{key_info}, partial_sum={result.get('partial_sum')}, count={result.get('count')}"
    if "total_sum" in result or "total_numbers" in result:
        return f"{key_info}, total_sum={result.get('total_sum')}, total_numbers={result.get('total_numbers')}"

    return key_info


DEFAULT_AGGREGATOR_CODE = """def aggregator(results):
    return {"task": "custom", "results": results}
"""


# Best-effort node resource hints keyed by "ip:port" and by "ip".
# Populated from Module1 discovery when available.
NODE_RESOURCE_HINTS: Dict[str, Dict[str, Any]] = {}


def _parse_node_address(node: str) -> Optional[Tuple[str, int]]:
    try:
        host, port = node.split(":")
        return host.strip(), int(port)
    except Exception:
        return None


def _is_node_live(node: str, timeout: float = 0.8) -> bool:
    """Fast TCP liveness check for worker node address (ip:port)."""
    parsed = _parse_node_address(node)
    if not parsed:
        return False

    host, port = parsed
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _split_live_and_dead_nodes(nodes: List[str], timeout: float = 0.8) -> Tuple[List[str], List[str]]:
    """Split input nodes into currently live and dead lists."""
    live_nodes: List[str] = []
    dead_nodes: List[str] = []

    for node in nodes:
        if _is_node_live(node, timeout=timeout):
            live_nodes.append(node)
        else:
            dead_nodes.append(node)

    return live_nodes, dead_nodes


def _collect_node_metrics(nodes: List[str], timeout: float = 0.8) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Collect lightweight node metrics and map IP -> first matching node address."""
    active_nodes: Dict[str, Dict[str, Any]] = {}
    ip_to_node: Dict[str, str] = {}

    for node in nodes:
        parsed = _parse_node_address(node)
        if not parsed:
            continue
        host, port = parsed

        if host not in ip_to_node:
            ip_to_node[host] = node

        hints = NODE_RESOURCE_HINTS.get(node, {}) or NODE_RESOURCE_HINTS.get(host, {})

        latency_ms = 999.0
        try:
            started = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            latency_ms = (time.perf_counter() - started) * 1000 if result == 0 else 999.0
        except Exception:
            latency_ms = 999.0

        active_nodes[host] = {
            "latency_ms": latency_ms,
            "cpu_cores": hints.get("cpu_cores"),
            "cpu_freq_mhz": hints.get("cpu_freq_mhz"),
            "cpu_percent": hints.get("cpu_percent", 0.0),
            "ram_total_gb": hints.get("ram_total_gb"),
            "ram_available_gb": hints.get("ram_available_gb", 0.0),
            "worker_port": port,
        }

    return active_nodes, ip_to_node


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _compute_weighted_chunk_quotas(
    tasks: List[Dict[str, Any]],
    nodes: List[str],
    active_nodes: Dict[str, Dict[str, Any]],
    ip_to_node: Dict[str, str],
    failure_counts: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, int]]:
    """Compute per-node integer chunk quotas from CPU + RAM weighted capacity.

        Mathematical model:
            cpu_capacity_i = cores_i * freq_mhz_i * (1 - cpu_usage_i)
            mem_capacity_i = ram_available_gb_i
            net_quality_i = 1 / (1 + latency_ms_i / 100)
            cpu_norm_i = cpu_capacity_i / Σ cpu_capacity
            mem_norm_i = mem_capacity_i / Σ mem_capacity
            net_norm_i = net_quality_i / Σ net_quality
            base_weight_i = 0.55 * cpu_norm_i + 0.30 * mem_norm_i + 0.15 * net_norm_i
            reliability_penalty_i = exp(-0.7 * failure_count_i)
            weight_i = base_weight_i * reliability_penalty_i
      ideal_chunks_i = total_chunks * weight_i

    Integer quotas are obtained with Hamilton apportionment (floor + largest remainder),
    guaranteeing Σ quotas == total_chunks.
    """
    if not tasks or not nodes:
        return None

    total_chunks = len(tasks)
    failure_counts = failure_counts or {}

    # Build resource vectors only for nodes we can map back to an address.
    resource_rows: List[Tuple[str, float, float, float]] = []
    for ip, metrics in active_nodes.items():
        node_addr = ip_to_node.get(ip)
        if not node_addr:
            continue

        cores = max(1.0, _to_float(metrics.get("cpu_cores"), 1.0))
        freq_mhz = max(1000.0, _to_float(metrics.get("cpu_freq_mhz"), 1000.0))
        cpu_percent = min(100.0, max(0.0, _to_float(metrics.get("cpu_percent"), 40.0)))
        ram_available = max(0.25, _to_float(metrics.get("ram_available_gb"), 1.0))
        latency_ms = max(0.0, _to_float(metrics.get("latency_ms"), 999.0))

        cpu_capacity = max(0.001, cores * freq_mhz * (1.0 - (cpu_percent / 100.0)))
        mem_capacity = max(0.001, ram_available)
        net_quality = max(0.001, 1.0 / (1.0 + (latency_ms / 100.0)))
        resource_rows.append((node_addr, cpu_capacity, mem_capacity, net_quality))

    if not resource_rows:
        return None

    total_cpu = sum(cpu for _, cpu, _, _ in resource_rows)
    total_mem = sum(mem for _, _, mem, _ in resource_rows)
    total_net = sum(net for _, _, _, net in resource_rows)
    if total_cpu <= 0 or total_mem <= 0 or total_net <= 0:
        return None

    CPU_WEIGHT = 0.55
    MEM_WEIGHT = 0.30
    NET_WEIGHT = 0.15

    weighted: Dict[str, float] = {}
    for node_addr, cpu_capacity, mem_capacity, net_quality in resource_rows:
        cpu_norm = cpu_capacity / total_cpu
        mem_norm = mem_capacity / total_mem
        net_norm = net_quality / total_net

        base_weight = (CPU_WEIGHT * cpu_norm) + (MEM_WEIGHT * mem_norm) + (NET_WEIGHT * net_norm)
        fail_count = max(0, int(failure_counts.get(node_addr, 0)))
        reliability_penalty = math.exp(-0.7 * fail_count)
        weighted[node_addr] = base_weight * reliability_penalty

    total_weight = sum(weighted.values())
    if total_weight <= 0:
        return None

    # Hamilton method: floor first, then allocate by largest fractional remainder.
    quotas: Dict[str, int] = {}
    remainders: List[Tuple[float, str]] = []
    allocated = 0
    for node_addr in nodes:
        weight = weighted.get(node_addr, 0.0)
        ideal = (weight / total_weight) * total_chunks
        base = math.floor(ideal)
        quotas[node_addr] = base
        allocated += base
        remainders.append((ideal - base, node_addr))

    remaining = total_chunks - allocated
    if remaining > 0:
        remainders.sort(key=lambda x: x[0], reverse=True)
        for _, node_addr in remainders[:remaining]:
            quotas[node_addr] = quotas.get(node_addr, 0) + 1

    # If rounding produced edge anomalies, normalize with deterministic repair.
    quota_total = sum(quotas.values())
    if quota_total < total_chunks:
        for _, node_addr in sorted(remainders, key=lambda x: x[0], reverse=True):
            quotas[node_addr] = quotas.get(node_addr, 0) + 1
            quota_total += 1
            if quota_total == total_chunks:
                break
    elif quota_total > total_chunks:
        for _, node_addr in sorted(remainders, key=lambda x: x[0]):
            while quotas.get(node_addr, 0) > 0 and quota_total > total_chunks:
                quotas[node_addr] -= 1
                quota_total -= 1

    return quotas


def _order_nodes_with_module2(nodes: List[str], log_callback: Optional[Callable] = None) -> List[str]:
    """Order nodes using Module 2 distribution metrics (fallback to original order)."""
    if not nodes or DistributionService is None:
        return nodes

    try:
        service = DistributionService(
            scheduling_policy=SchedulingPolicy.LEAST_LOADED,
            balance_strategy=LoadBalanceStrategy.LATENCY_AWARE,
        )
        active_nodes, ip_to_node = _collect_node_metrics(nodes)
        service.active_nodes = active_nodes

        perfs = service.get_all_node_performance()
        scored: List[Tuple[float, str]] = []
        for perf in perfs:
            if not perf:
                continue
            ip = perf.get("ip")
            if ip and ip in ip_to_node:
                load_score = perf.get("load_score", 0.0)
                scored.append((load_score, ip_to_node[ip]))

        if not scored:
            return nodes

        scored.sort(key=lambda x: x[0])
        ordered = [node for _, node in scored]

        # Preserve any nodes missing in scored output.
        remaining = [n for n in nodes if n not in ordered]
        ordered.extend(remaining)

        if log_callback:
            log_callback(f"🧠 Module2 node order: {', '.join(ordered)}")
        return ordered
    except Exception as e:
        if log_callback:
            log_callback(f"⚠ Module2 ordering failed, fallback to default order: {e}")
        return nodes


def _assign_tasks_with_module2(
    tasks: List[Dict[str, Any]],
    nodes: List[str],
    log_callback: Optional[Callable] = None,
    failure_counts: Optional[Dict[str, int]] = None,
) -> List[Tuple[Dict[str, Any], str]]:
    """Assign chunk tasks to nodes using Module 2 DistributionService."""
    if not tasks or not nodes:
        return []

    if DistributionService is None or DistributionTask is None:
        return [(task, nodes[idx % len(nodes)]) for idx, task in enumerate(tasks)]

    try:
        service = DistributionService(
            scheduling_policy=SchedulingPolicy.LEAST_LOADED,
            balance_strategy=LoadBalanceStrategy.LATENCY_AWARE,
        )
        active_nodes, ip_to_node = _collect_node_metrics(nodes)
        service.active_nodes = active_nodes

        quotas = _compute_weighted_chunk_quotas(
            tasks,
            nodes,
            active_nodes,
            ip_to_node,
            failure_counts=failure_counts,
        )
        if quotas:
            if log_callback:
                quota_preview = ", ".join(f"{n}:{q}" for n, q in quotas.items() if q > 0)
                log_callback(f"📐 Weighted chunk quotas (CPU/RAM): {quota_preview}")

            ordered_nodes = sorted(nodes, key=lambda n: quotas.get(n, 0), reverse=True)
            scheduled_by_quota: List[Tuple[Dict[str, Any], str]] = []
            task_index = 0
            for node in ordered_nodes:
                quota = quotas.get(node, 0)
                for _ in range(quota):
                    if task_index >= len(tasks):
                        break
                    scheduled_by_quota.append((tasks[task_index], node))
                    task_index += 1

            if task_index < len(tasks):
                for idx in range(task_index, len(tasks)):
                    scheduled_by_quota.append((tasks[idx], nodes[idx % len(nodes)]))

            if scheduled_by_quota:
                return scheduled_by_quota

        distribution_tasks: List[Any] = []
        task_lookup: Dict[str, Dict[str, Any]] = {}

        for idx, task in enumerate(tasks):
            task_id = task.get("task_id", f"chunk-{idx + 1}")
            priority = 5
            payload = task.get("payload", {})
            if isinstance(payload, dict):
                try:
                    priority = int(payload.get("priority", 5))
                except Exception:
                    priority = 5

            distribution_tasks.append(
                DistributionTask(task_id=task_id, task_type="compute", priority=priority)
            )
            task_lookup[task_id] = task

        assignment = service.distribute_tasks(distribution_tasks)
        scheduled: List[Tuple[Dict[str, Any], str]] = []
        seen_ids = set()

        for ip, assigned in assignment.items():
            node_addr = ip_to_node.get(ip)
            if not node_addr:
                continue
            for assigned_task in assigned:
                source_task = task_lookup.get(assigned_task.task_id)
                if source_task is not None:
                    scheduled.append((source_task, node_addr))
                    seen_ids.add(assigned_task.task_id)

        # Fallback for any unassigned tasks.
        if len(scheduled) < len(tasks):
            remaining_tasks = [t for t in tasks if t.get("task_id") not in seen_ids]
            for idx, task in enumerate(remaining_tasks):
                scheduled.append((task, nodes[idx % len(nodes)]))

        if log_callback and scheduled:
            preview = [f"{t.get('task_id', 'unknown')}->{n}" for t, n in scheduled[:10]]
            log_callback(f"🧠 Module2 assignment: {', '.join(preview)}")

        return scheduled
    except Exception as e:
        if log_callback:
            log_callback(f"⚠ Module2 assignment failed, fallback to round-robin: {e}")
        return [(task, nodes[idx % len(nodes)]) for idx, task in enumerate(tasks)]


def count_attachment_files(payload: Dict[str, Any]) -> int:
    """Count dataset/file attachments in payload."""
    count = 0
    for key, value in payload.items():
        if "file" in key.lower() or "dataset" in key.lower():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, str) and value:
                count += len([v for v in value.split(",") if v])
    return count


def estimate_chunk_size(payload: Dict[str, Any], num_nodes: int) -> Optional[int]:
    """Estimate a chunk size when user doesn't provide one."""
    if num_nodes <= 0:
        return None

    # Range-based payload
    if "start" in payload and "end" in payload:
        try:
            start = int(payload.get("start"))
            end = int(payload.get("end"))
            total = abs(end - start) + 1
            return max(1, total // num_nodes)
        except Exception:
            pass

    # Generic list payloads
    for key, value in payload.items():
        if isinstance(value, list) and key.lower() != "chunk_size":
            total = len(value)
            if total > 0:
                return max(1, total // num_nodes)

    return None


def aggregate_custom_task_results(task_name: str, results: List[Dict], log_callback: Optional[Callable] = None) -> Dict:
    """Aggregate custom task results with a safety correction for chunked partial sums.

    If a custom aggregator returns `total_sum`/`total_numbers` that do not match
    the actual sum of chunk-level `partial_sum`/`count`, we auto-correct to avoid
    first-chunk-only totals.
    """
    final_result: Dict[str, Any]

    task_info = get_task_info(task_name)
    if task_info and task_info.get("aggregator"):
        try:
            final_result = task_info["aggregator"](results)
        except Exception as e:
            final_result = {"task": task_name, "results": results, "aggregation_error": str(e)}
    else:
        final_result = {"task": task_name, "results": results}

    # Safety correction for chunked numeric reductions.
    try:
        if not isinstance(final_result, dict):
            return {"task": task_name, "result": final_result}

        has_chunk_partials = bool(results) and all(
            isinstance(r, dict) and "partial_sum" in r and "count" in r for r in results
        )

        if has_chunk_partials and "total_sum" in final_result and "total_numbers" in final_result:
            expected_sum = sum(float(r.get("partial_sum", 0)) for r in results)
            expected_count = sum(int(r.get("count", 0)) for r in results)

            current_sum = float(final_result.get("total_sum", 0))
            current_count = int(final_result.get("total_numbers", 0))

            if abs(current_sum - expected_sum) > 1e-9 or current_count != expected_count:
                if log_callback:
                    log_callback(
                        "⚠ Custom aggregator totals mismatch detected. "
                        f"Using chunk totals instead (sum={expected_sum}, count={expected_count})."
                    )

                # Preserve int formatting for whole-number sums.
                final_result["total_sum"] = int(expected_sum) if expected_sum.is_integer() else expected_sum
                final_result["total_numbers"] = expected_count
    except Exception:
        # Never fail execution due to safety correction.
        pass

    return final_result


class DiscoveryWorker(threading.Thread):
    """Background worker for continuous node discovery."""
    
    def __init__(self, discovery_callback: Callable, update_interval: int = 10):
        super().__init__(daemon=True)
        self.discovery_callback = discovery_callback
        self.update_interval = update_interval
        self.is_running = False
        self.discovery_service = None
    
    def run(self):
        """Run continuous discovery."""
        self.is_running = True
        self.discovery_service = NodeDiscoveryService(
            discovery_callback=self.discovery_callback
        )
        self.discovery_service.start_discovery()
        
        while self.is_running:
            threading.Event().wait(self.update_interval)
    
    def stop(self):
        """Stop discovery."""
        self.is_running = False
        if self.discovery_service:
            self.discovery_service.stop_discovery()


class TaskExecutionWorker(threading.Thread):
    """Background worker for distributed task execution."""
    
    def __init__(self, task_name: str, payload: Dict, nodes: List[str], 
                 progress_callback: Callable, completion_callback: Callable, log_callback: Callable,
                 metrics_callback: Optional[Callable] = None):
        super().__init__(daemon=True)
        self.task_name = task_name
        self.payload = payload
        self.nodes = nodes
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.log_callback = log_callback
        self.metrics_callback = metrics_callback
        self.is_running = False

    def _emit_metrics_snapshot(self, worker_stats: Dict[str, Dict[str, Any]], completed: int, total: int, started_at: float):
        """Send live performance snapshot to GUI."""
        if not self.metrics_callback:
            return

        elapsed_s = max(0.001, time.perf_counter() - started_at)
        cluster_throughput = completed / elapsed_s
        remaining = max(0, total - completed)
        eta_cluster = (remaining / cluster_throughput) if cluster_throughput > 0 else None

        workers_payload: Dict[str, Dict[str, Any]] = {}
        for node, st in worker_stats.items():
            attempts = int(st.get("attempts", 0))
            successes = int(st.get("successes", 0))
            failures = int(st.get("failures", 0))
            retries = int(st.get("retries", 0))
            total_duration_ms = float(st.get("total_duration_ms", 0.0))
            throughput = successes / max(0.001, total_duration_ms / 1000.0)
            avg_latency = total_duration_ms / attempts if attempts > 0 else 0.0
            success_rate = (successes / attempts) * 100.0 if attempts > 0 else 0.0
            eta_worker = (remaining / throughput) if throughput > 0 else None

            workers_payload[node] = {
                "attempts": attempts,
                "successes": successes,
                "failures": failures,
                "retries": retries,
                "throughput": throughput,
                "avg_latency_ms": avg_latency,
                "success_rate": success_rate,
                "eta_s": eta_worker,
                "last_status": st.get("last_status", "idle"),
            }

        self.metrics_callback({
            "mode": "task",
            "task_name": self.task_name,
            "completed": completed,
            "total": total,
            "cluster_throughput": cluster_throughput,
            "cluster_eta_s": eta_cluster,
            "elapsed_s": elapsed_s,
            "workers": workers_payload,
        })

    def _execute_on_node(self, node: str, task_id: str) -> Dict[str, Any]:
        """Execute non-chunked task on one node and return execution metadata."""
        try:
            host, port = node.split(":")
            port = int(port)
        except Exception:
            return {
                "node": node,
                "task_id": task_id,
                "status": "error",
                "message": f"Invalid node address: {node}",
                "duration_ms": 0.0,
                "result": {"status": "error", "message": f"Invalid node address: {node}"},
            }

        task_data = {
            "task_id": task_id,
            "task_name": self.task_name,
            "payload": self.payload
        }

        started = time.perf_counter()
        result = MasterClient.send_task(host, port, task_data)
        duration_ms = (time.perf_counter() - started) * 1000
        status = "ok" if result.get("status") != "error" else "error"

        return {
            "node": node,
            "task_id": task_id,
            "status": status,
            "message": result.get("message", "") if status == "error" else "",
            "duration_ms": duration_ms,
            "result": result,
        }
    
    def run(self):
        """Execute task on all nodes and aggregate results."""
        self.is_running = True
        try:
            results = []
            errors = []
            run_started = time.perf_counter()
            execution_nodes = _order_nodes_with_module2(self.nodes, self.log_callback)
            execution_nodes, dead_nodes = _split_live_and_dead_nodes(execution_nodes, timeout=0.8)
            if dead_nodes:
                self.log_callback(f"⚠ Skipping offline workers before run: {', '.join(dead_nodes)}")
            if not execution_nodes:
                self.completion_callback(False, {"errors": ["No live workers available"]})
                return
            
            self.log_callback(f"🚀 Starting execution: {self.task_name}")
            self.log_callback(f"📡 Target workers ({len(execution_nodes)}): {', '.join(execution_nodes)}")
            self.log_callback(f"📦 Payload summary: {summarize_payload(self.payload)}")
            attachment_count = count_attachment_files(self.payload)
            if attachment_count:
                self.log_callback(f"📁 Attaching {attachment_count} file(s) to payload")

            dispatch_targets: List[Tuple[str, str]] = []
            for idx, node in enumerate(execution_nodes):
                task_id = f"{self.task_name}-{idx + 1}-{int(time.time() * 1000)}"
                dispatch_targets.append((node, task_id))
                self.log_callback(f"➡ Queue task_id={task_id} to {node}")

            worker_stats: Dict[str, Dict[str, Any]] = {
                node: {
                    "attempts": 0,
                    "successes": 0,
                    "failures": 0,
                    "retries": 0,
                    "total_duration_ms": 0.0,
                    "last_status": "queued",
                }
                for node, _ in dispatch_targets
            }

            completed = 0
            total_units = len(dispatch_targets)
            self._emit_metrics_snapshot(worker_stats, completed, total_units, run_started)
            with ThreadPoolExecutor(max_workers=max(1, len(dispatch_targets))) as pool:
                future_map = {
                    pool.submit(self._execute_on_node, node, task_id): (node, task_id)
                    for node, task_id in dispatch_targets
                }

                for future in as_completed(future_map):
                    if not self.is_running:
                        break

                    outcome = future.result()
                    node = outcome["node"]
                    task_id = outcome["task_id"]
                    duration_ms = outcome["duration_ms"]
                    node_stat = worker_stats.setdefault(node, {
                        "attempts": 0,
                        "successes": 0,
                        "failures": 0,
                        "retries": 0,
                        "total_duration_ms": 0.0,
                        "last_status": "queued",
                    })
                    node_stat["attempts"] += 1
                    node_stat["total_duration_ms"] += duration_ms

                    if outcome["status"] == "error":
                        node_stat["failures"] += 1
                        node_stat["retries"] += 1
                        node_stat["last_status"] = "error"
                        errors.append(f"{node}: {outcome.get('message', 'Unknown error')}")
                        self.log_callback(f"❌ {node} | task_id={task_id} | {duration_ms:.2f} ms | {outcome.get('message')}")
                    else:
                        result = outcome["result"]
                        node_stat["successes"] += 1
                        node_stat["last_status"] = "success"
                        results.append(result)
                        self.log_callback(
                            f"✅ {node} | task_id={task_id} | {duration_ms:.2f} ms | {summarize_result(result)}"
                        )

                    completed += 1
                    progress = completed / total_units
                    self.progress_callback(progress)
                    self._emit_metrics_snapshot(worker_stats, completed, total_units, run_started)
            
            # Aggregate results
            self.log_callback(f"🧮 Aggregating results: success={len(results)}, failed={len(errors)}")
            
            if results:
                if self.task_name == "range_sum":
                    final_result = aggregate_range_sum(results)
                elif self.task_name == "array_sum":
                    final_result = aggregate_array_sum(results)
                else:
                    final_result = aggregate_custom_task_results(self.task_name, results, self.log_callback)
                
                if errors:
                    final_result["errors"] = errors
                
                total_ms = (time.perf_counter() - run_started) * 1000
                self.log_callback(f"🎉 Execution completed in {total_ms:.2f} ms")
                self.log_callback(f"📊 Final result summary: {summarize_result(final_result)}")
                self.completion_callback(True, final_result)
            else:
                self.log_callback("✗ No successful results from any worker")
                self.completion_callback(False, {"errors": errors})
        
        except Exception as e:
            self.log_callback(f"✗ Execution error: {str(e)}")
            self.completion_callback(False, str(e))
    
    def stop(self):
        """Stop execution."""
        self.is_running = False


class ChunkedTaskExecutionWorker(threading.Thread):
    """Background worker for distributed task execution with chunking."""
    
    def __init__(self, task_name: str, tasks: List[Dict], nodes: List[str], 
                 progress_callback: Callable, completion_callback: Callable, log_callback: Callable,
                 metrics_callback: Optional[Callable] = None):
        super().__init__(daemon=True)
        self.task_name = task_name
        self.tasks = tasks  # List of chunked tasks
        self.nodes = nodes
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.log_callback = log_callback
        self.metrics_callback = metrics_callback
        self.is_running = False

    def _emit_metrics_snapshot(self, worker_stats: Dict[str, Dict[str, Any]], completed: int, total: int, started_at: float):
        """Send live performance snapshot to GUI for chunked execution."""
        if not self.metrics_callback:
            return

        elapsed_s = max(0.001, time.perf_counter() - started_at)
        cluster_throughput = completed / elapsed_s
        remaining = max(0, total - completed)
        eta_cluster = (remaining / cluster_throughput) if cluster_throughput > 0 else None

        workers_payload: Dict[str, Dict[str, Any]] = {}
        for node, st in worker_stats.items():
            attempts = int(st.get("attempts", 0))
            successes = int(st.get("successes", 0))
            failures = int(st.get("failures", 0))
            retries = int(st.get("retries", 0))
            total_duration_ms = float(st.get("total_duration_ms", 0.0))
            throughput = successes / max(0.001, total_duration_ms / 1000.0)
            avg_latency = total_duration_ms / attempts if attempts > 0 else 0.0
            success_rate = (successes / attempts) * 100.0 if attempts > 0 else 0.0
            eta_worker = (remaining / throughput) if throughput > 0 else None

            workers_payload[node] = {
                "attempts": attempts,
                "successes": successes,
                "failures": failures,
                "retries": retries,
                "throughput": throughput,
                "avg_latency_ms": avg_latency,
                "success_rate": success_rate,
                "eta_s": eta_worker,
                "last_status": st.get("last_status", "idle"),
            }

        self.metrics_callback({
            "mode": "chunked",
            "task_name": self.task_name,
            "completed": completed,
            "total": total,
            "cluster_throughput": cluster_throughput,
            "cluster_eta_s": eta_cluster,
            "elapsed_s": elapsed_s,
            "workers": workers_payload,
        })

    def _execute_chunk_on_node(self, task: Dict[str, Any], node: str) -> Dict[str, Any]:
        """Execute one chunk on one node and return metadata for master-side coordination."""
        task_name = task.get("task_name")
        payload = task.get("payload")
        task_id = task.get("task_id", f"{task_name}-chunk")

        try:
            host, port = node.split(":")
            port = int(port)
        except Exception:
            return {
                "task_id": task_id,
                "task": task,
                "node": node,
                "status": "error",
                "duration_ms": 0.0,
                "message": f"Invalid node address: {node}",
                "result": {"status": "error", "message": f"Invalid node address: {node}"},
            }

        task_data = {
            "task_id": task_id,
            "task_name": task_name,
            "payload": payload
        }

        started = time.perf_counter()
        result = MasterClient.send_task(host, port, task_data)
        duration_ms = (time.perf_counter() - started) * 1000

        return {
            "task_id": task_id,
            "task": task,
            "node": node,
            "status": "ok" if result.get("status") != "error" else "error",
            "duration_ms": duration_ms,
            "message": result.get("message", "") if result.get("status") == "error" else "",
            "result": result,
        }
    
    def run(self):
        """Execute chunked tasks on nodes and aggregate results."""
        self.is_running = True
        try:
            results = []
            errors = []
            run_started = time.perf_counter()
            total_chunks = len(self.tasks)
            failure_counts: Dict[str, int] = {}
            task_attempts: Dict[str, int] = {}
            completed_chunks = 0
            max_attempts = max(3, len(self.nodes) * 3)
            chunk_state: Dict[str, str] = {}
            worker_stats: Dict[str, Dict[str, Any]] = {
                node: {
                    "attempts": 0,
                    "successes": 0,
                    "failures": 0,
                    "retries": 0,
                    "total_duration_ms": 0.0,
                    "last_status": "idle",
                }
                for node in self.nodes
            }

            pending_tasks: List[Dict[str, Any]] = []
            for idx, task in enumerate(self.tasks):
                task_copy = dict(task)
                task_copy["task_id"] = task_copy.get("task_id", f"{self.task_name}-chunk-{idx + 1}")
                pending_tasks.append(task_copy)
                task_attempts[task_copy["task_id"]] = 0
                chunk_state[task_copy["task_id"]] = "pending"
            
            self.log_callback(f"🚀 Starting chunked execution: {self.task_name}")
            self.log_callback(f"🧩 Chunks: {len(self.tasks)} across {len(self.nodes)} node(s)")
            attachment_count = count_attachment_files(self.tasks[0].get("payload", {})) if self.tasks else 0
            if attachment_count:
                self.log_callback(f"📁 Attaching {attachment_count} file(s) per chunk")

            live_nodes, dead_nodes = _split_live_and_dead_nodes(self.nodes, timeout=0.8)
            if dead_nodes:
                self.log_callback(f"⚠ Offline before run: {', '.join(dead_nodes)}")

            if not live_nodes:
                self.log_callback("✗ No live worker nodes available")
                self.completion_callback(False, {"errors": ["No live workers available"]})
                return

            self._emit_metrics_snapshot(worker_stats, completed_chunks, total_chunks, run_started)

            while pending_tasks and self.is_running:
                # Continuously refresh live workers to catch runtime drop-offs.
                live_nodes, newly_dead = _split_live_and_dead_nodes(live_nodes, timeout=0.8)
                if newly_dead:
                    self.log_callback(f"⚠ Workers went offline: {', '.join(newly_dead)}")

                if not live_nodes:
                    errors.append(f"All workers went offline with {len(pending_tasks)} chunk(s) remaining")
                    break

                scheduled_chunks = _assign_tasks_with_module2(
                    pending_tasks,
                    live_nodes,
                    self.log_callback,
                    failure_counts=failure_counts,
                )
                if not scheduled_chunks:
                    errors.append("No schedulable chunks produced for remaining tasks")
                    break

                # Wave execution: at most one chunk per live worker, then rebalance again.
                wave: List[Tuple[Dict[str, Any], str]] = []
                used_nodes = set()
                for task, node in scheduled_chunks:
                    if node in used_nodes:
                        continue
                    wave.append((task, node))
                    used_nodes.add(node)
                    if len(wave) >= len(live_nodes):
                        break

                if not wave:
                    # Defensive fallback.
                    wave = [(pending_tasks[0], live_nodes[0])]

                for task, node in wave:
                    task_id = task.get("task_id", f"{self.task_name}-chunk")
                    chunk_state[task_id] = "running"
                    pending_label_index = (total_chunks - len(pending_tasks)) + 1
                    self.log_callback(
                        f"➡ Queue chunk {pending_label_index}/{total_chunks} | task_id={task_id} to {node} | payload={summarize_payload(task.get('payload'))}"
                    )

                with ThreadPoolExecutor(max_workers=max(1, len(wave))) as pool:
                    future_map = {
                        pool.submit(self._execute_chunk_on_node, task, node): (task, node)
                        for task, node in wave
                    }

                    for future in as_completed(future_map):
                        if not self.is_running:
                            break

                        outcome = future.result()
                        task = outcome["task"]
                        task_id = outcome["task_id"]
                        node = outcome["node"]
                        duration_ms = outcome["duration_ms"]
                        node_stat = worker_stats.setdefault(node, {
                            "attempts": 0,
                            "successes": 0,
                            "failures": 0,
                            "retries": 0,
                            "total_duration_ms": 0.0,
                            "last_status": "idle",
                        })
                        node_stat["attempts"] += 1
                        node_stat["total_duration_ms"] += duration_ms

                        if outcome["status"] == "error":
                            task_attempts[task_id] = task_attempts.get(task_id, 0) + 1
                            failure_counts[node] = failure_counts.get(node, 0) + 1
                            chunk_state[task_id] = "pending"
                            node_stat["failures"] += 1
                            node_stat["retries"] += 1
                            node_stat["last_status"] = "error"

                            self.log_callback(
                                f"❌ task_id={task_id} on {node} | {duration_ms:.2f} ms | attempt={task_attempts[task_id]} | {outcome.get('message')}"
                            )

                            if not _is_node_live(node, timeout=0.6):
                                self.log_callback(f"🔌 Worker marked offline during run: {node}")
                                live_nodes = [n for n in live_nodes if n != node]

                            if task_attempts[task_id] >= max_attempts:
                                errors.append(
                                    f"{task_id} failed after {task_attempts[task_id]} attempts: {outcome.get('message', 'Unknown error')}"
                                )
                                chunk_state[task_id] = "failed"
                                pending_tasks = [t for t in pending_tasks if t.get("task_id") != task_id]
                                completed_chunks += 1
                        else:
                            result = outcome["result"]
                            results.append(result)
                            chunk_state[task_id] = "success"
                            node_stat["successes"] += 1
                            node_stat["last_status"] = "success"
                            self.log_callback(
                                f"✅ task_id={task_id} on {node} | {duration_ms:.2f} ms | {summarize_result(result)}"
                            )
                            pending_tasks = [t for t in pending_tasks if t.get("task_id") != task_id]
                            completed_chunks += 1

                        progress = (completed_chunks / total_chunks) if total_chunks else 1.0
                        self.progress_callback(progress)
                        self._emit_metrics_snapshot(worker_stats, completed_chunks, total_chunks, run_started)

                # State snapshot for master-side coordination visibility.
                state_counts: Dict[str, int] = {"pending": 0, "running": 0, "success": 0, "failed": 0}
                for state in chunk_state.values():
                    if state in state_counts:
                        state_counts[state] += 1
                self.log_callback(
                    "📈 Chunk states | "
                    f"pending={state_counts['pending']} running={state_counts['running']} "
                    f"success={state_counts['success']} failed={state_counts['failed']}"
                )
            
            # Aggregate results
            self.log_callback(f"🧮 Aggregating chunk results: success={len(results)}, failed={len(errors)}")
            
            if results:
                if self.task_name == "range_sum":
                    final_result = aggregate_range_sum(results)
                elif self.task_name == "array_sum":
                    final_result = aggregate_array_sum(results)
                else:
                    final_result = aggregate_custom_task_results(self.task_name, results, self.log_callback)
                
                if errors:
                    final_result["errors"] = errors
                
                total_ms = (time.perf_counter() - run_started) * 1000
                self.log_callback(f"🎉 Chunked execution completed in {total_ms:.2f} ms")
                self.log_callback(f"📊 Final result summary: {summarize_result(final_result)}")
                self.completion_callback(True, final_result)
            else:
                self.log_callback("✗ No successful results from any chunk")
                self.completion_callback(False, {"errors": errors})
        
        except Exception as e:
            self.log_callback(f"✗ Execution error: {str(e)}")
            self.completion_callback(False, str(e))
    
    def stop(self):
        """Stop execution."""
        self.is_running = False


class CustomTaskDialog(tk.Toplevel):
    """Dialog for creating custom tasks with automatic parameter extraction."""
    
    def __init__(self, parent, worker_nodes_callback=None):
        super().__init__(parent)
        self.title("Create Custom Task")
        self.geometry("900x800")
        self.task_result = None
        self.attached_files = []
        self.worker_nodes_callback = worker_nodes_callback  # Callback to get current worker nodes
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Task Name
        tk.Label(self, text="Task Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.task_name_var = tk.StringVar()
        tk.Entry(self, textvariable=self.task_name_var, width=40).grid(row=0, column=1, columnspan=2, padx=10, pady=10)
        
        # Description
        tk.Label(self, text="Description:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.desc_var = tk.StringVar()
        tk.Entry(self, textvariable=self.desc_var, width=40).grid(row=1, column=1, columnspan=2, padx=10, pady=10)
        
        # Executor Code Section
        tk.Label(self, text="Executor Code (Python):", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="nw", padx=10, pady=10)
        self.executor_text = scrolledtext.ScrolledText(self, height=10, width=80)
        self.executor_text.grid(row=2, column=1, columnspan=2, padx=10, pady=10)
        # BIND to detect changes in real-time
        self.executor_text.bind("<KeyRelease>", self._on_executor_change)
        
        self.executor_text.insert("1.0", """def executor(payload, progress_cb):
    # Access parameters from payload: payload.get("param_name")
    # Example: value = payload.get("param_name", default_value)
    
    result = {"status": "success", "data": "your result"}
    progress_cb(1.0)
    return result""")
        
        # Aggregator Code Section
        tk.Label(self, text="Aggregator Code (Python):", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="nw", padx=10, pady=10)
        self.aggregator_text = scrolledtext.ScrolledText(self, height=8, width=80)
        self.aggregator_text.grid(row=3, column=1, columnspan=2, padx=10, pady=10)
        
        self.aggregator_text.insert("1.0", """def aggregator(results):
    return {"task": "custom", "total": len(results)}""")
        
        # DYNAMIC Parameters Section - Shows detected parameters in real-time
        tk.Label(self, text="Detected Parameters:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="nw", padx=10, pady=10)
        
        # Frame to hold detected parameters
        self.params_frame = tk.Frame(self, bg="#f5f5f5", relief="solid", borderwidth=1)
        self.params_frame.grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=10, ipady=8)
        
        # Label to show parameters
        self.params_label = tk.Label(self.params_frame, 
                                     text="(Parameters will auto-detect from executor code)", 
                                     font=("Arial", 9), 
                                     fg="#666666",
                                     bg="#f5f5f5",
                                     wraplength=400,
                                     justify="left")
        self.params_label.pack(anchor="w", padx=5, pady=5)

        # Dataset attachment section
        tk.Label(self, text="Attach Dataset Files:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="nw", padx=10, pady=10)

        attach_frame = tk.Frame(self)
        attach_frame.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=10)

        self.attach_label = tk.Label(
            attach_frame,
            text="(No files attached)",
            fg="#666666",
            wraplength=400,
            justify="left"
        )
        self.attach_label.pack(side="left", padx=5)

        tk.Button(
            attach_frame,
            text="Browse",
            command=self._attach_dataset_files,
            bg="#607D8B",
            fg="white",
            width=10
        ).pack(side="left", padx=10)
        
        # Buttons
        button_frame_bottom = tk.Frame(self)
        button_frame_bottom.grid(row=6, column=0, columnspan=4, pady=20)
        
        tk.Button(button_frame_bottom, text="Register Task", command=self._register_task, 
                 bg="#2196F3", fg="white", width=15, font=("Arial", 10)).pack(side="left", padx=10)
        
        # NEW: Distribute button
        tk.Button(button_frame_bottom, text="Register & Distribute to Workers", 
                 command=self._register_and_distribute, 
                 bg="#4CAF50", fg="white", width=25, font=("Arial", 10)).pack(side="left", padx=10)
        
        tk.Button(button_frame_bottom, text="Cancel", command=self.destroy, 
                 bg="#757575", fg="white", width=15, font=("Arial", 10)).pack(side="left", padx=10)
    
    def _on_executor_change(self, event=None):
        """Auto-extract parameters when executor code changes - REAL-TIME."""
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        
        # Extract parameters in real-time
        params = extract_payload_keys(executor_code)
        
        # Update the detected parameters display DYNAMICALLY
        if params:
            # Show parameters in blue with nice formatting
            param_text = f"✓ Parameters Detected: {', '.join(params)}"
            self.params_label.config(text=param_text, fg="#2196F3", font=("Arial", 9, "bold"))
        else:
            # No parameters found
            self.params_label.config(text="(No parameters detected in code)", 
                                    fg="#999999", 
                                    font=("Arial", 9))

    def _attach_dataset_files(self):
        """Attach dataset files for the custom task."""
        file_paths = filedialog.askopenfilenames(title="Select dataset files")
        if file_paths:
            self.attached_files = list(file_paths)
            short_list = [Path(p).name for p in self.attached_files]
            self.attach_label.config(
                text=f"Attached ({len(short_list)}): {', '.join(short_list)}",
                fg="#2196F3"
            )
    
    def _register_task(self):
        """Register custom task locally (master only)."""
        task_name = self.task_name_var.get().strip()
        description = self.desc_var.get().strip()
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        aggregator_code = self.aggregator_text.get("1.0", tk.END).strip() or DEFAULT_AGGREGATOR_CODE
        
        if not all([task_name, executor_code]):
            messagebox.showerror("Validation Error", "Task name and executor code are required!")
            return
        
        try:
            # Validate executor code
            namespace = {}
            exec(executor_code, namespace)
            executor_func = namespace.get("executor")
            
            # Validate aggregator code
            namespace = {}
            exec(aggregator_code, namespace)
            aggregator_func = namespace.get("aggregator")
            
            if not executor_func or not aggregator_func:
                messagebox.showerror("Code Error", "Functions must be defined!")
                return
            
            # AUTO-EXTRACT PARAMETERS
            params = extract_payload_keys(executor_code)

            # Persist attached dataset files as default parameter (if provided)
            params_meta: Any = params
            if self.attached_files:
                params_meta = {"dataset_files": self.attached_files}
            
            # Register in master's memory
            register_custom_task(
                task_name=task_name,
                executor=executor_func,
                aggregator=aggregator_func,
                description=description or f"Custom task: {task_name}"
            )
            
            # Save to shared registry
            save_custom_task(task_name, executor_code, aggregator_code, description, params_meta)
            
            param_msg = f"\n\nDetected parameters: {', '.join(params) if params else 'None'}"
            messagebox.showinfo("Success", f"Task '{task_name}' registered locally!{param_msg}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Registration Error", f"Failed:\n{str(e)}")
    
    def _register_and_distribute(self):
        """Register task and distribute to all worker nodes."""
        task_name = self.task_name_var.get().strip()
        description = self.desc_var.get().strip()
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        aggregator_code = self.aggregator_text.get("1.0", tk.END).strip() or DEFAULT_AGGREGATOR_CODE
        
        if not all([task_name, executor_code]):
            messagebox.showerror("Validation Error", "Task name and executor code are required!")
            return
        
        try:
            # Validate executor code
            namespace = {}
            exec(executor_code, namespace)
            executor_func = namespace.get("executor")
            
            # Validate aggregator code
            namespace = {}
            exec(aggregator_code, namespace)
            aggregator_func = namespace.get("aggregator")
            
            if not executor_func or not aggregator_func:
                messagebox.showerror("Code Error", "Functions must be defined!")
                return
            
            # AUTO-EXTRACT PARAMETERS
            params = extract_payload_keys(executor_code)

            params_meta: Any = params
            if self.attached_files:
                params_meta = {"dataset_files": self.attached_files}
            
            # Register in master's memory
            register_custom_task(
                task_name=task_name,
                executor=executor_func,
                aggregator=aggregator_func,
                description=description or f"Custom task: {task_name}"
            )
            
            # Save to shared registry
            save_custom_task(task_name, executor_code, aggregator_code, description, params_meta)
            
            # Get worker nodes from callback
            if not self.worker_nodes_callback:
                messagebox.showerror("Error", "No worker nodes available")
                return
            
            worker_nodes = self.worker_nodes_callback()
            if not worker_nodes:
                messagebox.showerror("Error", "No worker nodes configured")
                return
            
            # Distribute to workers
            results = distribute_task_to_workers(
                task_name, executor_code, aggregator_code, description, params_meta, worker_nodes
            )
            
            # Show distribution results
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            result_msg = f"\nTask distributed to {success_count}/{total_count} workers:\n\n"
            for node, success in results.items():
                status = "✓" if success else "✗"
                result_msg += f"{status} {node}\n"
            
            param_msg = f"\n\nDetected parameters: {', '.join(params) if params else 'None'}"
            
            if success_count == total_count:
                messagebox.showinfo("Success", f"Task '{task_name}' registered and distributed!{result_msg}{param_msg}")
            else:
                messagebox.showwarning("Partial Success", f"Task registered on master.\nDistributed to {success_count}/{total_count} workers.{result_msg}{param_msg}")
            
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed:\n{str(e)}")


class EditCustomTaskDialog(tk.Toplevel):
    """Dialog for editing existing custom tasks with parameter detection."""
    
    def __init__(self, parent, task_name: str, task_data: Dict):
        super().__init__(parent)
        self.title(f"Edit Custom Task: {task_name}")
        self.geometry("900x750")
        self.task_name = task_name
        self.task_data = task_data
        self.task_result = None
        self.attached_files = []
        
        self._create_widgets()
        self._populate_fields()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Task Name (read-only)
        tk.Label(self, text="Task Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.task_name_var = tk.StringVar(value=self.task_name)
        task_name_entry = tk.Entry(self, textvariable=self.task_name_var, width=40, state="readonly")
        task_name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=10)
        tk.Label(self, text="(Read-only)", font=("Arial", 8, "italic"), fg="gray").grid(row=0, column=3, sticky="w", padx=5)
        
        # Description
        tk.Label(self, text="Description:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.desc_var = tk.StringVar()
        tk.Entry(self, textvariable=self.desc_var, width=40).grid(row=1, column=1, columnspan=2, padx=10, pady=10)
        
        # Executor Code
        tk.Label(self, text="Executor Code (Python):", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="nw", padx=10, pady=10)
        self.executor_text = scrolledtext.ScrolledText(self, height=10, width=80)
        self.executor_text.grid(row=2, column=1, columnspan=2, padx=10, pady=10)
        # BIND to detect changes in real-time
        self.executor_text.bind("<KeyRelease>", self._on_executor_change)
        
        # Aggregator Code
        tk.Label(self, text="Aggregator Code (Python):", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="nw", padx=10, pady=10)
        self.aggregator_text = scrolledtext.ScrolledText(self, height=8, width=80)
        self.aggregator_text.grid(row=3, column=1, columnspan=2, padx=10, pady=10)
        
        # DYNAMIC Parameters Section - Real-time detection while editing
        tk.Label(self, text="Detected Parameters:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="nw", padx=10, pady=10)
        
        # Frame to hold detected parameters
        self.params_frame = tk.Frame(self, bg="#f5f5f5", relief="solid", borderwidth=1)
        self.params_frame.grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=10, ipady=8)
        
        # Label to show parameters
        self.params_label = tk.Label(self.params_frame, 
                                     text="(Parameters will auto-detect from executor code)", 
                                     font=("Arial", 9), 
                                     fg="#666666",
                                     bg="#f5f5f5",
                                     wraplength=400,
                                     justify="left")
        self.params_label.pack(anchor="w", padx=5, pady=5)

        # Dataset attachment section
        tk.Label(self, text="Attach Dataset Files:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky="nw", padx=10, pady=10)

        attach_frame = tk.Frame(self)
        attach_frame.grid(row=5, column=1, columnspan=2, sticky="ew", padx=10, pady=10)

        self.attach_label = tk.Label(
            attach_frame,
            text="(No files attached)",
            fg="#666666",
            wraplength=400,
            justify="left"
        )
        self.attach_label.pack(side="left", padx=5)

        tk.Button(
            attach_frame,
            text="Browse",
            command=self._attach_dataset_files,
            bg="#607D8B",
            fg="white",
            width=10
        ).pack(side="left", padx=10)
        
        # Buttons
        button_frame_bottom = tk.Frame(self)
        button_frame_bottom.grid(row=6, column=0, columnspan=4, pady=20)
        
        tk.Button(button_frame_bottom, text="Save Changes", command=self._save_changes, 
                 bg="#2196F3", fg="white", width=15, font=("Arial", 10)).pack(side="left", padx=10)
        tk.Button(button_frame_bottom, text="Cancel", command=self.destroy, 
                 bg="#757575", fg="white", width=15, font=("Arial", 10)).pack(side="left", padx=10)
    
    def _populate_fields(self):
        """Populate fields with existing task data."""
        self.desc_var.set(self.task_data.get("description", ""))
        self.executor_text.insert("1.0", self.task_data.get("executor_code", ""))
        self.aggregator_text.insert("1.0", self.task_data.get("aggregator_code", ""))
        parameters = self.task_data.get("parameters", {})
        if isinstance(parameters, dict) and parameters.get("dataset_files"):
            self.attached_files = parameters.get("dataset_files", [])
            short_list = [Path(p).name for p in self.attached_files]
            self.attach_label.config(
                text=f"Attached ({len(short_list)}): {', '.join(short_list)}",
                fg="#2196F3"
            )
        # Trigger initial detection
        self._on_executor_change()
    
    def _on_executor_change(self, event=None):
        """Auto-extract parameters when executor code changes - REAL-TIME."""
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        params = extract_payload_keys(executor_code)
        
        # Update the detected parameters display DYNAMICALLY
        if params:
            # Show parameters in blue with nice formatting
            param_text = f"✓ Parameters Detected: {', '.join(params)}"
            self.params_label.config(text=param_text, fg="#2196F3", font=("Arial", 9, "bold"))
        else:
            # No parameters found
            self.params_label.config(text="(No parameters detected in code)", 
                                    fg="#999999", 
                                    font=("Arial", 9))

    def _attach_dataset_files(self):
        """Attach dataset files for the custom task."""
        file_paths = filedialog.askopenfilenames(title="Select dataset files")
        if file_paths:
            self.attached_files = list(file_paths)
            short_list = [Path(p).name for p in self.attached_files]
            self.attach_label.config(
                text=f"Attached ({len(short_list)}): {', '.join(short_list)}",
                fg="#2196F3"
            )
    
    def _save_changes(self):
        """Save changes to the custom task with auto-detected parameters."""
        description = self.desc_var.get().strip()
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        aggregator_code = self.aggregator_text.get("1.0", tk.END).strip() or DEFAULT_AGGREGATOR_CODE
        
        if not executor_code:
            messagebox.showerror("Validation Error", "Executor code is required!")
            return
        
        try:
            # Validate executor code
            namespace = {}
            exec(executor_code, namespace)
            executor_func = namespace.get("executor")
            
            # Validate aggregator code
            namespace = {}
            exec(aggregator_code, namespace)
            aggregator_func = namespace.get("aggregator")
            
            if not executor_func or not aggregator_func:
                messagebox.showerror("Code Error", "Functions must be defined!")
                return
            
            # AUTO-EXTRACT PARAMETERS
            params = extract_payload_keys(executor_code)
            params_meta: Any = params
            if self.attached_files:
                params_meta = {"dataset_files": self.attached_files}
            
            # Update in memory registry
            from module3_execution.tasks import _custom_registry
            
            _custom_registry._tasks[self.task_name] = {
                "executor": executor_func,
                "aggregator": aggregator_func,
                "description": description or f"Custom task: {self.task_name}"
            }
            
            # Update in file registry with AUTO-DETECTED parameters
            save_custom_task(self.task_name, executor_code, aggregator_code, description, params_meta)
            
            # Show success with detected parameters
            param_msg = f"\n\nNew parameters: {', '.join(params) if params else 'None'}"
            messagebox.showinfo("Success", f"Task '{self.task_name}' updated!{param_msg}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed:\n{str(e)}")


class MasterGUI:
    """Master mode GUI for task distribution."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Computing - Master")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f0f0f0")
        
        # Discovery setup
        self.discovery_worker = None
        self.discovered_nodes = {}
        
        self.current_task = None
        self.current_worker = None
        self.execution_results = None
        self.logs_text = None
        self.param_entries = {}
        self.auto_configure_btn = None
        self._auto_configure_running = False
        self.performance_tree = None
        self.performance_summary_var = None
        self.performance_task_var = None
        self._performance_stats: Dict[str, Any] = {}
        
        self._create_widgets()
        self._start_discovery()
    
    def _start_discovery(self):
        """Start background node discovery."""
        self.discovery_worker = DiscoveryWorker(
            discovery_callback=self._on_node_discovered,
            update_interval=10
        )
        self.discovery_worker.start()
        self._log("🔍 Auto-discovery service started...")
    
    def _on_node_discovered(self, node_addr: str, state: str):
        """Handle node discovery."""
        if state == "discovered":
            self._log(f"Worker discovered: {node_addr}")
            if node_addr not in self.nodes_listbox.get(0, tk.END):
                self.nodes_listbox.insert(tk.END, node_addr)
                self.discovered_nodes[node_addr] = True
    
    def _create_widgets(self):
        """Create main GUI widgets."""
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")
        
        tk.Label(header, text="Master Node - Distributed Computing System", 
                font=("Arial", 18, "bold"), fg="white", bg="#2c3e50").pack(pady=15)
        
        # Main container
        main_container = ttk.PanedWindow(self.root, orient="horizontal")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel
        left_panel = tk.Frame(self.root, bg="white")
        main_container.add(left_panel, weight=1)
        
        # Right panel - Create FIRST to initialize logs_text
        right_panel = tk.Frame(self.root, bg="white")
        main_container.add(right_panel, weight=2)
        self._create_right_panel(right_panel)
        
        # Now create left panel after logs_text exists
        self._create_left_panel(left_panel)
    
    def _create_left_panel(self, parent):
        """Create left panel with tasks and discovery."""
        tk.Label(parent, text="Auto-Discovery", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=5)
        
        discovery_frame = tk.LabelFrame(parent, text="Discovery Status", bg="white")
        discovery_frame.pack(padx=10, pady=5, fill="x")
        
        self.discovery_status_label = tk.Label(discovery_frame, text="🔍 Scanning...", bg="white", fg="#2196F3")
        self.discovery_status_label.pack(padx=10, pady=5)

        # Auto-configure button (Module1 discovery)
        self.auto_configure_btn = tk.Button(
            parent,
            text="Auto Configure Nodes",
            command=self._auto_configure_nodes,
            bg="#3F51B5",
            fg="white",
            width=22,
            font=("Arial", 9, "bold")
        )
        self.auto_configure_btn.pack(padx=10, pady=5, fill="x")
        
        tk.Label(parent, text="Available Tasks", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=5)
        
        self.task_listbox = tk.Listbox(parent, height=10, width=30, bg="white")
        self.task_listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.task_listbox.bind("<<ListboxSelect>>", self._on_task_select)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.task_listbox.yview)
        scrollbar.pack(side="right", fill="y", pady=5)
        self.task_listbox.config(yscrollcommand=scrollbar.set)
        
        # Compact button grid layout (2 columns, 3 rows)
        button_frame = tk.Frame(parent, bg="white")
        button_frame.pack(padx=10, pady=5, fill="x")
        
        # Row 1: Create & Edit buttons
        tk.Button(button_frame, text="Create Task", command=self._open_custom_task_dialog,
                 bg="#4CAF50", fg="white", width=12, font=("Arial", 9)).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        tk.Button(button_frame, text="Edit Task", command=self._open_edit_task_dialog,
                 bg="#FF9800", fg="white", width=12, font=("Arial", 9)).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        # Row 2: Delete & Refresh buttons
        tk.Button(button_frame, text="Delete Task", command=self._delete_task,
                 bg="#f44336", fg="white", width=12, font=("Arial", 9)).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        
        tk.Button(button_frame, text="Refresh", command=self._update_task_list,
                 bg="#2196F3", fg="white", width=12, font=("Arial", 9)).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        
        # Configure grid columns to be equal width
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        self._update_task_list()
    
    def _create_right_panel(self, parent):
        """Create right panel with configuration and execution."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configuration tab
        config_frame = tk.Frame(notebook, bg="white")
        notebook.add(config_frame, text="Configuration")
        self._create_config_tab(config_frame)
        
        # Nodes tab
        node_frame = tk.Frame(notebook, bg="white")
        notebook.add(node_frame, text="Worker Nodes")
        self._create_nodes_tab(node_frame)
        
        # Execution tab
        exec_frame = tk.Frame(notebook, bg="white")
        notebook.add(exec_frame, text="Execution")
        self._create_execution_tab(exec_frame)
        
        # Logs tab
        log_frame = tk.Frame(notebook, bg="white")
        notebook.add(log_frame, text="Logs")
        self._create_logs_tab(log_frame)
    
    def _create_config_tab(self, parent):
        """Create configuration tab with dynamic parameter fields."""
        tk.Label(parent, text="Task Configuration", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        self.config_text = scrolledtext.ScrolledText(parent, height=6, width=80, bg="#f5f5f5")
        self.config_text.pack(padx=10, pady=10, fill="both")
        
        # Main parameter frame for dynamic parameters
        self.param_frame_wrapper = tk.LabelFrame(parent, text="Task Parameters (Auto-generated from code)", 
                                                font=("Arial", 10, "bold"), bg="white", padx=10, pady=10)
        self.param_frame_wrapper.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Initialize placeholder
        self.param_placeholder = tk.Label(self.param_frame_wrapper, text="(Select a task to see parameters)", 
                                         bg="white", fg="#999999")
        self.param_placeholder.pack()
        
        self.param_entries = {}
    

    def _create_nodes_tab(self, parent):
        """Create worker nodes configuration tab."""
        tk.Label(parent, text="Connected Worker Nodes", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        input_frame = tk.LabelFrame(parent, text="Add Node Manually", font=("Arial", 10, "bold"), bg="white")
        input_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Label(input_frame, text="Node Address (IP:Port):", bg="white").pack(side="left", padx=5, pady=5)
        self.node_input_var = tk.StringVar(value="127.0.0.1:6000")
        tk.Entry(input_frame, textvariable=self.node_input_var, width=30).pack(side="left", padx=5)
        tk.Button(input_frame, text="Add", command=self._add_node, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        
        list_frame = tk.LabelFrame(parent, text="Auto-Discovered & Manual Nodes", font=("Arial", 10, "bold"), bg="white")
        list_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.nodes_listbox = tk.Listbox(list_frame, height=10, width=50, bg="white")
        self.nodes_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        button_frame = tk.Frame(list_frame, bg="white")
        button_frame.pack(padx=10, pady=5, fill="x")
        
        tk.Button(button_frame, text="Test Connection", command=self._test_node_connection,
                 bg="#2196F3", fg="white", width=20).pack(side="left", padx=5)
        tk.Button(button_frame, text="Remove Selected", command=self._remove_node, 
                 bg="#f44336", fg="white", width=20).pack(side="left", padx=5)
    
    def _create_execution_tab(self, parent):
        """Create execution tab."""
        progress_frame = tk.Frame(parent, bg="white")
        progress_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Label(progress_frame, text="Execution Progress:", bg="white").pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        
        self.progress_label = tk.Label(progress_frame, text="0%", bg="white", width=5)
        self.progress_label.pack(side="left", padx=5)
        
        button_frame = tk.Frame(parent, bg="white")
        button_frame.pack(padx=10, pady=10, fill="x")
        
        self.execute_btn = tk.Button(button_frame, text="Execute Task", command=self._execute_task,
                                     bg="#2196F3", fg="white", width=20, font=("Arial", 11, "bold"))
        self.execute_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(button_frame, text="Stop", command=self._stop_execution,
                                  bg="#f44336", fg="white", width=20, font=("Arial", 11, "bold"), state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Export Results", command=self._export_results,
                 bg="#FF9800", fg="white", width=20).pack(side="left", padx=5)

        perf_frame = tk.LabelFrame(parent, text="Live Performance Panel", bg="white", font=("Arial", 10, "bold"))
        perf_frame.pack(padx=10, pady=6, fill="x")

        self.performance_task_var = tk.StringVar(value="Task: -")
        tk.Label(perf_frame, textvariable=self.performance_task_var, bg="white", fg="#2c3e50", font=("Arial", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        self.performance_summary_var = tk.StringVar(value="Throughput: 0.00 chunk/s | ETA: - | Speedup est: -")
        tk.Label(perf_frame, textvariable=self.performance_summary_var, bg="white", fg="#1b5e20", font=("Arial", 9)).pack(anchor="w", padx=8, pady=(0, 6))

        columns = ("worker", "throughput", "retries", "success_rate", "eta", "completed", "failed", "avg_latency", "state")
        self.performance_tree = ttk.Treeview(perf_frame, columns=columns, show="headings", height=6)
        self.performance_tree.heading("worker", text="Worker")
        self.performance_tree.heading("throughput", text="Throughput(ch/s)")
        self.performance_tree.heading("retries", text="Retries")
        self.performance_tree.heading("success_rate", text="Success %")
        self.performance_tree.heading("eta", text="ETA(s)")
        self.performance_tree.heading("completed", text="Completed")
        self.performance_tree.heading("failed", text="Failed")
        self.performance_tree.heading("avg_latency", text="Avg Lat(ms)")
        self.performance_tree.heading("state", text="State")

        self.performance_tree.column("worker", width=160, anchor="w")
        self.performance_tree.column("throughput", width=120, anchor="center")
        self.performance_tree.column("retries", width=70, anchor="center")
        self.performance_tree.column("success_rate", width=90, anchor="center")
        self.performance_tree.column("eta", width=80, anchor="center")
        self.performance_tree.column("completed", width=85, anchor="center")
        self.performance_tree.column("failed", width=70, anchor="center")
        self.performance_tree.column("avg_latency", width=95, anchor="center")
        self.performance_tree.column("state", width=80, anchor="center")
        self.performance_tree.pack(fill="x", padx=8, pady=(0, 8))

        self._reset_performance_panel()
        
        tk.Label(parent, text="Results:", font=("Arial", 10, "bold"), bg="white").pack(padx=10, pady=(10, 5), anchor="w")
        
        self.results_text = scrolledtext.ScrolledText(parent, height=15, width=100, bg="#f5f5f5")
        self.results_text.pack(padx=10, pady=10, fill="both", expand=True)

    def _auto_configure_nodes(self):
        """Auto-configure worker nodes using Module1 discovery logic."""
        if self._auto_configure_running:
            self._log("⚠ Auto configure already running...")
            return

        self._auto_configure_running = True
        if self.auto_configure_btn:
            self.auto_configure_btn.config(state="disabled")

        self._log("🚀 Auto configure nodes started (Module1 discovery)")

        thread = threading.Thread(target=self._run_auto_configure, daemon=True)
        thread.start()

    def _run_auto_configure(self):
        """Run discovery service once and populate worker nodes list."""
        original_print = builtins.print

        def _log_print(*args, **kwargs):
            message = " ".join(str(a) for a in args)
            if message:
                self._log(message)

        try:
            builtins.print = _log_print

            # Mimic module1_discovery.main behavior with GUI logs
            self._log("\n" + "=" * 70)
            self._log(" WiFi Distributed Computing - Module 1: Node Discovery")
            self._log("=" * 70 + "\n")

            collector = NodeInfoCollector()
            info = collector.collect_all_info()

            self._log("Local Node Information:")
            self._log("-" * 70)
            self._log(f"Hostname:      {info.hostname}")
            self._log(f"IP Address:    {info.ip_address}")
            self._log(f"MAC Address:   {info.mac_address}")
            self._log(f"OS:            {info.os_info}")
            self._log(f"CPU:           {info.cpu_cores} cores @ {info.cpu_freq_mhz:.0f} MHz (Usage: {info.cpu_percent:.1f}%)")
            self._log(f"RAM:           {info.ram_available_gb:.2f} GB / {info.ram_total_gb:.2f} GB available")
            self._log(f"Storage:       {info.storage_available_gb:.2f} GB / {info.storage_total_gb:.2f} GB available")
            if info.network_bandwidth_mbps:
                self._log(f"Network:       {info.network_bandwidth_mbps:.0f} Mbps")
            else:
                self._log("Network:       Bandwidth unknown")
            self._log("-" * 70 + "\n")

            service = Module1DiscoveryService(scan_interval=10)
            service.start()
            self._log("   Methods: ARP cache, arp-scan, nmap, ICMP ping sweep")
            self._log("   Auto-config scan running...\n")

            # Allow one scan cycle plus brief buffer
            time.sleep(12)

            service.stop()
            service.print_all_nodes()

            discovered = service.get_discovered_nodes()
            added_count = 0

            if not discovered:
                self._log("ℹ️  No live workers discovered.")
            else:
                for ip, node_data in discovered.items():
                    if ip == info.ip_address:
                        continue

                    worker_port = node_data.get("worker_port")
                    open_ports = node_data.get("open_ports", []) or []

                    port_candidates = []
                    if worker_port:
                        port_candidates.append(int(worker_port))
                    else:
                        port_candidates = [p for p in open_ports if p in {6000, 6001, 6002, 6003, 6004, 6005}]

                    if not port_candidates:
                        self._log(f"⚠ Skipping {ip}: no worker port found")
                        continue

                    for port in port_candidates:
                        node_addr = f"{ip}:{port}"

                        # Cache resource hints for weighted chunk assignment.
                        node_hints = {
                            "cpu_cores": node_data.get("cpu_cores"),
                            "cpu_freq_mhz": node_data.get("cpu_freq_mhz"),
                            "cpu_percent": node_data.get("cpu_percent"),
                            "ram_total_gb": node_data.get("ram_total_gb"),
                            "ram_available_gb": node_data.get("ram_available_gb"),
                        }
                        NODE_RESOURCE_HINTS[node_addr] = node_hints
                        NODE_RESOURCE_HINTS[ip] = node_hints

                        if node_addr not in self.nodes_listbox.get(0, tk.END):
                            self.nodes_listbox.insert(tk.END, node_addr)
                            self.discovered_nodes[node_addr] = True
                            added_count += 1
                            self._log(f"✓ Auto-added worker: {node_addr}")

            self._log(f"✅ Auto configure complete. Added {added_count} worker node(s).")

        except Exception as e:
            self._log(f"❌ Auto configure failed: {str(e)}")
        finally:
            builtins.print = original_print
            self._auto_configure_running = False
            if self.auto_configure_btn:
                self.auto_configure_btn.config(state="normal")
    
    def _create_logs_tab(self, parent):
        """Create logs tab."""
        tk.Label(parent, text="System Logs", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(parent, height=25, width=100, bg="#1e1e1e", fg="#00ff00")
        self.logs_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        tk.Button(parent, text="Clear Logs", command=lambda: self.logs_text.delete("1.0", tk.END),
                 bg="#757575", fg="white").pack(padx=10, pady=5)
    
    def _log(self, message: str):
        """Add message to logs."""
        if self.logs_text is None:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.logs_text.insert(tk.END, log_msg)
        self.logs_text.see(tk.END)
        self.root.update_idletasks()
    
    def _update_task_list(self):
        """Update available tasks."""
        self.task_listbox.delete(0, tk.END)
        all_tasks = self._get_display_tasks()
        
        for task_name, description in all_tasks.items():
            self.task_listbox.insert(tk.END, f"{task_name}: {description}")
        
        self._log("✓ Task list updated")

    def _get_display_tasks(self) -> Dict[str, str]:
        """Get task list for UI (built-ins + JSON custom tasks as source of truth)."""
        tasks = {name: info.get("description", "") for name, info in SUPPORTED_TASKS.items()}

        try:
            custom_tasks = get_all_custom_tasks() or {}
            for task_name, task_data in custom_tasks.items():
                tasks[task_name] = task_data.get("description") or f"Custom task: {task_name}"
        except Exception:
            # Fallback to in-memory registry if file read fails
            tasks = get_all_tasks()

        return tasks
    def _stop_execution(self):
        """Stop execution."""
        if self.current_worker:
            self.current_worker.stop()
            self._log("Execution stopped by user")
            self.execute_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _reset_performance_panel(self, task_name: str = "-"):
        """Reset live performance panel state."""
        self._performance_stats = {
            "task_name": task_name,
            "workers": {},
            "cluster_throughput": 0.0,
            "cluster_eta_s": None,
            "completed": 0,
            "total": 0,
            "elapsed_s": 0.0,
        }
        if self.performance_task_var:
            self.performance_task_var.set(f"Task: {task_name}")
        if self.performance_summary_var:
            self.performance_summary_var.set("Throughput: 0.00 chunk/s | ETA: - | Speedup est: -")
        if self.performance_tree:
            for iid in self.performance_tree.get_children():
                self.performance_tree.delete(iid)

    def _update_performance_metrics(self, event: Dict[str, Any]):
        """Thread-safe entry point for live performance updates from workers."""
        self.root.after(0, lambda: self._apply_performance_metrics(event))

    def _apply_performance_metrics(self, event: Dict[str, Any]):
        """Render latest performance snapshot into UI panel."""
        if not isinstance(event, dict):
            return

        self._performance_stats.update({
            "task_name": event.get("task_name", self._performance_stats.get("task_name", "-")),
            "cluster_throughput": float(event.get("cluster_throughput", 0.0) or 0.0),
            "cluster_eta_s": event.get("cluster_eta_s"),
            "completed": int(event.get("completed", 0) or 0),
            "total": int(event.get("total", 0) or 0),
            "elapsed_s": float(event.get("elapsed_s", 0.0) or 0.0),
        })

        incoming_workers = event.get("workers", {}) or {}
        self._performance_stats["workers"] = incoming_workers

        if self.performance_task_var:
            task_name = self._performance_stats.get("task_name", "-")
            completed = self._performance_stats.get("completed", 0)
            total = self._performance_stats.get("total", 0)
            self.performance_task_var.set(f"Task: {task_name} | Progress: {completed}/{total}")

        if self.performance_tree:
            existing = {self.performance_tree.item(iid, "values")[0]: iid for iid in self.performance_tree.get_children() if self.performance_tree.item(iid, "values")}
            for node, st in incoming_workers.items():
                throughput = float(st.get("throughput", 0.0) or 0.0)
                retries = int(st.get("retries", 0) or 0)
                success_rate = float(st.get("success_rate", 0.0) or 0.0)
                eta_s = st.get("eta_s")
                eta_text = f"{eta_s:.1f}" if isinstance(eta_s, (int, float)) else "-"
                completed_w = int(st.get("successes", 0) or 0)
                failed_w = int(st.get("failures", 0) or 0)
                avg_latency = float(st.get("avg_latency_ms", 0.0) or 0.0)
                state = st.get("last_status", "idle")

                values = (
                    node,
                    f"{throughput:.2f}",
                    str(retries),
                    f"{success_rate:.1f}",
                    eta_text,
                    str(completed_w),
                    str(failed_w),
                    f"{avg_latency:.1f}",
                    state,
                )

                iid = existing.get(node)
                if iid:
                    self.performance_tree.item(iid, values=values)
                else:
                    self.performance_tree.insert("", "end", values=values)

        cluster_throughput = self._performance_stats.get("cluster_throughput", 0.0) or 0.0
        eta_cluster = self._performance_stats.get("cluster_eta_s")
        eta_cluster_text = f"{eta_cluster:.1f}s" if isinstance(eta_cluster, (int, float)) else "-"

        workers = self._performance_stats.get("workers", {}) or {}
        max_worker_tp = 0.0
        for st in workers.values():
            max_worker_tp = max(max_worker_tp, float(st.get("throughput", 0.0) or 0.0))
        speedup_est = (cluster_throughput / max_worker_tp) if max_worker_tp > 0 else None
        speedup_text = f"{speedup_est:.2f}x" if isinstance(speedup_est, (int, float)) else "-"

        if self.performance_summary_var:
            self.performance_summary_var.set(
                f"Throughput: {cluster_throughput:.2f} chunk/s | ETA: {eta_cluster_text} | Speedup est: {speedup_text}"
            )
    
    def _update_progress(self, progress: float):
        """Update progress bar."""
        self.progress_var.set(progress * 100)
        self.progress_label.config(text=f"{int(progress * 100)}%")
        self.root.update_idletasks()
    
    def _execution_complete(self, success: bool, result):
        """Handle execution completion."""
        self.execute_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        if success:
            self._log("✓ Task execution completed successfully")
            self.results_text.insert("1.0", json.dumps(result, indent=2))
            self.execution_results = result
            messagebox.showinfo("Success", "Task execution completed!")
        else:
            self._log(f"✗ Execution failed: {result}")
            messagebox.showerror("Error", f"Task execution failed")
        
        self.progress_var.set(100 if success else 0)
    
    def _export_results(self):
        """Export results to JSON."""
        if not self.execution_results:
            messagebox.showwarning("Export Error", "No results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.execution_results, f, indent=2)
                messagebox.showinfo("Success", f"Results exported to {file_path}")
                self._log(f"Results exported: {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
    
    def cleanup(self):
        """Cleanup on exit."""
        if self.discovery_worker:
            self.discovery_worker.stop()
    
    def _on_task_select(self, event):
        """Handle task selection and generate parameter fields."""
        selection = self.task_listbox.curselection()
        if selection:
            task_str = self.task_listbox.get(selection[0])
            self.current_task = task_str.split(":")[0].strip()
            
            self.config_text.delete("1.0", tk.END)
            self.config_text.insert("1.0", f"Selected Task: {self.current_task}\n\n")
            
            all_tasks = self._get_display_tasks()
            if self.current_task in all_tasks:
                self.config_text.insert(tk.END, f"Description: {all_tasks[self.current_task]}\n\n")
            
            self._clear_parameter_fields()
            
            task_info = get_task_info(self.current_task)
            if task_info:
                params, defaults = resolve_task_parameters(task_info)

                if params:
                    self.config_text.insert(tk.END, f"Parameters: {', '.join(params)}\n\n")
                    self._create_parameter_fields(params, defaults)
                else:
                    self.config_text.insert(tk.END, "Parameters: None detected\n\n")
            elif self.current_task == "range_sum":
                self._create_parameter_fields(["start", "end", "chunk_size"], {})
            elif self.current_task == "array_sum":
                self._create_parameter_fields(["numbers", "chunk_size"], {})
            
            self._log(f"Task selected: {self.current_task}")
    
    def _clear_parameter_fields(self):
        """Clear previously created parameter fields."""
        if hasattr(self, 'param_entries'):
            for widget in self.param_entries.values():
                if widget:
                    widget.destroy()
            self.param_entries.clear()
    
    def _create_parameter_fields(self, params: List[str], defaults: Optional[Dict] = None):
        """Dynamically create input fields for task parameters."""
        if defaults is None:
            defaults = {}
        elif not isinstance(defaults, dict):
            # Defensive fallback for unexpected metadata shapes.
            defaults = {}

        if not hasattr(self, 'param_entries'):
            self.param_entries = {}
        
        for child in self.param_frame_wrapper.winfo_children():
            child.destroy()
        
        self.param_entries = {}
        
        if not params:
            tk.Label(self.param_frame_wrapper, text="(No parameters for this task)", 
                    bg="white", fg="#999999").pack()
            return
        
        for param_name in params:
            default_val = defaults.get(param_name, "")
            
            frame = tk.Frame(self.param_frame_wrapper, bg="white")
            frame.pack(fill="x", padx=5, pady=3)
            
            label = tk.Label(frame, text=f"{param_name}:", width=20, anchor="w", bg="white", font=("Arial", 9))
            label.pack(side="left", padx=5)
            
            entry = tk.Entry(frame, width=40, font=("Arial", 9))
            entry.pack(side="left", padx=5, fill="x", expand=True)

            def _browse_files(target_entry=entry):
                files = filedialog.askopenfilenames(title=f"Select files for {param_name}")
                if files:
                    target_entry.delete(0, tk.END)
                    target_entry.insert(0, ",".join(files))

            if "file" in param_name.lower() or "dataset" in param_name.lower():
                tk.Button(frame, text="Browse", command=_browse_files,
                          bg="#607D8B", fg="white", width=8).pack(side="left", padx=5)
            
            if default_val:
                entry.insert(0, str(default_val))
            
            self.param_entries[param_name] = entry
    
    def _add_node(self):
        """Add worker node."""
        node = self.node_input_var.get().strip()
        if node:
            self.nodes_listbox.insert(tk.END, node)
            self._log(f"Node added: {node}")
            self.node_input_var.set("")
        else:
            messagebox.showwarning("Input Error", "Please enter a valid node address")
    
    def _remove_node(self):
        """Remove selected node."""
        selection = self.nodes_listbox.curselection()
        if selection:
            node = self.nodes_listbox.get(selection[0])
            self.nodes_listbox.delete(selection[0])
            self._log(f"Node removed: {node}")
    
    def _test_node_connection(self):
        """Test connection to selected node."""
        selection = self.nodes_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a node to test")
            return
        
        node = self.nodes_listbox.get(selection[0])
        self._log(f"Testing connection to {node}...")
        
        try:
            host, port = node.split(":")
            port = int(port)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                self._log(f"✓ Connection successful to {node}")
                messagebox.showinfo("Connection Test", f"✓ Successfully connected to {node}")
            else:
                self._log(f"✗ Connection failed to {node}")
                messagebox.showerror("Connection Test", f"✗ Could not connect to {node}")
        except Exception as e:
            self._log(f"✗ Connection test error: {str(e)}")
            messagebox.showerror("Connection Test", f"✗ Error: {str(e)}")
    
    def _open_custom_task_dialog(self):
        """Open custom task dialog with worker nodes callback."""
        def get_worker_nodes():
            """Get current worker nodes from listbox."""
            return list(self.nodes_listbox.get(0, tk.END))
        
        dialog = CustomTaskDialog(self.root, worker_nodes_callback=get_worker_nodes)
        self.root.wait_window(dialog)
        self._update_task_list()
    
    def _open_edit_task_dialog(self):
        """Open edit dialog for selected custom task."""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a task to edit")
            return
        
        task_str = self.task_listbox.get(selection[0])
        task_name = task_str.split(":")[0].strip()
        
        # Check if it's a built-in task
        if task_name in ["range_sum", "array_sum"]:
            messagebox.showwarning("Edit Error", f"Cannot edit built-in task '{task_name}'")
            return
        
        # Load task data from registry
        task_data = load_custom_task(task_name)
        
        if not task_data:
            messagebox.showerror("Load Error", f"Could not load task '{task_name}'")
            return
        
        dialog = EditCustomTaskDialog(self.root, task_name, task_data)
        self.root.wait_window(dialog)
        self._update_task_list()
    
    def _delete_task(self):
        """Delete selected custom task."""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a task to delete")
            return
        
        task_str = self.task_listbox.get(selection[0])
        task_name = task_str.split(":")[0].strip()
        
        # Prevent deleting built-in tasks
        if task_name in ["range_sum", "array_sum"]:
            messagebox.showerror("Delete Error", f"Cannot delete built-in task '{task_name}'")
            return
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Delete task '{task_name}'?\n\nThis cannot be undone."):
            try:
                if delete_custom_task(task_name):
                    # Also remove from in-memory registry (if present) to avoid stale runtime entries.
                    try:
                        from module3_execution.tasks import _custom_registry
                        _custom_registry._tasks.pop(task_name, None)
                        _custom_registry._validators.pop(task_name, None)
                    except Exception:
                        pass

                    if self.current_task == task_name:
                        self.current_task = None
                        self.config_text.delete("1.0", tk.END)
                        self.config_text.insert("1.0", "(Select a task)")
                        self._clear_parameter_fields()

                    messagebox.showinfo("Success", f"Task '{task_name}' deleted")
                    self._log(f"Task deleted: {task_name}")
                    self._update_task_list()
                else:
                    messagebox.showerror("Delete Error", f"Could not delete task '{task_name}'")
            except Exception as e:
                messagebox.showerror("Delete Error", str(e))
    
    def _execute_task(self):
        """Execute selected task on worker nodes."""
        if not self.current_task:
            messagebox.showerror("Selection Error", "Please select a task first")
            return
        
        nodes = list(self.nodes_listbox.get(0, tk.END))
        if not nodes:
            messagebox.showerror("Configuration Error", "No worker nodes configured")
            return
        
        payload = {}
        
        try:
            for param_name, entry_widget in self.param_entries.items():
                value = entry_widget.get().strip()
                if not value:
                    messagebox.showerror("Parameter Error", f"Parameter '{param_name}' cannot be empty")
                    return
                
                try:
                    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                        payload[param_name] = int(value)
                    elif '.' in value:
                        payload[param_name] = float(value)
                    elif ',' in value:
                        try:
                            payload[param_name] = [int(x.strip()) for x in value.split(",")]
                        except ValueError:
                            payload[param_name] = [x.strip() for x in value.split(",")]
                    else:
                        payload[param_name] = value
                except Exception:
                    payload[param_name] = value

            # Merge any attached dataset/file parameters saved with the custom task
            task_info = get_task_info(self.current_task)
            stored_params = task_info.get("parameters", {}) if task_info else {}
            if isinstance(stored_params, dict):
                for key, value in stored_params.items():
                    if "file" in key.lower() or "dataset" in key.lower():
                        if value and not payload.get(key):
                            payload[key] = value
                            self._log(f"📎 Using stored attachment list for '{key}' ({len(value)} files)")

            # Validate attached file parameters (dataset/file paths)
            try:
                for key, value in payload.items():
                    if "file" in key.lower() or "dataset" in key.lower():
                        validate_file_attachments(value)
            except Exception as e:
                messagebox.showerror("File Validation Error", str(e))
                self.execute_btn.config(state="normal")
                self.stop_btn.config(state="disabled")
                return
            
            self.execute_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.progress_var.set(0)
            self.results_text.delete("1.0", tk.END)
            self._reset_performance_panel(self.current_task)
            
            self._log(f"Starting: {self.current_task}")
            
            # Split tasks based on task type
            if self.current_task == "range_sum":
                start = payload.get("start", 1)
                end = payload.get("end", 100)
                chunk_size = payload.get("chunk_size", 10000)
                
                # Generate chunked tasks
                tasks = generate_range_sum_tasks(start, end, chunk_size)
                self._log(f"Split into {len(tasks)} chunks")
                self._log(f"Sending {len(tasks)} tasks to {len(nodes)} node(s)")
                
                # Execute chunked tasks
                self.current_worker = ChunkedTaskExecutionWorker(
                    self.current_task, tasks, nodes,
                    self._update_progress, self._execution_complete, self._log,
                    metrics_callback=self._update_performance_metrics
                )
                self.current_worker.start()
            
            elif self.current_task == "array_sum":
                numbers = payload.get("numbers", [])
                chunk_size = payload.get("chunk_size", 5000)
                
                # Generate chunked tasks
                tasks = generate_array_sum_tasks(numbers, chunk_size)
                self._log(f"Split into {len(tasks)} chunks")
                self._log(f"Sending {len(tasks)} tasks to {len(nodes)} node(s)")
                
                # Execute chunked tasks
                self.current_worker = ChunkedTaskExecutionWorker(
                    self.current_task, tasks, nodes,
                    self._update_progress, self._execution_complete, self._log,
                    metrics_callback=self._update_performance_metrics
                )
                self.current_worker.start()
            
            else:
                # For custom tasks - ALWAYS try to create chunks
                chunk_size = payload.get("chunk_size")

                # Auto-estimate chunk size if missing
                if not chunk_size:
                    estimated = estimate_chunk_size(payload, len(nodes))
                    if estimated:
                        chunk_size = estimated
                        payload["chunk_size"] = chunk_size
                        self._log(f"⚙ Auto chunk_size set to {chunk_size}")

                # Try to chunk the task when chunk_size is available
                if chunk_size:
                    tasks = self._create_custom_chunks(payload, int(chunk_size), len(nodes))

                    if len(tasks) > 1:
                        self._log(f"Split into {len(tasks)} chunks")
                        self._log(f"Sending {len(tasks)} tasks to {len(nodes)} node(s)")

                        self.current_worker = ChunkedTaskExecutionWorker(
                            self.current_task, tasks, nodes,
                            self._update_progress, self._execution_complete, self._log,
                            metrics_callback=self._update_performance_metrics
                        )
                        self.current_worker.start()
                        return

                # Fallback: send as-is to all nodes
                self._log(f"Sending to {len(nodes)} node(s): {', '.join(nodes)}")
                self._log(f"Payload: {json.dumps(payload, indent=2)}")

                self.current_worker = TaskExecutionWorker(
                    self.current_task, payload, nodes,
                    self._update_progress, self._execution_complete, self._log,
                    metrics_callback=self._update_performance_metrics
                )
                self.current_worker.start()
        
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to execute task:\n{str(e)}")
            self.execute_btn.config(state="normal")
    
    def _create_custom_chunks(self, payload: Dict, chunk_size: int, num_nodes: int) -> List[Dict]:
        """
        Create chunks for custom tasks.
        Supports splitting list/array parameters and numeric ranges intelligently.
        
        Args:
            payload: Original payload with chunk_size
            chunk_size: Size of each chunk
            num_nodes: Number of worker nodes
        
        Returns:
            List of task dicts with chunked payloads
        """
        tasks = []

        # Strategy 1: Range-based chunking for payloads with start/end
        if "start" in payload and "end" in payload:
            try:
                start = int(payload.get("start"))
                end = int(payload.get("end"))

                if chunk_size <= 0:
                    self._log("⚠ Invalid chunk_size for range chunking. Sending as-is to all nodes.")
                    return [{"task_name": self.current_task, "payload": payload}]

                # Normalize reversed range
                if start > end:
                    start, end = end, start

                self._log(f"Chunking numeric range with size {chunk_size}")
                self._log(f"Total range: {start} to {end}")

                chunk_count = 0
                current = start
                while current <= end:
                    chunk_end = min(current + chunk_size - 1, end)
                    chunk_payload = payload.copy()
                    chunk_payload["start"] = current
                    chunk_payload["end"] = chunk_end

                    task_id = f"{self.current_task}-range-{chunk_count + 1}"
                    tasks.append({
                        "task_id": task_id,
                        "task_name": self.current_task,
                        "payload": chunk_payload
                    })

                    chunk_count += 1
                    self._log(f"  Chunk {chunk_count}: range {current} to {chunk_end}")
                    current = chunk_end + 1

                if tasks:
                    return tasks
            except Exception:
                # Fall through to list-based chunking if start/end are not usable ints.
                pass
        
        # Find list/array parameters in payload to chunk (exclude chunk_size itself)
        list_params = {}
        for key, value in payload.items():
            if isinstance(value, list) and key.lower() != "chunk_size":
                list_params[key] = value

        # Strategy 2: Generic data chunking (preferred when `data` exists)
        if "data" in list_params:
            data_list = list_params["data"]
            self._log(f"Chunking generic 'data' with size {chunk_size}")
            self._log(f"Total items: {len(data_list)}")

            chunk_count = 0
            for i in range(0, len(data_list), chunk_size):
                chunk = data_list[i:i + chunk_size]
                chunk_payload = payload.copy()
                chunk_payload["data"] = chunk
                task_id = f"{self.current_task}-data-{chunk_count + 1}"

                tasks.append({
                    "task_id": task_id,
                    "task_name": self.current_task,
                    "payload": chunk_payload
                })
                chunk_count += 1
                self._log(f"  Data chunk {chunk_count}: {len(chunk)} items (indices {i} to {i + len(chunk) - 1})")

            if tasks:
                return tasks
        
        # If no list parameters found, return single task
        if not list_params:
            self._log(f"⚠ No list parameters found to chunk. Sending as-is to all nodes.")
            return [{"task_name": self.current_task, "payload": payload}]
        
        # Get the first (primary) list parameter to chunk
        primary_param = list(list_params.keys())[0]
        original_list = list_params[primary_param]
        
        self._log(f"Chunking parameter '{primary_param}' with size {chunk_size}")
        self._log(f"Total items: {len(original_list)}")
        
        # Create chunks from the list
        chunk_count = 0
        for i in range(0, len(original_list), chunk_size):
            chunk = original_list[i:i + chunk_size]
            chunk_payload = payload.copy()
            chunk_payload[primary_param] = chunk
            task_id = f"{self.current_task}-list-{chunk_count + 1}"
            
            tasks.append({
                "task_id": task_id,
                "task_name": self.current_task,
                "payload": chunk_payload
            })
            chunk_count += 1
            self._log(f"  Chunk {chunk_count}: {len(chunk)} items (indices {i} to {i + len(chunk) - 1})")
        
        return tasks
