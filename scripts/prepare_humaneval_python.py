#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

from datasets import load_dataset


DATASET = "bigcode/humanevalpack"
REVISION = "9a41762f73a8cb23bb5811b73d5aab164efcf378"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    args = parser.parse_args()

    dataset = load_dataset(DATASET, "python", split="test", revision=REVISION)
    prompts = []
    tests = []
    for row in dataset:
        prompt = (
            "Complete the Python function below. Return exactly one fenced Python code block "
            "containing the complete implementation, including the supplied imports and function definition. "
            "Do not include an explanation.\n\n"
            + row["prompt"]
        )
        prompt_id = "humaneval-" + row["task_id"].replace("/", "-").lower()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        prompts.append(
            {
                "benchmark": DATASET,
                "dataset_revision": REVISION,
                "domain": "coding_quality",
                "prompt": prompt,
                "prompt_id": prompt_id,
                "source": f"https://huggingface.co/datasets/{DATASET}/tree/{REVISION}",
                "source_id": row["task_id"],
            }
        )
        tests.append(
            {
                "dataset_revision": REVISION,
                "entry_point": row["entry_point"],
                "prompt_id": prompt_id,
                "prompt_sha256": prompt_hash,
                "task_id": row["task_id"],
                "test": row["test"],
            }
        )

    if len(prompts) != 164 or len(tests) != 164:
        raise RuntimeError(f"Expected 164 Python tasks, found {len(prompts)}")
    if len({row["prompt_id"] for row in prompts}) != 164:
        raise RuntimeError("Duplicate HumanEval prompt IDs")

    write_jsonl(args.prompts, prompts)
    write_jsonl(args.tests, tests)
    print(f"wrote {len(prompts)} prompts to {args.prompts}")
    print(f"wrote {len(tests)} tests to {args.tests}")


if __name__ == "__main__":
    main()
