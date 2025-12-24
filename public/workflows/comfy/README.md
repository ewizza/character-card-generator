# ComfyUI Workflows (Phase 1)

Phase 1 uses **curated, known-good ComfyUI workflows** stored in this folder.

## Files

- `sd_basic.api.json` + `sd_basic.bindings.json`
  - A minimal SD 1.5-style workflow: Load Checkpoint → Text Encode (pos/neg) → KSampler → VAE Decode → SaveImage.
  - The bindings map tells the app which node inputs to update (prompt, size, steps, seed, etc.).

- `flux_basic.api.json` + `flux_basic.bindings.json`
  - Placeholder in this phase. Replace with your own API-format FLUX workflow export.

## Exporting from ComfyUI

In ComfyUI, use **Save → "Save (API format)"** to export an API-format workflow.

If you replace `sd_basic.api.json` with your own, update `sd_basic.bindings.json` to match your node ids.
