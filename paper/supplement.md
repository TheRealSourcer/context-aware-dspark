# Supplementary Information

## S1. Frozen protocol

The complete frozen protocol is distributed as `protocols/jhss-technical-note.md`. It defines `base_prompt_id` as the independent cluster, fixed DSpark as the confirmatory reference, dynamic DSpark as the intervention, and decode throughput as the primary outcome. Thresholds were fixed at 0.40 outside generated string literals and 0.20 inside generated string literals before holdout evaluation.

## S2. Long-context validation

The holdout contains 432 unique cells: six methods, three repeats, and 24 prompt variants. The 24 variants comprise six source-example IDs and four context lengths (512, 2,048, 4,096, and 6,144 raw tokens). Every source contains all four lengths. Every archived request reports a sampled peak memory clock of 456 MHz. The validator rejects missing cells, duplicate cells, inconsistent prompt metadata, incorrect source/context structure, and mixed memory-clock states.

### Table S1. Long-context aggregate results

| Method | Requests | Mean decode tok/s | Paired speedup vs target [95% CI] | Proposed | Accepted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Target only | 72 | 39.02 | 1.000 | 0 | 0 |
| DFlash-4 | 72 | 84.16 | 2.087 [1.902, 2.283] | 37,188 | 25,767 |
| Fixed DSpark-7 | 72 | 82.66 | 2.053 [1.850, 2.271] | 45,876 | 28,497 |
| Dynamic DSpark-7 | 72 | 84.12 | 2.099 [1.899, 2.302] | 40,248 | 28,449 |
| Shutoff-only DSpark | 72 | 82.68 | 2.054 [1.851, 2.272] | 45,876 | 28,497 |
| Combined DSpark | 72 | 84.10 | 2.099 [1.898, 2.302] | 40,248 | 28,449 |

The direct dynamic-versus-fixed DSpark ratio is 1.0224 [1.0104, 1.0415].

## S3. HumanEval evaluation

HumanEvalPack was materialized from `bigcode/humanevalpack`, Python split, revision `9a41762f73a8cb23bb5811b73d5aab164efcf378`. The generated prompt file has SHA-256 `a442453118dd0d44e751afc282c2cf3d3e303a05c60d54bc1856bf48e65f7fc6`. The test bundle has SHA-256 `806f71af16154c1a92ee293053357307cc3cab43b23f4815e42ba4d7f5bcc853`.

The quality result uses repeat zero as one pass@1 completion per task. Two additional repeats provide timing measurements but are not treated as additional independent quality tasks.

### Table S2. HumanEval outcomes

| Method | Passed | Test failures | Runtime errors | Exact outputs vs target | Mean decode tok/s across 3 repeats |
| --- | ---: | ---: | ---: | ---: | ---: |
| Target only | 129/164 | 27 | 8 | 164/164 | 54.31 |
| Fixed DSpark | 130/164 | 26 | 8 | 151/164 | 123.52 |
| Dynamic DSpark | 130/164 | 26 | 8 | 152/164 | 122.81 |

Dynamic and fixed DSpark were textually identical on 163 of 164 quality-scored tasks and had identical pass/fail outcomes on all 164. Their three-repeat paired throughput ratio was 0.9943 [0.9927, 0.9959].

## S4. Sandbox

Generated Python was executed with Podman image `docker.io/library/python@sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5`. Each case ran without network access, with a read-only root filesystem, no Linux capabilities, `no-new-privileges`, one CPU, 512 MiB memory, at most 32 processes, and an external timeout. Only the generated candidate and audited official test were mounted read-only.

## S5. Artifact hashes

The public reproducibility artifact is identified by DOI https://doi.org/10.5281/zenodo.22049029.

| Artifact | SHA-256 |
| --- | --- |
| Long-context holdout raw data | `790133955cb28deb6b3977f167471b8220e675c150527a71996c2163e92b767b` |
| HumanEval generations, 3 repeats | `d0be33b3bf3504a3ae1b296e502d795de5790a1feb6748d0e35d473b9682b3fd` |
| HumanEval test bundle | `806f71af16154c1a92ee293053357307cc3cab43b23f4815e42ba4d7f5bcc853` |
| Target GGUF | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| DSpark GGUF | `2ae4373d73f17fe5a8a7e44da2a3b0c62b986693d1c404c0a769cb6a33bba9e7` |
| Runtime patch | `fb0a90027c723d30db0cc6ccdc5b40659295bb09bf1853dc328e3fa78548e208` |

## S6. Data-rights boundary

HumanEvalPack declares an MIT license. SPEED-Bench uses the NVIDIA Evaluation Dataset License and incorporates source-code examples with additional underlying rights. The public artifact therefore includes HumanEval materials and rights-safe aggregate or metric-only long-context data, but not full long-context prompts or generated responses. The withheld files remain identified by immutable hashes so an authorized reviewer can verify them on request.
