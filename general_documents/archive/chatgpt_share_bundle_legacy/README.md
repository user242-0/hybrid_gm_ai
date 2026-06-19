# Legacy ChatGPT share-bundle workflow

These files were moved out of the repository root and `scripts/` on
2026-06-19 because they are not used by the runtime.

- `chatgpt_shared_manifest.yaml` lists files for a historical ChatGPT upload
  bundle.
- `make_share_bundle.py` builds that bundle.

The script historically expects `chatgpt_shared_manifest.yml`, while the
tracked manifest uses the `.yaml` suffix. This mismatch is preserved as
historical context rather than repaired because the workflow is archived.
