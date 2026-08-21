# Model Provenance

All revisions and SHA-256 values below are immutable identifiers for the files used in the benchmark.

| Role | Hugging Face source | Revision | Local file | SHA-256 |
| --- | --- | --- | --- | --- |
| Target | `Qwen/Qwen3-8B-GGUF` | `7c41481f57cb95916b40956ab2f0b139b296d974` | `models/target/Qwen3-8B-Q4_K_M.gguf` | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |
| EAGLE-3 | `williamliao/Qwen3-8B-EAGLE3-Speculator-GGUF` | `44480ff4ea6330788818f7f5fc9a69b326dc4c06` | `models/eagle3/Qwen3-8B-speculator.eagle3-F16.gguf` | `d6cf1f3cf29e9cd72c02fb11f989f5192f2b24e142741fdc2de8cd590140f2f2` |
| DFlash | `AtomicChat/Qwen3-8B-DFlash-GGUF` | `788b1a553f50979b99fecf6abe7a4c3fd88a8d89` | `models/dflash/Qwen3-8B-DFlash.Q8_0.gguf` | `5be4f6b1bfd5c2c1aa753d4c03e30700114654fefbbf29f02257ef37adb00bf0` |
| DSpark source | `deepseek-ai/dspark_qwen3_8b_block7` | `03326e5043815da1f81b109078b2889737c26017` | Converted to `models/dspark-deepspec-bf16.gguf` | `2ae4373d73f17fe5a8a7e44da2a3b0c62b986693d1c404c0a769cb6a33bba9e7` |

The DSpark SafeTensors checkpoint was converted to BF16 GGUF with `convert_hf_to_gguf.py --outtype bf16`. The output checksum above is authoritative. The initial study used `llama.cpp` b10241, commit `9bd4c09ea`. The adaptive extension uses instrumented `llama.cpp` b10248, commit `e8e06f78e`. The executable `build-study/bin/llama-server` has SHA-256 `5f6fc026ddb095d67f7b33947a3c5bc099a69ac3fb339514fc9a172d5d9f9ddc`; its dynamically linked adaptive components are `libllama-common.so` (`7bcd0d851d423967af81535bc96b33cae0f8147ead6088bfd1c30809e04c6527`) and `libllama-server-impl.so` (`108652e7511f53ebff539cb255d19ccb04500d899ea33dec678138611932a59b`). The rebuildable source delta is `telemetry.patch`, SHA-256 `fb0a90027c723d30db0cc6ccdc5b40659295bb09bf1853dc328e3fa78548e208`.
