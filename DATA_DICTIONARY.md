# Data Dictionary

## Long-Context Metrics

`data/long-context-metrics.jsonl` contains one JSON object per request. It is derived from the withheld raw holdout by removing the `prompt` and generated `content` fields.

| Field | Meaning |
| --- | --- |
| `prompt_id` | Identifier for one source and context-length variant. |
| `base_prompt_id` | Pseudonymous source-example cluster used as the bootstrap unit. |
| `source_id` | Identifier of the source row in the pinned benchmark. |
| `source` | Public dataset source locator. |
| `benchmark` | Benchmark name. |
| `domain` | Workload domain label. |
| `context_bin` | Requested raw prompt-token length. |
| `method` | Runtime method configuration. |
| `repeat` | Technical repeat number. |
| `position` | Position in the deterministically shuffled run order. |
| `max_tokens` | Maximum completion-token count. |
| `wall_seconds` | Client-observed request duration. |
| `content_sha256` | SHA-256 of the withheld generated text. |
| `finish_reason` | Server finish reason. |
| `usage` | Prompt, completion, and total token counts reported by the server. |
| `timings` | Server timing and speculative-decoding telemetry. |
| `gpu` | Device sensor values sampled after the request. |
| `gpu_peak` | Peak device sensor values sampled during the request. |
| `warmup_count` | Number of warmup requests before the method run. |

The metric-only file must contain 432 unique `(method, repeat, prompt_id)` cells, six source clusters, four context lengths, three repeats, and six methods. The validator in `scripts/analyze_adaptive_holdout.py` enforces this design.

## HumanEval Generations

`data/humaneval-python-generations.jsonl` contains 1,476 rows: 164 tasks, three methods, and three repeats. The schema is the benchmark-runner schema documented above plus `dataset_revision`. Unlike the long-context release, prompts and generated text are included because the source benchmark declares the MIT License.

## HumanEval Evaluations

`data/humaneval-python-evaluated.jsonl` contains 492 rows: one quality-scored completion for each of 164 tasks and three methods. `passed` is true only when the generated candidate completed the official tests with exit status zero in the isolated container. `status` distinguishes passing, test-failure, runtime, syntax, timeout, and extraction outcomes. Diagnostic trace text is excluded from the public file because it is not needed to reproduce aggregate results.
