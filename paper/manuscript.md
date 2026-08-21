# Context-Dependent Effects of Dynamic Confidence Thresholds for Speculative Decoding on a Consumer GPU

**Vicente Bertolotti**

Green Hope High School, 2500 Carpenter Upchurch Road, Cary, NC 27519, USA

Corresponding author: Vicente Bertolotti, cuentavicen@gmail.com

## Abstract

Speculative decoding can accelerate a large language model by asking a smaller draft model to propose several tokens and checking them in one target-model pass. The best number of proposals depends on both proposal accuracy and verification cost. This technical note tested whether a simple generated-output rule could improve DSpark speculative decoding on consumer hardware. The rule used a confidence threshold of 0.40 outside string literals and 0.20 inside string literals. Thresholds were selected on six coding examples and frozen before evaluation on six different source-example IDs, each represented at four prompt lengths. The resulting holdout contained 432 requests across six methods and three technical repeats on Qwen3-8B Q4_K_M and an AMD Radeon RX 6800. Dynamic thresholds improved paired decode throughput over fixed DSpark by 1.0224x (source-cluster bootstrap 95% interval, 1.0104-1.0415). They reduced proposed draft tokens by 12.3%, from 45,876 to 40,248, while accepted draft tokens decreased by 0.17%. A separate 164-task HumanEval experiment found identical fixed-versus-dynamic pass/fail outcomes: both passed 130 tasks, and 163 of 164 generated outputs were textually identical. However, dynamic thresholds were slightly slower on these short functions (0.9943x fixed DSpark, 95% interval 0.9927-0.9959). The rule therefore produced a small, measurable benefit on the tested long-context workload but not a universal speedup. The results support workload-specific validation of speculative scheduling policies and do not generalize beyond the tested model, runtime, and GPU.

**Keywords:** speculative decoding; large language models; consumer GPU; inference optimization; DSpark; confidence calibration; adaptive scheduling; Vulkan; Qwen3; reproducible benchmarking

## Introduction

Large language models generate text one token at a time. Each new token normally requires another target-model forward pass, which makes generation latency grow with output length. Speculative decoding reduces this serial cost by using a smaller draft model to propose several tokens and then verifying those proposals together with the target model (1, 2). Correct draft tokens are accepted, while the first rejected position is replaced using the target model.

The speed of speculative decoding is determined by more than draft accuracy. A longer draft can create more accepted tokens per target pass, but it also increases draft computation and target verification work. A policy that is effective for one prompt length, workload, model, or device can therefore be ineffective for another. This concern is especially important on consumer GPUs, where memory capacity and kernel behavior differ from the data-center accelerators used in many inference studies.

DFlash predicts a complete block of draft tokens in parallel rather than generating the draft autoregressively (3). DSpark extends this design with a low-rank sequential correction and a confidence prediction for each draft position (4). Its runtime can stop the verified draft prefix when confidence falls below a threshold. In the implementation evaluated here, the complete seven-position DSpark graph is still computed, so thresholding reduces target verification work rather than eliminating the initial draft pass.

Generated code contains different local token patterns. Tokens inside quoted strings can be highly repetitive or locally predictable, while syntax outside strings can impose different constraints. This study therefore tested a small runtime intervention: use one frozen confidence threshold outside generated string literals and a lower threshold inside them. The intervention does not train or modify model weights.

The primary research question was: on an AMD Radeon RX 6800 running Qwen3-8B, does selecting DSpark's confidence threshold from generated string-literal state reduce speculative work and improve paired decode throughput over a fixed threshold on source-example-ID-disjoint long-context coding prompts? A separate executable-code experiment tested whether fixed and dynamic DSpark produced different HumanEval task outcomes. All claims are limited to this controlled case study.

[FIGURE 1 NEAR HERE]

## Materials and Methods

### Hardware and software

Experiments used an AMD Ryzen 5 5600X processor, 32 GiB system memory, and an AMD Radeon RX 6800 with 16 GiB video memory. The target was the official Qwen3-8B Q4_K_M GGUF checkpoint (5). DSpark used the converted BF16 `deepseek-ai/dspark_qwen3_8b_block7` checkpoint. The adaptive extension ran on `llama.cpp` release 10248, commit `e8e06f78e`, with a published source patch (6). Target and draft layers ran through Vulkan with flash attention, an 8,192-token context, 512-token batch and microbatch sizes, and one concurrent request.

