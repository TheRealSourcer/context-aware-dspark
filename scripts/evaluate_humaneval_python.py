#!/usr/bin/env python3
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import subprocess
import tempfile


DEFAULT_IMAGE = "docker.io/library/python@sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def extract_python(content: str, entry_point: str) -> tuple[str | None, str | None]:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", content, flags=re.IGNORECASE | re.DOTALL)
    matching = [block for block in blocks if re.search(rf"\bdef\s+{re.escape(entry_point)}\s*\(", block)]
    if len(matching) == 1:
        return matching[0].strip() + "\n", None
    if len(matching) > 1:
        return None, "ambiguous_code_blocks"
    if blocks:
        return None, "entry_point_missing"
    stripped = content.strip()
    if re.search(rf"\bdef\s+{re.escape(entry_point)}\s*\(", stripped):
        return stripped + "\n", None
    return None, "no_code_block"


def run_case(code: str, test: str, image: str, timeout: float) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="humaneval-") as directory:
        case_dir = Path(directory)
        case_dir.chmod(0o755)
        runner = case_dir / "runner.py"
        runner.write_text(code + "\n" + test + "\n", encoding="utf-8")
        runner.chmod(0o644)
        command = [
            "podman",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "all",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "32",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--user",
            "65534:65534",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--volume",
            f"{case_dir}:/case:ro,Z",
            image,
            "python",
            "-I",
            "-B",
            "/case/runner.py",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return "timeout", "execution exceeded time limit"
        detail = (result.stderr or result.stdout).strip()[-2000:]
        if result.returncode == 0:
            return "passed", detail
        if "SyntaxError" in detail or "IndentationError" in detail:
            return "syntax_error", detail
        if "AssertionError" in detail:
            return "test_failure", detail
        return "runtime_error", detail


def bootstrap_accuracy(values: list[int], seed: int) -> dict:
    rng = random.Random(seed)
    samples = []
    for _ in range(10000):
        samples.append(sum(values[rng.randrange(len(values))] for _ in values) / len(values))
    return {
        "accuracy": sum(values) / len(values),
        "ci_low": percentile(samples, 0.025),
        "ci_high": percentile(samples, 0.975),
    }


def bootstrap_difference(values: list[int], reference: list[int], seed: int) -> dict:
    differences = [value - ref for value, ref in zip(values, reference)]
    rng = random.Random(seed)
    samples = []
    for _ in range(10000):
        samples.append(sum(differences[rng.randrange(len(differences))] for _ in differences) / len(differences))
    return {
        "difference": sum(differences) / len(differences),
        "ci_low": percentile(samples, 0.025),
        "ci_high": percentile(samples, 0.975),
        "gained": sum(value == 1 and ref == 0 for value, ref in zip(values, reference)),
        "lost": sum(value == 0 and ref == 1 for value, ref in zip(values, reference)),
    }


def bootstrap_speedup(rows: list[dict], method: str, reference: str, prompt_ids: list[str], seed: int) -> dict:
    indexed = {(row["method"], row["repeat"], row["prompt_id"]): row for row in rows}
    repeats = sorted({row["repeat"] for row in rows})
    ratios = []
    for prompt_id in prompt_ids:
        values = [
            math.log(
                indexed[(method, repeat, prompt_id)]["timings"]["predicted_per_second"]
                / indexed[(reference, repeat, prompt_id)]["timings"]["predicted_per_second"]
            )
            for repeat in repeats
        ]
        ratios.append(sum(values) / len(values))
    rng = random.Random(seed)
    samples = []
    for _ in range(10000):
        samples.append(math.exp(sum(ratios[rng.randrange(len(ratios))] for _ in ratios) / len(ratios)))
    return {
        "reference": reference,
        "geomean": math.exp(sum(ratios) / len(ratios)),
        "ci_low": percentile(samples, 0.025),
        "ci_high": percentile(samples, 0.975),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("tests", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--methods", nargs="+", default=["baseline", "dspark_n7", "dspark_n7_dynamic"])
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--reuse-evaluated", action="store_true")
    parser.add_argument("--quality-repeat", type=int, default=0)
    args = parser.parse_args()

    rows = load_jsonl(args.results)
    tests = {row["prompt_id"]: row for row in load_jsonl(args.tests)}
    timing_rows = [row for row in rows if row["method"] in args.methods]
    timing_repeats = sorted({row["repeat"] for row in timing_rows})
    timing_keys = [(row["method"], row["repeat"], row["prompt_id"]) for row in timing_rows]
    expected_timing = {
        (method, repeat, prompt_id)
        for method in args.methods
        for repeat in timing_repeats
        for prompt_id in tests
    }
    if len(timing_keys) != len(set(timing_keys)) or set(timing_keys) != expected_timing:
        raise RuntimeError("Timing results are not a complete method, repeat, and task design")

    selected = [row for row in timing_rows if row["repeat"] == args.quality_repeat]
    keys = [(row["method"], row["prompt_id"]) for row in selected]
    expected = {(method, prompt_id) for method in args.methods for prompt_id in tests}
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise RuntimeError("Results must contain exactly one row for every requested method and task")

    if args.reuse_evaluated:
        evaluated = load_jsonl(args.output)
        evaluated_keys = {(row["method"], row["prompt_id"]) for row in evaluated}
        if len(evaluated) != len(expected) or evaluated_keys != expected:
            raise RuntimeError("Existing evaluated output does not match the requested methods and tasks")
    else:
        evaluated = []
        for index, row in enumerate(selected, start=1):
            test = tests[row["prompt_id"]]
            prompt_hash = hashlib.sha256(row["prompt"].encode()).hexdigest()
            if prompt_hash != test["prompt_sha256"]:
                raise RuntimeError(f"Prompt hash mismatch for {row['prompt_id']}")
            code, extraction_error = extract_python(row["content"], test["entry_point"])
            if extraction_error:
                status, detail = extraction_error, ""
            else:
                status, detail = run_case(code or "", test["test"], args.image, args.timeout)
            evaluated.append(
                {
                    "content_sha256": row["content_sha256"],
                    "detail": detail,
                    "finish_reason": row.get("finish_reason"),
                    "method": row["method"],
                    "passed": status == "passed",
                    "prompt_id": row["prompt_id"],
                    "status": status,
                }
            )
            print(f"{index}/{len(selected)} {row['method']} {row['prompt_id']} {status}", flush=True)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for row in evaluated:
                handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    by_method = defaultdict(list)
    status_counts = defaultdict(lambda: defaultdict(int))
    for row in evaluated:
        by_method[row["method"]].append(int(row["passed"]))
        status_counts[row["method"]][row["status"]] += 1
    summary = {
        "container_image": args.image,
        "methods": {},
        "quality_repeat": args.quality_repeat,
        "results_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
        "tasks": len(tests),
        "tests_sha256": hashlib.sha256(args.tests.read_bytes()).hexdigest(),
        "timing_repeats": timing_repeats,
    }
    for method in args.methods:
        summary["methods"][method] = {
            **bootstrap_accuracy(by_method[method], 20260821),
            "passed": sum(by_method[method]),
            "status_counts": dict(sorted(status_counts[method].items())),
            "total": len(by_method[method]),
        }

    evaluated_index = {(row["method"], row["prompt_id"]): row for row in evaluated}
    result_index = {(row["method"], row["prompt_id"]): row for row in selected}
    prompt_ids = sorted(tests)
    for method in args.methods:
        method_rows = [row for row in timing_rows if row["method"] == method]
        summary["methods"][method]["decode_tps_mean"] = sum(
            row["timings"]["predicted_per_second"] for row in method_rows
        ) / len(method_rows)
        summary["methods"][method]["draft_tokens"] = sum(row["timings"].get("draft_n", 0) for row in method_rows)
        summary["methods"][method]["accepted_tokens"] = sum(
            row["timings"].get("draft_n_accepted", 0) for row in method_rows
        )
        summary["methods"][method]["memory_clock_values"] = sorted(
            {row["gpu_peak"]["peak_gpu_memory_clock_mhz"] for row in method_rows}
        )
    for method in args.methods:
        if method == "baseline":
            continue
        method_values = [int(evaluated_index[(method, prompt_id)]["passed"]) for prompt_id in prompt_ids]
        baseline_values = [int(evaluated_index[("baseline", prompt_id)]["passed"]) for prompt_id in prompt_ids]
        summary["methods"][method]["difference_vs_baseline"] = bootstrap_difference(
            method_values, baseline_values, 20260822
        )
        summary["methods"][method]["exact_outputs_vs_baseline"] = sum(
            result_index[(method, prompt_id)]["content_sha256"]
            == result_index[("baseline", prompt_id)]["content_sha256"]
            for prompt_id in prompt_ids
        )
        summary["methods"][method]["speedup_vs_baseline"] = bootstrap_speedup(
            timing_rows, method, "baseline", prompt_ids, 20260824
        )
    if "dspark_n7" in args.methods and "dspark_n7_dynamic" in args.methods:
        fixed_values = [int(evaluated_index[("dspark_n7", prompt_id)]["passed"]) for prompt_id in prompt_ids]
        dynamic_values = [
            int(evaluated_index[("dspark_n7_dynamic", prompt_id)]["passed"]) for prompt_id in prompt_ids
        ]
        summary["methods"]["dspark_n7_dynamic"]["difference_vs_dspark_n7"] = bootstrap_difference(
            dynamic_values, fixed_values, 20260823
        )
        summary["methods"]["dspark_n7_dynamic"]["exact_outputs_vs_dspark_n7"] = sum(
            result_index[("dspark_n7_dynamic", prompt_id)]["content_sha256"]
            == result_index[("dspark_n7", prompt_id)]["content_sha256"]
            for prompt_id in prompt_ids
        )
        summary["methods"]["dspark_n7_dynamic"]["speedup_vs_dspark_n7"] = bootstrap_speedup(
            timing_rows, "dspark_n7_dynamic", "dspark_n7", prompt_ids, 20260825
        )

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
