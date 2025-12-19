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

# Already patched?
if 'app.get("/api/comfy/models' in text:
    print("Already present: /api/comfy/models endpoints")
    sys.exit(0)

# Find the /api/comfy/history route block and insert after it
pattern = r'app\.get\("/api/comfy/history/:promptId",\s*async\s*\(req,\s*res\)\s*=>\s*\{[\s\S]*?\n\}\);\s*'
m = re.search(pattern, text)
if not m:
    print("ERROR: Could not locate /api/comfy/history route block to insert after.")
    sys.exit(1)

insertion = f"""
// List available model folders (ComfyUI /models)
app.get("/api/comfy/models", async (req, res) => {{
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

    const fullUrl = buildComfyUrl(apiUrl, "/models");
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

    res.setHeader("Access-Control-Allow-Origin", "*");
    res.type("application/json").send(text);
  }} catch (error) {{
    console.error("ComfyUI /models proxy error:", error);
    res.status(500).json({{
      error: {{
        code: "500",
        message: "Internal server error in ComfyUI models proxy",
        details: error.message,
      }},
    }});
  }}
}});

// List models in a folder (ComfyUI /models/<folder>), e.g. checkpoints, vae, loras
app.get("/api/comfy/models/:folder", async (req, res) => {{
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

    const folder = req.params.folder;
    const fullUrl = buildComfyUrl(apiUrl, `/models/${{encodeURIComponent(folder)}}`);
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

    res.setHeader("Access-Control-Allow-Origin", "*");
    res.type("application/json").send(text);
  }} catch (error) {{
    console.error("ComfyUI /models/:folder proxy error:", error);
    res.status(500).json({{
      error: {{
        code: "500",
        message: "Internal server error in ComfyUI models folder proxy",
        details: error.message,
      }},
    }});
  }}
}});
""".strip("\n").replace("\n", NL) + NL + NL

text = text[:m.end()] + NL + insertion + text[m.end():]
SERVER.write_bytes(text.encode("utf-8"))
print("OK: Added /api/comfy/models and /api/comfy/models/:folder to proxy/server.js")