Requests used Qwen3 non-thinking mode, temperature zero, a fixed seed, and a 512-token output limit. The long-context holdout reported a sampled peak memory clock of 456 MHz for every request. The later HumanEval experiment reported 673 MHz for every request. Comparisons were made only within each experiment; absolute throughput was not compared between clock states.

### Fixed and dynamic confidence policies

DSpark proposed up to seven tokens per block. Fixed DSpark used the checkpoint's standard draft path without an added confidence threshold. The dynamic policy selected a threshold before each block using a lightweight lexer over generated output. The threshold was 0.40 outside string literals and 0.20 inside string literals. Markdown triple-backtick fences were not treated as language strings. The lexer was deliberately simple and was not a complete parser for every programming language.

For confidence values c1 through c7 and threshold t, the scheduler retained the longest prefix in which each included confidence was at least t. Empty proposals were retained in telemetry. The full seven-position draft graph was evaluated before truncation, so the policy could save verification work but not the complete draft computation. Figure 1 summarizes this sequence.

### Calibration and long-context holdout

The two thresholds were selected using six SPEED-Bench coding source examples (7). Each example was cropped to 512, 2,048, 4,096, and 6,144 raw tokens, producing 24 calibration prompts. Threshold selection occurred only on this calibration set.

The holdout used six different SPEED-Bench source-example IDs at the same four prompt lengths. There was no source ID overlap between calibration and holdout. The context variants preserved an instruction prefix and an immediate completion suffix, creating controlled lengths but also an artificial splice. Answer-padding text was removed before tokenization. The 24 holdout prompts were evaluated with target-only decoding, DFlash-4, fixed DSpark-7, dynamic-threshold DSpark, terminal-shutoff DSpark, and the combined policy. Three deterministically shuffled repeats produced 432 requests. The confirmatory comparison used the 144 fixed and dynamic DSpark requests.

### Executable-code evaluation

Quality was evaluated separately on all 164 Python HumanEvalPack tasks at immutable revision `9a41762f73a8cb23bb5811b73d5aab164efcf378` (8, 9). Target-only, fixed DSpark, and dynamic DSpark generated one quality-scored completion per task using the same temperature-zero policy. Two additional repeats were collected for timing. The evaluator required one unambiguous Python code block containing the expected function definition.

Generated code was executed with the official bundled tests in a rootless Podman container pinned to `python@sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5`. The container had no network, a read-only root filesystem, dropped Linux capabilities, a 512 MiB memory limit, a process limit of 32, and a wall-time limit. Outcomes were classified as pass, test failure, runtime error, syntax error, timeout, or extraction failure.

### Statistics

The primary outcome was the geometric mean paired ratio of server-reported decode tokens per second. A log throughput ratio was calculated for matching dynamic and fixed DSpark requests. Ratios were averaged across three repeats and four context variants within each source example. A fixed-seed percentile bootstrap then resampled the six independent `base_prompt_id` clusters 10,000 times to form a 95% interval (10). The source example, not each crop or repeat, was the resampling unit.

Secondary outcomes included proposed and accepted draft tokens, client-observed completion throughput, output-hash identity, and completion-token-count identity. HumanEval accuracy was the number of tasks passing all tests divided by 164. Paired quality differences counted tasks gained or lost relative to the reference. HumanEval timing ratios averaged three repeats within each task and bootstrapped tasks. These intervals describe the tested task set and do not account for all possible system-level variation.

The protocol, thresholds, primary comparison, cluster unit, and exclusion rules were frozen in `study/protocols/jhss-technical-note.md` before the HumanEval experiment.

## Results

### Long-context throughput

Fixed DSpark averaged 82.66 decode tokens/s across the holdout. Dynamic DSpark averaged 84.12 decode tokens/s. The paired geometric throughput ratio was 1.0224, with a source-cluster bootstrap 95% interval of 1.0104 to 1.0415. Against target-only decoding, fixed and dynamic DSpark reached paired geometric ratios of 2.053 and 2.099, respectively, but those broader speedups were contextual rather than the primary test.

The dynamic policy reduced proposed draft tokens from 45,876 to 40,248, a 12.3% decrease. Accepted draft tokens changed from 28,497 to 28,449, a 0.17% decrease in aggregate. Mean client-observed completion throughput increased from 53.93 to 54.51 tokens/s, which was smaller than the decode-only improvement because it included prompt processing and HTTP overhead.

