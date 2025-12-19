from pathlib import Path
import sys

API = Path("src/scripts/api.js")
if not API.exists():
    print("ERROR: src/scripts/api.js not found (run from repo root).")
    sys.exit(1)

raw = API.read_bytes()
NL = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8", errors="strict")

# If already patched, do nothing
if "async fetchComfyViewBlob(" in text and "URL.createObjectURL" in text and "Image fetch is implemented in the next patch" not in text:
    print("Already patched (3b-3 view fetch appears present).")
    sys.exit(0)

# Insert helper method before makeRequest (stable anchor in this repo)
anchor = f"{NL}  async makeRequest("
pos = text.find(anchor)
if pos == -1:
    print("ERROR: Could not find anchor 'async makeRequest' to insert helper.")
    sys.exit(1)

helper = f"""
  async fetchComfyViewBlob(comfyBaseUrl, filename, subfolder = "", type = "output") {{
    const qs = new URLSearchParams({{
      filename: filename,
      subfolder: subfolder ?? "",
      type: type ?? "output",
    }}).toString();

    const resp = await fetch(`/api/comfy/view?${{qs}}`, {{
      method: "GET",
      headers: {{ "X-API-URL": comfyBaseUrl }},
    }});

    if (!resp.ok) {{
      const t = await resp.text().catch(() => "");
      throw new Error(`ComfyUI view failed (${{resp.status}}): ${{t || resp.statusText}}`);
    }}

    return await resp.blob();
  }}
""".strip("\n").replace("\n", NL) + NL + NL

if "async fetchComfyViewBlob(" not in text:
    text = text[:pos] + helper + text[pos:]

# Replace the "throw new Error(`ComfyUI completed ... Image fetch is implemented in the next patch.`)"
marker = "Image fetch is implemented in the next patch"
idx = text.find(marker)
if idx == -1:
    print("ERROR: Could not find the 3b-2 placeholder message to replace.")
    sys.exit(1)

# Find the start of the throw block containing that marker
throw_start = text.rfind("throw new Error", 0, idx)
if throw_start == -1:
    print("ERROR: Could not find 'throw new Error' before marker.")
    sys.exit(1)

# Find end of that throw statement (the closing ');' on its own indentation)
end = text.find(f"{NL}    );", throw_start)
if end == -1:
    print("ERROR: Could not find end of throw block.")
    sys.exit(1)
end = end + len(f"{NL}    );") + len(NL)

replacement = f"""    // Piece 3b-3: fetch the output image via /api/comfy/view and return a blob URL for display.
    let imgBlob;
    try {{
      imgBlob = await this.fetchComfyViewBlob(
        comfyBaseUrl,
        out.filename,
        out.subfolder,
        out.type,
      );
    }} catch (e) {{
      throw new Error(`ComfyUI image fetch failed (prompt_id: ${{promptId}}): ${{e.message}}`);
    }}

    const objectUrl = URL.createObjectURL(imgBlob);
    return objectUrl;
""".replace("\n", NL)

text = text[:throw_start] + replacement + text[end:]

API.write_bytes(text.encode("utf-8"))
print("OK: Applied Piece 3b-3 (view fetch + return blob URL) to src/scripts/api.js")
