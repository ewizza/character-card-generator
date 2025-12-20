from pathlib import Path
import json
import sys

MAIN = Path("src/scripts/main.js")
BIND = Path("public/workflows/comfy/sd_basic.bindings.json")

def read_text(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    s = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    return s, nl

def write_text(p: Path, s: str, nl: str):
    p.write_bytes(s.replace("\n", nl).encode("utf-8"))

def patch_main():
    if not MAIN.exists():
        raise RuntimeError("main.js not found (run from repo root).")

    s, nl = read_text(MAIN)
    changed = False

    # 1) Ensure updateImageProviderUI() calls loadComfyCheckpoints()
    key = "const updateImageProviderUI = () => {"
    i = s.find(key)
    if i != -1:
        # find end of that function (the next "\n    };" after it)
        end = s.find("\n    };", i)
        if end != -1:
            block = s[i:end]
            if "loadComfyCheckpoints" not in block:
                insert = "\n\n      this.loadComfyCheckpoints();"
                s = s[:end] + insert + s[end:]
                changed = True

    # 2) Provider change handler should call loadComfyCheckpoints()
    old = 'imageProviderSelect.addEventListener("change", () => {\n\n        updateImageProviderUI();\n\n        this.saveAPISettings();\n\n      });'
    if old in s and "this.loadComfyCheckpoints();" not in old:
        s = s.replace(
            old,
            'imageProviderSelect.addEventListener("change", () => {\n\n        updateImageProviderUI();\n\n        this.loadComfyCheckpoints();\n        this.saveAPISettings();\n\n      });'
        )
        changed = True
    else:
        # More tolerant replace: insert between updateImageProviderUI() and saveAPISettings()
        needle = "updateImageProviderUI();\n\n        this.saveAPISettings();"
        if needle in s and "this.loadComfyCheckpoints();" not in s[s.find(needle)-120:s.find(needle)+120]:
            s = s.replace(needle, "updateImageProviderUI();\n\n        this.loadComfyCheckpoints();\n        this.saveAPISettings();")
            changed = True

    # 3) Initial state should call loadComfyCheckpoints()
    init = "// Initial state\n\n      updateImageProviderUI();"
    if init in s and "this.loadComfyCheckpoints();" not in s[s.find(init):s.find(init)+200]:
        s = s.replace(init, init + "\n\n      this.loadComfyCheckpoints();")
        changed = True

    # 4) Ensure comfyui workflow family + base url change listeners exist
    if "Refresh ComfyUI checkpoints when ComfyUI settings change" not in s:
        anchor = "    // Clear config button"
        if anchor in s:
            snippet = (
                '    // Refresh ComfyUI checkpoints when ComfyUI settings change\n'
                '    const comfyuiWorkflowFamilyEl = document.getElementById("comfyui-workflow-family");\n'
                '    if (comfyuiWorkflowFamilyEl) {\n'
                '      comfyuiWorkflowFamilyEl.addEventListener("change", () => {\n'
                '        this.loadComfyCheckpoints();\n'
                '        this.saveAPISettings();\n'
                '      });\n'
                '    }\n'
                '    const comfyuiBaseUrlEl = document.getElementById("comfyui-base-url");\n'
                '    if (comfyuiBaseUrlEl) {\n'
                '      comfyuiBaseUrlEl.addEventListener("change", () => {\n'
                '        this.loadComfyCheckpoints();\n'
                '        this.saveAPISettings();\n'
                '      });\n'
                '    }\n\n'
            )
            s = s.replace(anchor, snippet + anchor, 1)
            changed = True

    # 5) Make saveAPISettings() call loadComfyCheckpoints() (robust brace-find)
    sig = "saveAPISettings() {"
    p = s.find(sig)
    if p != -1:
        q = s.find("}", p)
        # find first occurrence of loadImageSamplers() call inside the method
        body_start = s.find("{", p) + 1
        body_end = s.find("\n  }\n", p)
        if body_start != 0 and body_end != -1:
            body = s[body_start:body_end]
            if "this.loadImageSamplers();" in body and "this.loadComfyCheckpoints();" not in body:
                s = s.replace("this.loadImageSamplers();", "this.loadImageSamplers();\n    this.loadComfyCheckpoints();", 1)
                changed = True

    if changed:
        write_text(MAIN, s, nl)
        print("main.js: wired loadComfyCheckpoints() so dropdown shows + populates")
    else:
        print("main.js: no changes needed")

def patch_bindings():
    if not BIND.exists():
        raise RuntimeError("sd_basic.bindings.json not found.")

    raw = BIND.read_text(encoding="utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    data = json.loads(raw)

    defaults = data.get("defaults", {})
    # IMPORTANT: null means "do not apply unless user picked one"
    if defaults.get("ckptName", "___missing___") != None:
        defaults["ckptName"] = None
        data["defaults"] = defaults
        out = json.dumps(data, indent=2)
        BIND.write_text(out, encoding="utf-8", newline=nl)
        print("sd_basic.bindings.json: set defaults.ckptName = null")
    else:
        print("sd_basic.bindings.json: no changes needed")

def main():
    patch_main()
    patch_bindings()
    print("OK: v4b applied.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