All six independent source clusters had a dynamic-to-fixed ratio above 1.0. Descriptive ratios calculated from arithmetic mean throughput were 1.017, 1.004, 1.019, and 1.040 at 512, 2,048, 4,096, and 6,144 raw prompt tokens, respectively. The context pattern was descriptive because each point contained only six source examples.

[FIGURE 2 NEAR HERE]

### Executable code and short-function timing

Target-only decoding passed 129 of 164 HumanEval tasks (78.7%). Fixed DSpark and dynamic DSpark each passed 130 tasks (79.3%). Dynamic and fixed DSpark had identical pass/fail outcomes on all 164 tasks. Their generated text was exactly identical for 163 tasks; the one textual difference did not change test status. Relative to target-only decoding, each DSpark method gained one passing task and lost none, but this single difference is consistent with quantized numerical trajectory changes and is not evidence that speculative decoding improves model quality.

On the three-repeat short-function timing experiment, dynamic DSpark reached 0.9943x fixed DSpark throughput (task-cluster bootstrap 95% interval, 0.9927-0.9959). It proposed 73,829 tokens instead of 74,165 and accepted 61,816 instead of 61,843 across all repeats. The policy therefore had no measured quality disadvantage but also no speed advantage on this short workload.

[FIGURE 3 NEAR HERE]

### Exploratory terminal shutoff

The runtime also included a request-local terminal shutoff based on rolling accepted-prefix length. It never activated in the 72 independent holdout requests assigned to that policy, and its outputs matched fixed DSpark in all 72 cases. It reduced two severe regressions observed during calibration, but those examples were used to choose the rule. Terminal shutoff is therefore reported as an exploratory implementation result, not an independently demonstrated speedup.

## Discussion

The dynamic policy produced a statistically detectable but practically small long-context improvement. Its main measurable action was avoiding 12.3% of proposed verification tokens while preserving nearly the same aggregate number of accepted draft tokens. The benefit increased descriptively at the longest tested context. This pattern is consistent with verification becoming more expensive as context grows, although the experiment did not isolate every component of cycle latency.

The HumanEval result prevents a broader claim. Dynamic thresholds were slightly slower than fixed DSpark on short standalone functions even though executable outcomes were identical. A fixed policy should therefore not be enabled solely because it improves one long-context benchmark. A production scheduler would need to consider prompt length, device behavior, draft cost, verification cost, and recent acceptance.

DFlash 2 was released after these experiments. It adds a candidate selector for adjacent-token coherence and dynamic convolution to reduce suffix decay (11). Those changes overlap DSpark's main architectural correction and reduce the motivation for a new hybrid model. They do not remove the systems question studied here: even a stronger drafter can have a hardware- and workload-dependent optimal verification width. Future work should test weight-free adaptive width or disable policies on DFlash 2 rather than train another DSpark-style correction head.

The study also illustrates why output identity is not a sufficient quality measure. Although speculative verification preserves the target distribution in exact arithmetic, quantized GPU kernels can follow different greedy trajectories when verification changes batch shape. In the long-context holdout, dynamic and fixed DSpark were textually identical in 54 of 72 paired requests and had the same completion-token count in 66 of 72. HumanEval tests provided a more meaningful task-level check and found no fixed-versus-dynamic pass/fail differences.

### Limitations

The long-context holdout contained only six independent source examples. Four prompt lengths from each example and three repeats improved measurement precision but did not create 72 independent workloads. The crop procedure introduced an artificial discontinuity. Most long-context generations reached the 512-token output cap. Results covered one consumer GPU, one quantized target, one BF16 draft, one Vulkan runtime, and concurrency one. The simple lexer examined generated output rather than raw prompt state and was not language-complete.

The two experiments operated at different sampled memory clocks and must not be compared by absolute throughput. HumanEval quality used one completion per task; temperature-zero outputs still varied for a small number of tasks across timing repeats. The HumanEval timing interval resampled tasks but did not represent other models, prompts, devices, or server loads. Terminal shutoff did not activate on independent holdout data. Finally, DFlash 2 now supersedes part of DSpark's architectural motivation, so the most durable conclusion concerns workload-specific runtime evaluation rather than a particular draft model.

## Conclusion

On the tested RX 6800 long-context workload, generated-string-aware confidence thresholds improved DSpark decode throughput by 2.24% and reduced draft proposals by 12.3%, with a source-cluster interval excluding parity. The same rule did not improve short HumanEval throughput, while fixed and dynamic DSpark passed exactly the same 130 of 164 tasks. Dynamic confidence thresholding was therefore useful in a specific long-context setting but was not a universal optimization. Speculative decoding policies should be evaluated on the intended workload and hardware, using independent workload clusters and executable quality checks where possible.

