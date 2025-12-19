from pathlib import Path
import re
import sys

MAIN = Path("src/scripts/main.js")
if not MAIN.exists():
    print("ERROR: src/scripts/main.js not found (run from repo root).")
    sys.exit(1)

raw = MAIN.read_bytes()
NL = "\r\n" if b"\r\n" in raw else "\n"
txt = raw.decode("utf-8", errors="strict")

if "loadComfyCheckpoints" not in txt:
    print("ERROR: loadComfyCheckpoints() not found in main.js. (The dropdown logic was not added.)")
    sys.exit(1)

changed = False

# 1) Relax the shouldShow condition (accept sd_basic OR sd OR any value starting with "sd")
pat = r'const shouldShow\s*=\s*provider\s*===\s*"comfyui"\s*&&\s*family\s*===\s*"sd_basic";'
rep = 'const shouldShow = provider === "comfyui" && (family === "sd_basic" || family === "sd" || String(family).startsWith("sd"));'
txt2 = re.sub(pat, rep, txt)
if txt2 != txt:
    txt = txt2
    changed = True

# 2) Ensure we refresh checkpoints when workflow family changes
if "comfyui-workflow-family" in txt and "loadComfyCheckpoints" in txt:
    if "comfyuiWorkflowFamilyEl.addEventListener" not in txt:
        insert_anchor = 'const comfyuiWorkflowFamily'
        idx = txt.find(insert_anchor)
        if idx != -1:
            # Insert listener code after the existing "const comfyuiWorkflowFamily..." block.
            # Find the next semicolon after that const block.
            semi = txt.find(";", idx)
            if semi != -1:
                semi = semi + 1
                ins = (
                    NL +
                    '      const comfyuiWorkflowFamilyEl = document.getElementById("comfyui-workflow-family");' + NL +
                    '      if (comfyuiWorkflowFamilyEl) {' + NL +
                    '        comfyuiWorkflowFamilyEl.addEventListener("change", () => {' + NL +
                    '          this.loadComfyCheckpoints();' + NL +
                    '        });' + NL +
                    '      }' + NL
                )
                txt = txt[:semi] + ins + txt[semi:]
                changed = True

# 3) Ensure we refresh checkpoints when ComfyUI base URL changes
if "comfyui-base-url" in txt and "comfyuiBaseUrlEl.addEventListener" not in txt:
    idx = txt.find('document.getElementById("comfyui-base-url")')
    if idx != -1:
        # Insert near first occurrence in the setup block
        ins = (
            NL +
            '      const comfyuiBaseUrlEl = document.getElementById("comfyui-base-url");' + NL +
            '      if (comfyuiBaseUrlEl) {' + NL +
            '        comfyuiBaseUrlEl.addEventListener("change", () => {' + NL +
            '          this.loadComfyCheckpoints();' + NL +
            '        });' + NL +
            '      }' + NL
        )
        # Insert after the line containing the getElementById usage
        line_end = txt.find(NL, idx)
        if line_end != -1:
            txt = txt[:line_end] + ins + txt[line_end:]
            changed = True

if not changed:
    print("No changes needed (show condition/listeners already present).")
else:
    MAIN.write_text(txt, encoding="utf-8")
    print("OK: Updated ComfyUI checkpoint dropdown show-condition + refresh listeners in main.js")
