#!/usr/bin/env python3
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PURPLE = "#6D4AA2"
ORANGE = "#D17B2F"
NAVY = "#214A6B"
TEAL = "#2A7F75"
GRAY = "#5C6670"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Liberation Serif", "DejaVu Serif"],
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save(fig: plt.Figure, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".jpg"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def workflow(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 2.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.2, 1.0, 1.7, 1.0, "Target model\nlast verified token", NAVY),
        (2.4, 1.0, 1.7, 1.0, "DSpark\n7 parallel drafts", PURPLE),
        (4.6, 1.0, 1.7, 1.0, "Confidence rule\n0.40 code / 0.20 string", ORANGE),
        (6.8, 1.0, 1.3, 1.0, "Keep longest\nallowed prefix", TEAL),
        (8.6, 1.0, 1.2, 1.0, "Target\nverification", NAVY),
    ]
    for x, y, width, height, text, color in boxes:
        patch = FancyBboxPatch(
            (x, y), width, height, boxstyle="round,pad=0.03,rounding_size=0.06", facecolor=color, edgecolor="none"
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height / 2, text, color="white", ha="center", va="center", fontsize=9)
    for start, end in ((1.9, 2.4), (4.1, 4.6), (6.3, 6.8), (8.1, 8.6)):
        ax.add_patch(FancyArrowPatch((start, 1.5), (end, 1.5), arrowstyle="-|>", mutation_scale=13, color=GRAY))
    ax.text(5.45, 2.35, "Generated-output lexer chooses the threshold before each block", ha="center", color=GRAY)
    ax.text(5.45, 0.55, "The complete draft block is still computed; truncation reduces target verification work", ha="center", color=GRAY)
    save(fig, output)


def throughput(rows: list[dict], summary: dict, quality: dict, output: Path) -> None:
    indexed = {(row["method"], row["repeat"], row["prompt_id"]): row for row in rows}
    source_logs = defaultdict(list)
    for row in rows:
        if row["method"] != "dspark_n7_dynamic":
            continue
        reference = indexed[("dspark_n7", row["repeat"], row["prompt_id"])]
        source_logs[row["base_prompt_id"]].append(
            math.log(row["timings"]["predicted_per_second"] / reference["timings"]["predicted_per_second"])
        )
    source_ratios = [math.exp(sum(values) / len(values)) for _, values in sorted(source_logs.items())]
    contexts = [512, 2048, 4096, 6144]
    context_ratios = [
        summary["context_decode_tps"]["dspark_n7_dynamic"][str(context)]
        / summary["context_decode_tps"]["dspark_n7"][str(context)]
        for context in contexts
    ]
    pooled = summary["methods"]["dspark_n7_dynamic"]["speedup_vs_dspark"]
    short = quality["methods"]["dspark_n7_dynamic"]["speedup_vs_dspark_n7"]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.5), gridspec_kw={"width_ratios": [1.0, 1.25]})
    ax = axes[0]
    ax.scatter(source_ratios, range(1, 7), color=PURPLE, s=35, label="Source example")
    ax.errorbar(
        pooled["geomean"],
        0,
        xerr=[[pooled["geomean"] - pooled["ci_low"]], [pooled["ci_high"] - pooled["geomean"]]],
        fmt="D",
        color=ORANGE,
        capsize=4,
        label="Pooled [95% CI]",
    )
    ax.axvline(1, color="#222222", linewidth=1)
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6], ["Pooled", "S1", "S2", "S3", "S4", "S5", "S6"])
    ax.set_xlabel("Dynamic / fixed DSpark decode throughput")
    ax.set_title("a. Independent source clusters")
    ax.grid(axis="x", alpha=0.25)

    ax = axes[1]
    x = list(range(len(contexts)))
    ax.plot(x, context_ratios, color=PURPLE, marker="o", linewidth=2, label="Long-context holdout")
    ax.axhline(1, color="#222222", linewidth=1)
    ax.scatter([4.2], [short["geomean"]], color=GRAY, marker="s", s=45, label="HumanEval short functions")
    ax.set_xticks([*x, 4.2], ["512", "2K", "4K", "6K", "Short\nfunctions"])
    ax.set_ylabel("Dynamic / fixed DSpark")
    ax.set_xlabel("Raw prompt length or workload")
    ax.set_title("b. The effect depends on workload")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    save(fig, output)


def efficiency(summary: dict, quality: dict, output: Path) -> None:
    fixed = summary["methods"]["dspark_n7"]
    dynamic = summary["methods"]["dspark_n7_dynamic"]
    methods = ["Target only", "Fixed DSpark", "Dynamic DSpark"]
    passed = [
        quality["methods"]["baseline"]["passed"],
        quality["methods"]["dspark_n7"]["passed"],
        quality["methods"]["dspark_n7_dynamic"]["passed"],
    ]

    fig, axes = plt.subplots(1, 2, figsize=(8.7, 3.5))
    ax = axes[0]
    x = [0, 1]
    width = 0.34
    ax.bar([value - width / 2 for value in x], [fixed["draft_tokens"], fixed["accepted_tokens"]], width, color=ORANGE, label="Fixed")
    ax.bar([value + width / 2 for value in x], [dynamic["draft_tokens"], dynamic["accepted_tokens"]], width, color=PURPLE, label="Dynamic")
    ax.set_xticks(x, ["Proposed", "Accepted"])
    ax.set_ylabel("Tokens across 72 requests")
    ax.set_title("a. Long-context draft efficiency")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    ax.bar(methods, passed, color=[NAVY, ORANGE, PURPLE])
    ax.set_ylim(115, 135)
    ax.set_ylabel("HumanEval tests passed (of 164)")
    ax.set_title("b. Executable code quality")
    for index, value in enumerate(passed):
        ax.text(index, value + 0.5, str(value), ha="center")
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    setup()
    rows = load_jsonl(args.holdout)
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    quality = json.loads(args.quality.read_text(encoding="utf-8"))
    workflow(args.output_dir / "figure_1_workflow")
    throughput(rows, summary, quality, args.output_dir / "figure_2_throughput")
    efficiency(summary, quality, args.output_dir / "figure_3_efficiency_quality")


if __name__ == "__main__":
    main()
