from pathlib import Path
import sys

API = Path("src/scripts/api.js")
if not API.exists():
    print("ERROR: src/scripts/api.js not found (run from repo root).")
    sys.exit(1)

raw = API.read_bytes()
nl = b"\r\n" if b"\r\n" in raw else b"\n"
NL = "\r\n" if nl == b"\r\n" else "\n"
text = raw.decode("utf-8", errors="strict")

# If already patched, do nothing
if "async fetchComfyHistory(" in text and "async waitForComfyOutput(" in text and "ComfyUI completed (prompt_id:" in text:
    print("Already patched (3b-2 polling helpers present).")
    sys.exit(0)

insert_anchor = "  // Phase 1 (Piece 3b-1): load + bind workflow, submit to ComfyUI via proxy."
pos = text.find(insert_anchor)
if pos == -1:
    print("ERROR: Could not find insertion anchor for ComfyUI helpers.")
    sys.exit(1)

helpers = f"""
  async fetchComfyHistory(comfyBaseUrl, promptId) {{
    const resp = await fetch(`/api/comfy/history/${{encodeURIComponent(promptId)}}`, {{
      method: "GET",
      headers: {{"X-API-URL": comfyBaseUrl}},
    }});

    const text = await resp.text().catch(() => "");
    let json = null;
    try {{ json = JSON.parse(text); }} catch {{ /* ignore */ }}

    if (!resp.ok) {{
      const msg = json?.message || json?.error?.message || resp.statusText;
      throw new Error(`ComfyUI history failed (${{resp.status}}): ${{msg}}\\n${{text}}`);
    }}
    return json ?? {{}};
  }}

  extractFirstComfyImageFromHistory(historyJson, promptId) {{
    const entry = historyJson?.[promptId];
    const outputs = entry?.outputs;
    if (!outputs || typeof outputs !== "object") return null;

    for (const nodeId of Object.keys(outputs)) {{
      const nodeOut = outputs[nodeId];
      const images = nodeOut?.images;
      if (Array.isArray(images) && images.length > 0) {{
        const img = images[0];
        if (img?.filename) {{
          return {{
            filename: img.filename,
            subfolder: img.subfolder ?? "",
            type: img.type ?? "output",
            nodeId,
          }};
        }}
      }}
    }}
    return null;
  }}

  async waitForComfyOutput(comfyBaseUrl, promptId, opts = {{}}) {{
    const timeoutMs = Number.isFinite(opts.timeoutMs) ? opts.timeoutMs : 120000;
    const pollMs = Number.isFinite(opts.pollMs) ? opts.pollMs : 1000;
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {{
      const history = await this.fetchComfyHistory(comfyBaseUrl, promptId);
      const entry = history?.[promptId];
      const img = this.extractFirstComfyImageFromHistory(history, promptId);
      if (img) return img;

      const completed = entry?.status?.completed === true;
      const statusStr = entry?.status?.status_str;
      if (completed && statusStr && statusStr !== "success") {{
        throw new Error(`ComfyUI run completed with status '${{statusStr}}' (prompt_id: ${{promptId}}).`);
      }}
      if (completed) {{
        // Some fully-cached runs report success but return no outputs in history.
        throw new Error(`ComfyUI completed but returned no outputs (prompt_id: ${{promptId}}). Try changing seed/prompt to avoid full-cache.`);
      }}

      await new Promise((r) => setTimeout(r, pollMs));
    }}
    throw new Error(`Timed out waiting for ComfyUI outputs (prompt_id: ${{promptId}}).`);
  }}

""".strip("\n")

# Normalize helper block newlines to match file
helpers = helpers.replace("\n", NL) + NL + NL

text = text[:pos] + helpers + text[pos:]

needle = "    // Next pieces will: poll /api/comfy/history/:promptId and fetch /api/comfy/view."
idx = text.find(needle)
if idx == -1:
    print("ERROR: Could not find the submit-only placeholder block to replace.")
    sys.exit(1)

# Replace from that comment through the following throw new Error(...) block.
# We locate the next 'throw new Error(' and then the next line that ends the call '    );'
throw_idx = text.find("    throw new Error", idx)
if throw_idx == -1:
    print("ERROR: Could not find 'throw new Error' after placeholder comment.")
    sys.exit(1)

end_idx = text.find(f"{NL}    );", throw_idx)
if end_idx == -1:
    print("ERROR: Could not find end of submit-only throw block.")
    sys.exit(1)
end_idx = end_idx + len(f"{NL}    );") + len(NL)

replacement = f"""    // Piece 3b-2: poll history until we get an output filename (no /view fetch yet).
    const out = await this.waitForComfyOutput(comfyBaseUrl, promptId, {{
      timeoutMs: 120000,
      pollMs: 1000,
    }});

    throw new Error(
      `ComfyUI completed (prompt_id: ${{promptId}}). Output: ${{out.filename}} (subfolder: '${{out.subfolder}}', type: '${{out.type}}'). Image fetch is implemented in the next patch.`,
    );
""".replace("\n", NL)

text = text[:idx] + replacement + text[end_idx:]

API.write_bytes(text.encode("utf-8"))
print("OK: Applied Piece 3b-2 (poll history only) to src/scripts/api.js")
