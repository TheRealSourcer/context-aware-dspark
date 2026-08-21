# Context-Aware DSpark Reproducibility Artifact

This capsule supports the technical note "Context-Dependent Effects of Dynamic Confidence Thresholds for Speculative Decoding on a Consumer GPU." It contains the analysis code, runtime source patch, configuration, frozen protocol, model provenance, publication sources, exact HumanEvalPack materials, and a metric-only release of the long-context measurements.

Repository: https://github.com/TheRealSourcer/context-aware-dspark

Reserved software DOI: https://doi.org/10.5281/zenodo.22049029

## Scope

The confirmatory result compares fixed DSpark-7 with a dynamic policy that uses a confidence threshold of 0.40 outside generated string literals and 0.20 inside them. The tested system used Qwen3-8B Q4_K_M, a BF16 DSpark draft model, llama.cpp b10248, Vulkan, concurrency one, and an AMD Radeon RX 6800.

This is a case study of one model, runtime, device, and workload. The artifact does not support claims of a universal speedup.

## Contents

- `config/extended-methods.json`: exact server and method arguments.
- `data/long-context-metrics.jsonl`: 432 long-context measurement rows with prompts and generated text removed.
- `data/humaneval-python-prompts.jsonl`: 164 MIT-licensed HumanEvalPack prompts.
- `data/humaneval-python-tests.jsonl`: corresponding official tests.
- `data/humaneval-python-generations.jsonl`: 1,476 HumanEval generation and timing rows.
- `data/humaneval-python-evaluated.jsonl`: one quality outcome per method and task.
- `results/adaptive-summary.json`: archived long-context summary.
- `results/humaneval-python-summary.json`: archived executable-quality and timing summary.
- `scripts/`: benchmark, validation, evaluation, figure, and package-building code.
- `protocols/jhss-technical-note.md`: frozen confirmatory protocol.
- `telemetry.patch`: source delta against llama.cpp b10248 (`e8e06f78e`).
- `MODELS.md`: immutable model revisions and file hashes.
- `paper/`: manuscript and supplement sources plus publication figures.
- `MANIFEST.json` and `SHA256SUMS`: file inventory and integrity checks.

## Environment

Python 3.12 was used. Install the pinned analysis dependencies in an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The HumanEval evaluator additionally requires rootless Podman and the pinned image named in `results/humaneval-python-summary.json`. Generated code is untrusted. Do not execute it directly on the host.

## Reproduce The Long-Context Analysis

Run from this artifact's root:

```sh
.venv/bin/python scripts/analyze_adaptive_holdout.py \
  data/long-context-metrics.jsonl \
  --output reproduced/adaptive-summary.json \
  --table reproduced/adaptive-table.tex \
  --figure reproduced/context-throughput.pdf
```

The expected direct dynamic-versus-fixed geometric throughput ratio is `1.022414236487257`, with a source-cluster bootstrap 95% interval of `[1.0103738469671537, 1.0415173142264702]`.

The reproduced summary will have a different `input` value and input SHA-256 because it analyzes the metric-only release. All statistical and validation fields must match `results/adaptive-summary.json`.

## Reproduce HumanEval Materialization And Analysis

The archived prompt and test files can be regenerated from immutable HumanEvalPack revision `9a41762f73a8cb23bb5811b73d5aab164efcf378`:

```sh
.venv/bin/python scripts/prepare_humaneval_python.py \
  --prompts reproduced/humaneval-python-prompts.jsonl \
  --tests reproduced/humaneval-python-tests.jsonl
sha256sum reproduced/humaneval-python-prompts.jsonl reproduced/humaneval-python-tests.jsonl
```

Expected SHA-256 values are:

```text
a442453118dd0d44e751afc282c2cf3d3e303a05c60d54bc1856bf48e65f7fc6  reproduced/humaneval-python-prompts.jsonl
806f71af16154c1a92ee293053357307cc3cab43b23f4815e42ba4d7f5bcc853  reproduced/humaneval-python-tests.jsonl
```

Recompute statistics from the archived evaluations without executing generated code:

```sh
cp data/humaneval-python-evaluated.jsonl reproduced/humaneval-python-evaluated.jsonl
.venv/bin/python scripts/evaluate_humaneval_python.py \
  data/humaneval-python-generations.jsonl \
  data/humaneval-python-tests.jsonl \
  --output reproduced/humaneval-python-evaluated.jsonl \
  --summary reproduced/humaneval-python-summary.json \
  --reuse-evaluated
```

To rerun the untrusted-code evaluation, omit `--reuse-evaluated` and use a new output path. The script invokes rootless Podman with no network, a read-only root filesystem, dropped capabilities, `no-new-privileges`, one CPU, 512 MiB memory, a 32-process limit, and an external timeout.

## Reproduce Figures

```sh
.venv/bin/python scripts/make_jhss_figures.py \
  --holdout data/long-context-metrics.jsonl \
  --summary results/adaptive-summary.json \
  --quality results/humaneval-python-summary.json \
  --output-dir reproduced/figures
```

## Reproduce Measurements

Measurement reproduction requires the model files and patched llama.cpp build identified in `MODELS.md`. Model weights and binaries are not included. Apply `telemetry.patch` to the pinned llama.cpp revision, build with Vulkan, place the resulting server and models at the paths in `config/extended-methods.json`, and invoke `scripts/benchmark.py` with `--root .` plus the desired prompt, output, log, method, and repeat arguments.

The archived long-context prompts are not distributed. Authorized users must reconstruct them from the pinned SPEED-Bench revision and the study's selection procedure before rerunning that workload. HumanEval can be rerun with the included prompt file.

## Data-Rights Boundary

HumanEvalPack declares the MIT License. Its pinned prompts and tests and the associated model generations are included for exact verification.

SPEED-Bench is governed by the NVIDIA Evaluation Dataset License and contains examples originating from additional source repositories. This capsule therefore excludes every long-context `prompt` and generated `content` value. It retains source identifiers, hashes, timings, token counts, telemetry, and device measurements needed to reproduce the reported statistics. The SHA-256 of the withheld raw holdout is `790133955cb28deb6b3977f167471b8220e675c150527a71996c2163e92b767b`.

See `THIRD_PARTY_NOTICES.md`, `DATA_DICTIONARY.md`, and `RELEASE_CHECKLIST.md` before publication.

## AI Disclosure

Generative AI materially assisted literature discovery, code inspection, implementation suggestions, analysis scripting, debugging, figure preparation, and manuscript drafting and editing. No AI system is an author. The human author must understand and verify the complete artifact before release.
