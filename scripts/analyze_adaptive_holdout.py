#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


METHODS = [
    "baseline",
    "dflash_n4",
    "dspark_n7",
    "dspark_n7_dynamic",
    "dspark_n7_stop",
    "dspark_n7_adaptive",
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def percentile(values: list[float], probability: float) -> float:
    values = sorted(values)
    position = probability * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def paired_speedup(rows: list[dict], method: str, reference: str, seed: int = 20260804) -> dict:
    indexed = {(row["method"], row["repeat"], row["prompt_id"]): row for row in rows}
    by_source = defaultdict(list)
    for row in rows:
        if row["method"] != method:
            continue
        ref = indexed[(reference, row["repeat"], row["prompt_id"])]
        by_source[row["base_prompt_id"]].append(
            math.log(row["timings"]["predicted_per_second"] / ref["timings"]["predicted_per_second"])
        )

    source_logs = [mean(values) for values in by_source.values()]
    point = math.exp(mean(source_logs))
    rng = random.Random(seed)
    samples = []
    for _ in range(10000):
        sampled = [source_logs[rng.randrange(len(source_logs))] for _ in source_logs]
        samples.append(math.exp(mean(sampled)))
    return {
        "reference": reference,
        "cluster_unit": "base_prompt_id",
        "clusters": len(source_logs),
        "geomean": point,
        "ci_low": percentile(samples, 0.025),
        "ci_high": percentile(samples, 0.975),
    }


def method_summary(rows: list[dict], method: str) -> dict:
    selected = [row for row in rows if row["method"] == method]
    return {
        "rows": len(selected),
        "decode_tps_mean": mean([row["timings"]["predicted_per_second"] for row in selected]),
        "completion_tps_mean": mean([row["usage"]["completion_tokens"] / row["wall_seconds"] for row in selected]),
        "completion_tokens": sum(row["usage"]["completion_tokens"] for row in selected),
        "draft_attempts": sum(row["timings"].get("draft_n_attempts", 0) for row in selected),
        "draft_tokens": sum(row["timings"].get("draft_n", 0) for row in selected),
        "accepted_tokens": sum(row["timings"].get("draft_n_accepted", 0) for row in selected),
        "draft_ms": sum(row["timings"].get("draft_ms", 0.0) for row in selected),
        "terminal_off_requests": sum(row["timings"].get("draft_terminal_off_position", -1) >= 0 for row in selected),
        "memory_clock_values": sorted({row["gpu_peak"]["peak_gpu_memory_clock_mhz"] for row in selected}),
    }


def output_identity(rows: list[dict], method: str, reference: str) -> dict:
    indexed = {(row["method"], row["repeat"], row["prompt_id"]): row for row in rows}
    selected = [row for row in rows if row["method"] == method]
    exact = 0
    same_tokens = 0
    for row in selected:
        ref = indexed[(reference, row["repeat"], row["prompt_id"])]
        exact += row["content_sha256"] == ref["content_sha256"]
        same_tokens += row["usage"]["completion_tokens"] == ref["usage"]["completion_tokens"]
    return {"reference": reference, "exact": exact, "same_token_count": same_tokens, "pairs": len(selected)}


def validate_rows(rows: list[dict]) -> dict:
    methods = sorted({row["method"] for row in rows})
    if methods != sorted(METHODS):
        raise RuntimeError(f"Expected methods {METHODS}, found {methods}")

    repeats = sorted({row["repeat"] for row in rows})
    if repeats != [0, 1, 2]:
        raise RuntimeError(f"Expected repeats [0, 1, 2], found {repeats}")

    keys = [(row["method"], row["repeat"], row["prompt_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate method, repeat, and prompt cells found")

    prompt_ids = sorted({row["prompt_id"] for row in rows})
    expected_keys = {
        (method, repeat, prompt_id)
        for method in METHODS
        for repeat in repeats
        for prompt_id in prompt_ids
    }
    if len(prompt_ids) != 24 or set(keys) != expected_keys:
        raise RuntimeError("Expected a complete 6 method x 3 repeat x 24 prompt design")

    prompt_metadata = {}
    for row in rows:
        metadata = (row["base_prompt_id"], row["context_bin"], row.get("source_id"))
        previous = prompt_metadata.setdefault(row["prompt_id"], metadata)
        if previous != metadata:
            raise RuntimeError(f"Inconsistent metadata for prompt {row['prompt_id']}")

    source_contexts = defaultdict(set)
    for base_prompt_id, context_bin, _ in prompt_metadata.values():
        source_contexts[base_prompt_id].add(context_bin)
    expected_contexts = {512, 2048, 4096, 6144}
    if len(source_contexts) != 6 or any(values != expected_contexts for values in source_contexts.values()):
        raise RuntimeError("Expected six source examples with all four context variants")

    memory_clocks = sorted({row["gpu_peak"]["peak_gpu_memory_clock_mhz"] for row in rows})
    if memory_clocks != [456.0]:
        raise RuntimeError(f"Expected only the archived 456 MHz memory-clock state, found {memory_clocks}")

    return {
        "prompts": len(prompt_ids),
        "source_clusters": len(source_contexts),
        "contexts": sorted(expected_contexts),
        "repeats": repeats,
        "memory_clock_values": memory_clocks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--table", type=Path)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    validation = validate_rows(rows)

    summary = {
        "input": str(args.input),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "rows": len(rows),
        "validation": validation,
        "methods": {},
        "context_decode_tps": {},
    }
    for method in METHODS:
        cur = method_summary(rows, method)
        if method != "baseline":
            cur["speedup_vs_baseline"] = paired_speedup(rows, method, "baseline")
            cur["identity_vs_baseline"] = output_identity(rows, method, "baseline")
        if method in ("dspark_n7_dynamic", "dspark_n7_stop", "dspark_n7_adaptive"):
            cur["speedup_vs_dspark"] = paired_speedup(rows, method, "dspark_n7")
            cur["identity_vs_dspark"] = output_identity(rows, method, "dspark_n7")
        summary["methods"][method] = cur

        selected = [row for row in rows if row["method"] == method]
        summary["context_decode_tps"][method] = {
            str(context): mean([
                row["timings"]["predicted_per_second"] for row in selected if row["context_bin"] == context
            ])
            for context in (512, 2048, 4096, 6144)
        }

    text = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.table:
        labels = {
            "baseline": "Baseline",
            "dflash_n4": "DFlash-4",
            "dspark_n7": "DSpark-7",
            "dspark_n7_dynamic": "DSpark + threshold",
            "dspark_n7_stop": "DSpark + shutoff",
            "dspark_n7_adaptive": "DSpark + combined",
        }
        lines = [
            "\\begin{tabular}{lrrrr}",
            "\\toprule",
            "Method & Decode tok/s & Speedup [95\\% CI] & Completion tok/s & Proposed \\\\",
            "\\midrule",
        ]
        for method in METHODS:
            cur = summary["methods"][method]
            if method == "baseline":
                speedup = "1.000"
            else:
                speed = cur["speedup_vs_baseline"]
                speedup = f"{speed['geomean']:.3f} [{speed['ci_low']:.3f}, {speed['ci_high']:.3f}]"
            proposed = "--" if method == "baseline" else f"{cur['draft_tokens']:,}"
            lines.append(
                f"{labels[method]} & {cur['decode_tps_mean']:.2f} & {speedup} & "
                f"{cur['completion_tps_mean']:.2f} & {proposed} \\\\"
            )
        lines.extend(["\\bottomrule", "\\end{tabular}"])
        args.table.parent.mkdir(parents=True, exist_ok=True)
        args.table.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.figure:
        import matplotlib.pyplot as plt

        labels = {
            "baseline": "Baseline",
            "dflash_n4": "DFlash-4",
            "dspark_n7": "DSpark-7",
            "dspark_n7_dynamic": "DSpark + threshold",
            "dspark_n7_stop": "DSpark + shutoff",
            "dspark_n7_adaptive": "DSpark + combined",
        }
        styles = {
            "baseline": ("#454b66", "o", "-"),
            "dflash_n4": ("#43aa8b", "s", "-"),
            "dspark_n7": ("#e09f3e", "^", "-"),
            "dspark_n7_dynamic": ("#9c4dcc", "D", "-"),
            "dspark_n7_stop": ("#577590", "v", "--"),
            "dspark_n7_adaptive": ("#c44536", "P", "--"),
        }
        contexts = [512, 2048, 4096, 6144]
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        for method in METHODS:
            color, marker, linestyle = styles[method]
            values = [summary["context_decode_tps"][method][str(context)] for context in contexts]
            ax.plot(contexts, values, label=labels[method], color=color, marker=marker, linestyle=linestyle, linewidth=1.8)
        ax.set_xlabel("Raw prompt tokens")
        ax.set_ylabel("Decode tokens/s")
        ax.set_xticks(contexts, ["512", "2,048", "4,096", "6,144"])
        ax.grid(axis="y", alpha=0.25)
        ax.legend(ncol=2, fontsize=8, frameon=False)
        fig.tight_layout()
        args.figure.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.figure)
        plt.close(fig)
    print(text, end="")


if __name__ == "__main__":
    main()
