# Third-Party Notices

## llama.cpp

The runtime patch is a derivative source delta against llama.cpp release b10248, commit `e8e06f78e`. llama.cpp is distributed under the MIT License. The upstream license is included as `LICENSE-llama.cpp`.

Upstream repository: https://github.com/ggml-org/llama.cpp

## HumanEvalPack

The HumanEvalPack Python prompts and tests were materialized from `bigcode/humanevalpack` revision `9a41762f73a8cb23bb5811b73d5aab164efcf378`. The dataset declares the MIT License.

Dataset: https://huggingface.co/datasets/bigcode/humanevalpack/tree/9a41762f73a8cb23bb5811b73d5aab164efcf378

The model-generated completions are provided solely as research outputs associated with those tasks. They are untrusted code and must be evaluated only in an isolated sandbox.

## SPEED-Bench

The long-context workload was selected from NVIDIA SPEED-Bench revision `487aa718444e816458d1a0a52bfce7a454285cf4`. SPEED-Bench is governed by the NVIDIA Evaluation Dataset License and delegates responsibility for underlying source-dataset terms to the user.

Dataset: https://huggingface.co/datasets/nvidia/SPEED-Bench/tree/487aa718444e816458d1a0a52bfce7a454285cf4

No SPEED-Bench-derived prompt or generated response is included in this capsule. Only identifiers, cryptographic hashes, measurements, telemetry, and aggregates are released.

## Models

Model weights are not redistributed. `MODELS.md` identifies their upstream repositories, immutable revisions, and SHA-256 values. Use of each model remains subject to its upstream license and terms.
