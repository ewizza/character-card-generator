from pathlib import Path
import re
import sys

SERVER = Path("proxy/server.js")
if not SERVER.exists():
    print("ERROR: proxy/server.js not found. Run from repo root.")
    sys.exit(1)

raw = SERVER.read_bytes()
NL = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8", errors="strict")

if "/api/comfy/object_info" in text:
    print("Already present: /api/comfy/object_info")
    sys.exit(0)

# Insert after /api/comfy/models routes if present, otherwise after /api/comfy/view
insert_after = None
m = re.search(r'app\.get\("/api/comfy/models/:folder",[\s\S]*?\n\}\);\s*', text)
if m:
    insert_after = m
else:
    m2 = re.search(r'app\.get\("/api/comfy/view",[\s\S]*?\n\}\);\s*', text)
    if not m2:
        print("ERROR: could not find insertion anchor (/api/comfy/view).")
        sys.exit(1)
    insert_after = m2

block = f"""
// -----------------------------
// ComfyUI object_info passthrough (for sampler/scheduler lists, etc.)
// -----------------------------
app.get("/api/comfy/object_info", async (req, res) => {{
  try {{
    const apiUrl = req.headers["x-api-url"] || req.headers["x-comfy-url"];
    if (!apiUrl) {{
      return res.status(400).json({{
        error: {{
          code: "400",
          message: "ComfyUI Base URL required",
          details: "Please configure your ComfyUI Base URL in the image settings",
        }},
      }});
    }}

    const fullUrl = buildComfyUrl(apiUrl, "/object_info");
    const response = await fetch(fullUrl, {{ method: "GET" }});
    const text = await response.text();

    if (!response.ok) {{
      return res.status(response.status).json({{
        error: {{
          code: response.status.toString(),
          message: `ComfyUI Error: ${{response.statusText}}`,
          details: text,
        }},
      }});
    }}

    let json;
    try {{
      json = JSON.parse(text);
    }} catch {{
      return res.type("application/json").send(text);
    }}

    // Optional filter: /api/comfy/object_info?class=KSampler
    const cls = (req.query.class || "").toString().trim();
    if (cls) {{
      if (json && Object.prototype.hasOwnProperty.call(json, cls)) {{
        return res.json(json[cls]);
      }}
      return res.status(404).json({{
        error: {{
          code: "404",
          message: "Class not found in object_info",
          details: cls,
        }},
      }});
    }}

    return res.json(json);
  }} catch (error) {{
    console.error("ComfyUI /object_info proxy error:", error);
    res.status(500).json({{
      error: {{
        code: "500",
        message: "Internal server error in ComfyUI object_info proxy",
        details: error.message,
      }},
    }});
  }}
}});
""".strip("\n").replace("\n", NL) + NL + NL

text = text[:insert_after.end()] + NL + block + text[insert_after.end():]
SERVER.write_bytes(text.encode("utf-8"))
print("OK: Added /api/comfy/object_info to proxy/server.js")
