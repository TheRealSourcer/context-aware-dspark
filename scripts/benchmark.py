#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import threading
import time

import requests


ROOT = Path(__file__).resolve().parents[2]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def wait_ready(port: int, process: subprocess.Popen, timeout: float = 180.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited with status {process.returncode}")
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise TimeoutError("llama-server did not become ready")


def request(port: int, prompt: str, max_tokens: int) -> tuple[dict, float, dict]:
    payload = {
        "model": "Qwen3-8B",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    samples = []
    stop_sampling = threading.Event()

    def sample_gpu() -> None:
        while not stop_sampling.is_set():
            samples.append(gpu_stats())
            stop_sampling.wait(0.02)

    sampler = threading.Thread(target=sample_gpu, daemon=True)
    sampler.start()
    start = time.perf_counter()
    try:
        response = requests.post(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            json=payload,
            timeout=900,
        )
        elapsed = time.perf_counter() - start
    finally:
        stop_sampling.set()
        sampler.join(timeout=1)
    response.raise_for_status()
    peaks = {}
    for key in ("gpu_clock_mhz", "gpu_memory_clock_mhz", "gpu_power_w", "gpu_temp_c", "gpu_vram_used_mib"):
        values = [sample[key] for sample in samples if sample.get(key) is not None]
        peaks[f"peak_{key}"] = max(values) if values else None
    return response.json(), elapsed, peaks


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def read_number(path: str, divisor: float) -> float | None:
    try:
        return float(Path(path).read_text(encoding="utf-8").strip()) / divisor
    except (OSError, ValueError):
        return None


def gpu_stats() -> dict:
    base = "/sys/class/drm/card1/device"
    hwmon = base + "/hwmon/hwmon1"
    return {
        "gpu_clock_mhz": read_number(hwmon + "/freq1_input", 1_000_000),
        "gpu_memory_clock_mhz": read_number(hwmon + "/freq2_input", 1_000_000),
        "gpu_power_w": read_number(hwmon + "/power1_average", 1_000_000),
        "gpu_temp_c": read_number(hwmon + "/temp1_input", 1_000),
        "gpu_vram_used_mib": read_number(base + "/mem_info_vram_used", 1024 * 1024),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--methods", nargs="+", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--min-memory-clock", type=float, default=900)
    parser.add_argument("--max-warmups", type=int, default=20)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    root = args.root.resolve()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    prompts = load_jsonl(args.prompts)
    if args.limit is not None:
        prompts = prompts[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.logs.mkdir(parents=True, exist_ok=True)

    existing = set()
    if args.output.exists():
        for row in load_jsonl(args.output):
            existing.add((row["method"], row["repeat"], row["prompt_id"]))

    env = os.environ.copy()
    runtime_dir = root / Path(config["runtime"]).parent
    env["LD_LIBRARY_PATH"] = str(runtime_dir) + ":" + env.get("LD_LIBRARY_PATH", "")

    for repeat in range(args.repeats):
        order = list(prompts)
        random.Random(20260803 + repeat).shuffle(order)
        method_order = list(args.methods)
        random.Random(8675309 + repeat).shuffle(method_order)
        for method in method_order:
            if method not in config["methods"]:
                raise KeyError(f"Unknown method {method}")
            pending = [row for row in order if (method, repeat, row["prompt_id"]) not in existing]
            if not pending:
                continue

            command = [
                str(root / config["runtime"]),
                "-m",
                str(root / config["target"]),
                "--port",
                str(args.port),
                *config["common_args"],
                *config["methods"][method],
            ]
            log_path = args.logs / f"{method}-r{repeat}.log"
            with log_path.open("w", encoding="utf-8") as log_handle:
                process = subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                try:
                    wait_ready(args.port, process)
                    warmup_count = 0
                    while warmup_count < args.max_warmups:
                        warmup_response, _, warmup_gpu = request(
                            args.port,
                            "Write the integers from 1 through 500, one per line. Do not omit any integer and do not stop early.",
                            384,
                        )
                        warmup_count += 1
                        if (warmup_gpu.get("peak_gpu_memory_clock_mhz") or 0) >= args.min_memory_clock:
                            break
                    print(
                        f"{method} r{repeat} warmup={warmup_count} "
                        f"mclk={warmup_gpu.get('peak_gpu_memory_clock_mhz')} "
                        f"tps={warmup_response.get('timings', {}).get('predicted_per_second')}",
                        flush=True,
                    )
                    with args.output.open("a", encoding="utf-8") as output_handle:
                        for position, prompt in enumerate(pending):
                            response, elapsed, gpu_peak = request(args.port, prompt["prompt"], args.max_tokens)
                            content = response["choices"][0]["message"]["content"]
                            timing = response.get("timings", {})
                            row = {
                                **prompt,
                                "method": method,
                                "repeat": repeat,
                                "position": position,
                                "max_tokens": args.max_tokens,
                                "wall_seconds": elapsed,
                                "content": content,
                                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                                "finish_reason": response["choices"][0].get("finish_reason"),
                                "usage": response.get("usage", {}),
                                "timings": timing,
                                "gpu": gpu_stats(),
                                "gpu_peak": gpu_peak,
                                "warmup_count": warmup_count,
                            }
                            output_handle.write(json.dumps(row, ensure_ascii=True) + "\n")
                            output_handle.flush()
                            print(
                                f"{method} r{repeat} {position + 1}/{len(pending)} "
                                f"{prompt['domain']} {prompt['prompt_id']} "
                                f"{timing.get('predicted_per_second', float('nan')):.2f} tok/s",
                                flush=True,
                            )
                finally:
                    stop_server(process)


if __name__ == "__main__":
    main()
