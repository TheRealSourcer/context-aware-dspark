# Frozen Protocol: Context-Aware DSpark Thresholds

Date frozen: 2026-08-21

## Study type

This is a consumer-GPU computer-systems technical note. It tests a small runtime scheduling change on one model, one GPU, and one inference implementation. It does not claim that the result generalizes to other hardware or models.

## Research question

On an AMD Radeon RX 6800 running Qwen3-8B Q4_K_M, does selecting DSpark's confidence threshold according to generated string-literal state reduce speculative work and improve paired decode throughput over a fixed threshold on source-example-ID-disjoint long-context coding prompts?

## Confirmatory comparison

- Reference: `dspark_n7`
- Intervention: `dspark_n7_dynamic`
- Outside-string confidence threshold: 0.40
- Inside-string confidence threshold: 0.20
- Primary dataset: `results/raw/long-context-coding-v4-holdout.jsonl`
- Independent cluster: `base_prompt_id`
- Technical variants within each cluster: 512, 2,048, 4,096, and 6,144 raw prompt tokens
- Technical repeats: three per method and prompt variant

## Outcomes

The primary outcome is the geometric mean paired ratio of server-reported decode tokens per second. Log ratios are averaged across repeats and context variants within each source example. A fixed-seed, 10,000-sample percentile bootstrap resamples the six source examples.

Secondary outcomes are proposed draft tokens, accepted draft tokens, completion throughput, output-hash identity, completion-token-count identity, and throughput by context length.

The study does not use output identity as a quality metric. Quantized verification batch shapes can produce different greedy trajectories. Any code-quality analysis added later must be reported separately and must not change the frozen thresholds or primary analysis.

## Exploratory analyses

- Terminal shutoff is exploratory because it did not activate on the independent holdout.
- DFlash and target-only results provide context but are not part of the confirmatory comparison.
- Context-length interactions are descriptive because there are only six source clusters.

## Exclusions and validity rules

- All 432 expected method, repeat, and prompt cells must be present exactly once.
- The holdout must contain six `base_prompt_id` values, each with all four context variants.
- Every request must report a sampled peak memory clock of 456 MHz for the archived holdout analysis.
- The contaminated v2 long-context datasets and their results are excluded.
- No request or source cluster will be removed based on its measured throughput or output.

## Planned code-quality extension

If an audited HumanEval test bundle is available, target-only, fixed DSpark, and dynamic DSpark will be run with frozen settings and temperature zero. Generated code will be evaluated in a network-isolated, resource-limited sandbox. Correctness estimates and paired differences will be reported with raw numerators and denominators. If an audited test bundle is unavailable, the paper will state that executable quality was not measured rather than substitute an unvalidated proxy.