## Author Contributions

Vicente Bertolotti: conceptualization, methodology, investigation, software review, data curation, validation, visualization review, and writing - review and editing. No other person contributed sufficiently to qualify for authorship.

## Generative-AI Disclosure

OpenAI GPT-5.6 Sol, accessed through OpenCode, assisted with literature discovery, code inspection, implementation suggestions, analysis scripting, debugging, figure preparation, and manuscript drafting and editing. No AI system is an author. The listed human author is responsible for understanding the released implementation and for verifying all code, citations, analyses, and claims before submission.

## Funding and Competing Interests

This research received no external funding. Computation used personal or family-owned hardware, and any publication expenses are paid from personal or family funds. The author declares no competing interests.

## Ethics Statement

The study used public benchmark data, software, and machine-generated outputs. It involved no human participants, private personal data, animals, or clinical material. HumanEval tests were executed in a network-isolated, resource-limited container.

## Code and Data Availability

Analysis scripts, configurations, the runtime patch, aggregate results, a rights-safe metric release, checksums, and reproduction instructions are archived at https://github.com/TheRealSourcer/context-aware-dspark and https://doi.org/10.5281/zenodo.22049029. HumanEvalPack prompts and tests are MIT licensed and are identified by immutable revision. Raw SPEED-Bench-derived prompts and model outputs are withheld from the public artifact pending row-level verification of underlying source-code redistribution rights; source identifiers, immutable dataset revisions, hashes, and retrieval scripts are provided instead.

## References

**1.** Y. Leviathan, M. Kalman, Y. Matias. Fast inference from transformers via speculative decoding. *Proceedings of the 40th International Conference on Machine Learning*. Vol. 202, pg. 19274-19286, 2023, https://proceedings.mlr.press/v202/leviathan23a.html.

**2.** C. Chen, S. Borgeaud, G. Irving, J.-B. Lespiau, L. Sifre, J. Jumper. Accelerating large language model decoding with speculative sampling. *arXiv preprint arXiv:2302.01318*, 2023, https://doi.org/10.48550/arXiv.2302.01318.

**3.** J. Chen, Y. Liang, Z. Liu. DFlash: block diffusion for flash speculative decoding. *arXiv preprint arXiv:2602.06036*, 2026, https://doi.org/10.48550/arXiv.2602.06036.

**4.** X. Cheng, X. Yu, C. Shao, J. Li, Y. Xiong, Y. Qian, et al. DSpark: confidence-scheduled speculative decoding with semi-autoregressive generation. *arXiv preprint arXiv:2607.05147*, 2026, https://doi.org/10.48550/arXiv.2607.05147.

**5.** A. Yang, A. Li, B. Yang, B. Zhang, B. Hui, B. Zheng, et al. Qwen3 technical report. *arXiv preprint arXiv:2505.09388*, 2025, https://doi.org/10.48550/arXiv.2505.09388.

**6.** The ggml authors. llama.cpp, release 10248, commit e8e06f78e. Software repository, 2026, https://github.com/ggml-org/llama.cpp.

**7.** T. Abramovich, M. Ashkenazi, I. Putterman, B. Chislett, T. Mitra, B. D. Rouhani, et al. SPEED-Bench: a unified and diverse benchmark for speculative decoding. *arXiv preprint arXiv:2604.09557*, 2026, https://doi.org/10.48550/arXiv.2604.09557.

**8.** M. Chen, J. Tworek, H. Jun, Q. Yuan, H. Ponde de Oliveira Pinto, J. Kaplan, et al. Evaluating large language models trained on code. *arXiv preprint arXiv:2107.03374*, 2021, https://doi.org/10.48550/arXiv.2107.03374.

**9.** N. Muennighoff, Q. Liu, A. Zebaze, Q. Zheng, B. Hui, T. Y. Zhuo, et al. OctoPack: instruction tuning code large language models. *arXiv preprint arXiv:2308.07124*, 2023, https://doi.org/10.48550/arXiv.2308.07124.

**10.** B. Efron. Bootstrap methods: another look at the jackknife. *The Annals of Statistics*. Vol. 7, pg. 1-26, 1979, https://doi.org/10.1214/aos/1176344552.

**11.** Inco AI. DFlash 2: keep drafting parallel. Inco AI technical blog, 2026, https://inco.ai/blog/dflash2/.
