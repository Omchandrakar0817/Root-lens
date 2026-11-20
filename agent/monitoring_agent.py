#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import psutil


def collect_snapshot() -> dict[str, Any]:
    cpu = psutil.cpu_percent(interval=None, percpu=False)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append({
                "pid": info.get("pid"),
                "name": info.get("name"),
                "cpu_percent": round(float(info.get("cpu_percent") or 0), 2),
                "memory_percent": round(float(info.get("memory_percent") or 0), 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    processes.sort(key=lambda item: item["memory_percent"], reverse=True)
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "cpu_percent": round(float(cpu), 2),
        "memory_percent": round(float(memory.percent), 2),
        "disk_percent": round(float((disk.used / disk.total) * 100), 2),
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        },
        "processes": processes[:20],
        "logs": [f"snapshot cpu={cpu}% memory={memory.percent}% disk={((disk.used / disk.total) * 100):.1f}%"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Send host metrics to the Incident RCA API.")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/agents/ingest", help="Endpoint to send metrics to.")
    parser.add_argument("--token", required=True, help="Agent bearer token issued by the platform.")
    parser.add_argument("--interval", type=float, default=60.0, help="Seconds between metrics batches.")
    args = parser.parse_args()

    while True:
        payload = collect_snapshot()
        try:
            response = httpx.post(
                args.api_url,
                json=payload,
                headers={"Authorization": f"Bearer {args.token}"},
                timeout=15,
            )
            response.raise_for_status()
            print(f"{datetime.now(UTC).isoformat()} -> {response.status_code}")
        except Exception as exc:  # noqa: BLE001
            print(f"{datetime.now(UTC).isoformat()} -> send failed: {exc}")
        time.sleep(max(args.interval, 5.0))


if __name__ == "__main__":
    main()
