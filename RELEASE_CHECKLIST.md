# Release Checklist

Complete these human release checks before publishing version 1.0.0.

- Confirm the competing-interest statement.
- Confirm that the AI disclosure names the actual systems used and completely describes their role.
- Confirm that no SPEED-Bench-derived prompt or generated response is present.
- Verify `MANIFEST.json` and every entry in `SHA256SUMS`.
- Reproduce both summary JSON files and all three figures in a clean environment.
- Have the human author review and understand the runtime patch, evaluator, statistics, and manuscript.
- Upload the final capsule contents to the public repository and create the `v1.0.0` release.
- Replace the file in the reserved Zenodo record `10.5281/zenodo.22049029` with the final ZIP, confirm its metadata and MIT license, and publish the record.
