from pathlib import Path
import json
import re
import sys

ROOT = Path(".")
INDEX = ROOT / "index.html"
CFG = ROOT / "src/scripts/config.js"
MAIN = ROOT / "src/scripts/main.js"
API = ROOT / "src/scripts/api.js"
BIND = ROOT / "public/workflows/comfy/sd_basic.bindings.json"

def read_text(p: Path):
    raw = p.read_bytes()
    NL = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8", errors="strict"), NL

def write_text(p: Path, s: str):
    p.write_text(s, encoding="utf-8", newline="")

def ensure_index_dropdown():
    txt, NL = read_text(INDEX)
    if 'id="comfyui-checkpoint-group"' in txt:
        print("index.html: checkpoint group already present")
        return False

    # Insert right after the comfyui-workflow-family form-group inside #comfyui-settings
    anchor = '<select id="comfyui-workflow-family"'
    i = txt.find(anchor)
    if i == -1:
        raise RuntimeError("index.html: cannot find comfyui-workflow-family select")

    # Find the closing </div> of that form-group
    close_div = txt.find("</div>", i)
    if close_div == -1:
        raise RuntimeError("index.html: cannot find closing </div> after workflow family")
    close_div = close_div + len("</div>")

    insert = (
        NL +
        '                    <div class="form-group" id="comfyui-checkpoint-group" style="display: none;">' + NL +
        '                        <label for="comfyui-checkpoint" class="label">Checkpoint</label>' + NL +
        '                        <select id="comfyui-checkpoint" class="input" style="height: 3rem;">' + NL +
        '                            <option value="">(use workflow default)</option>' + NL +
        "                        </select>" + NL +
        '                        <p style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">' + NL +
        "                            Loaded from ComfyUI <code>/models/checkpoints</code> via the proxy." + NL +
        "                        </p>" + NL +
        "                    </div>" + NL
    )

    txt = txt[:close_div] + insert + txt[close_div:]
    write_text(INDEX, txt)
    print("index.html: added checkpoint dropdown markup")
    return True

def ensure_config_ckptname():
    txt, NL = read_text(CFG)
    changed = False

    # 1) Add default ckptName
    if "workflowFamily" in txt and "ckptName" not in txt:
        txt2 = txt.replace(
            'workflowFamily: "sd_basic",',
            'workflowFamily: "sd_basic",\n            ckptName: "",',
        )
        if txt2 != txt:
            txt = txt2
            changed = True

    # 2) loadFromForm: read comfyui-checkpoint
    if 'getElementById("comfyui-checkpoint")' not in txt:
        needle = 'const comfyuiWorkflowFamily = document\n      .getElementById("comfyui-workflow-family")\n      ?.value?.trim();'
        if needle in txt:
            txt = txt.replace(
                needle,
                needle + '\n    const comfyuiCheckpoint = document\n      .getElementById("comfyui-checkpoint")\n      ?.value?.trim();'
            )
            changed = True

        # persist ckptName even if empty
        insert_after = "this.config.api.image.comfyui.workflowFamily = comfyuiWorkflowFamily;"
        if insert_after in txt and "ckptName" not in txt.split(insert_after, 1)[1][:250]:
            txt = txt.replace(
                insert_after,
                insert_after + "\n    if (comfyuiCheckpoint !== undefined) {\n      this.config.api.image.comfyui.ckptName = comfyuiCheckpoint || \"\";\n    }"
            )
            changed = True

    # 3) saveToForm: set comfyui-checkpoint value
    if 'document.getElementById("comfyui-checkpoint")' not in txt.split("saveToForm", 1)[-1]:
        # add element reference near other comfyui refs
        ref_needle = 'const comfyuiWorkflowFamily = document.getElementById(\n        "comfyui-workflow-family",\n      );'
        if ref_needle in txt:
            txt = txt.replace(
                ref_needle,
                ref_needle + '\n      const comfyuiCheckpoint = document.getElementById("comfyui-checkpoint");'
            )
            changed = True

        fill_needle = 'this.config.api.image.comfyui?.workflowFamily || "sd_basic";'
        if fill_needle in txt:
            txt = txt.replace(
                fill_needle,
                fill_needle + '\n      if (comfyuiCheckpoint)\n        comfyuiCheckpoint.value =\n          this.config.api.image.comfyui?.ckptName || "";'
            )
            changed = True

    if changed:
        write_text(CFG, txt)
        print("config.js: added comfyui.ckptName persistence")
    else:
        print("config.js: no changes needed")
    return changed

def ensure_bindings_map():
    data = json.loads(BIND.read_text(encoding="utf-8"))
    mp = data.get("map", {})
    if "ckptName" in mp:
        print("sd_basic.bindings.json: ckptName mapping already present")
        return False

    # Node 4 is CheckpointLoaderSimple in your sd_basic.api.json
    mp["ckptName"] = [{"node": "4", "input": "ckpt_name"}]
    data["map"] = mp

    # IMPORTANT: do NOT add ckptName to defaults (empty string would get applied!)
    BIND.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("sd_basic.bindings.json: added ckptName -> node 4.ckpt_name")
    return True

def ensure_api_values_ckpt():
    txt, NL = read_text(API)
    if "ckptName:" in txt:
        print("api.js: ckptName already included in ComfyUI values")
        return False

    # Insert into the values object inside generateImageViaComfyUI
    m = re.search(r"const values\s*=\s*\{", txt)
    if not m:
        raise RuntimeError("api.js: cannot find 'const values = {'")

    ins = (
        NL +
        "      // Optional SD checkpoint override (ComfyUI sd_basic workflow)" + NL +
        "      ckptName: (() => {" + NL +
        "        if ((family || 'sd_basic') !== 'sd_basic') return undefined;" + NL +
        "        const raw = this.config.get('api.image.comfyui.ckptName');" + NL +
        "        if (!raw) return undefined;" + NL +
        "        const v = String(raw).trim();" + NL +
        "        return v ? v : undefined;" + NL +
        "      })()," + NL
    )

    txt = txt[:m.end()] + ins + txt[m.end():]
    write_text(API, txt)
    print("api.js: added ckptName into ComfyUI binding values")
    return True

def ensure_main_logic():
    txt, NL = read_text(MAIN)
    changed = False

    # 1) Add comfyui-checkpoint to apiInputs change-save list
    if "#comfyui-checkpoint" not in txt:
        txt2 = txt.replace(
            "#image-provider, #comfyui-base-url, #comfyui-workflow-family,",
            "#image-provider, #comfyui-base-url, #comfyui-workflow-family, #comfyui-checkpoint,"
        )
        if txt2 != txt:
            txt = txt2
            changed = True

    # 2) Make saveAPISettings refresh checkpoints too
    if "this.loadComfyCheckpoints();" not in txt:
        txt2 = txt.replace(
            "this.loadImageSamplers();",
            "this.loadImageSamplers();\n    this.loadComfyCheckpoints();"
        )
        if txt2 != txt:
            txt = txt2
            changed = True

    # 3) Add loadComfyCheckpoints() method if missing
    if "async loadComfyCheckpoints()" not in txt:
        # Insert just before loadImageSamplers() (keeps methods together)
        anchor = "  async loadImageSamplers() {"
        pos = txt.find(anchor)
        if pos == -1:
            raise RuntimeError("main.js: cannot find loadImageSamplers() to insert before")

        method = (
            "  async loadComfyCheckpoints() {" + NL +
            '    const group = document.getElementById("comfyui-checkpoint-group");' + NL +
            '    const select = document.getElementById("comfyui-checkpoint");' + NL +
            '    if (!group || !select) return;' + NL +
            "" + NL +
            '    const provider = document.getElementById("image-provider")?.value || "sdapi";' + NL +
            '    const family = document.getElementById("comfyui-workflow-family")?.value || "sd_basic";' + NL +
            "" + NL +
            "    // Show only for ComfyUI + sd_basic" + NL +
            '    const shouldShow = provider === "comfyui" && family === "sd_basic";' + NL +
            '    group.style.display = shouldShow ? "block" : "none";' + NL +
            "    if (!shouldShow) return;" + NL +
            "" + NL +
            '    const comfyBaseUrl = (document.getElementById("comfyui-base-url")?.value || "").trim() || this.config.get("api.image.comfyui.baseUrl");' + NL +
            "    if (!comfyBaseUrl) {" + NL +
            '      select.innerHTML = \'<option value="">Set ComfyUI Base URL to load checkpoints</option>\';' + NL +
            "      return;" + NL +
            "    }" + NL +
            "" + NL +
            '    const current = this.config.get("api.image.comfyui.ckptName") || "";' + NL +
            '    select.innerHTML = \'<option value="">Loading checkpoints…</option>\';' + NL +
            "" + NL +
            "    try {" + NL +
            "      const resp = await fetch('/api/comfy/models/checkpoints', {" + NL +
            "        method: 'GET'," + NL +
            "        headers: { 'X-API-URL': comfyBaseUrl }," + NL +
            "      });" + NL +
            "      const text = await resp.text().catch(() => '');" + NL +
            "      if (!resp.ok) throw new Error(text || resp.statusText);" + NL +
            "" + NL +
            "      let data = null;" + NL +
            "      try { data = JSON.parse(text); } catch { data = null; }" + NL +
            "      let items = [];" + NL +
            "      if (Array.isArray(data)) items = data;" + NL +
            "      else if (data && Array.isArray(data.models)) items = data.models;" + NL +
            "" + NL +
            "      items = items.filter(Boolean).map(String);" + NL +
            "      items.sort((a,b) => a.localeCompare(b));" + NL +
            "" + NL +
            "      select.innerHTML = '';" + NL +
            "      const opt0 = document.createElement('option');" + NL +
            "      opt0.value = '';" + NL +
            "      opt0.textContent = '(use workflow default)';" + NL +
            "      select.appendChild(opt0);" + NL +
            "" + NL +
            "      for (const name of items) {" + NL +
            "        const opt = document.createElement('option');" + NL +
            "        opt.value = name;" + NL +
            "        opt.textContent = name;" + NL +
            "        select.appendChild(opt);" + NL +
            "      }" + NL +
            "" + NL +
            "      if (current && !items.includes(current)) {" + NL +
            "        const opt = document.createElement('option');" + NL +
            "        opt.value = current;" + NL +
            "        opt.textContent = `⚠ missing: ${current}`;" + NL +
            "        select.appendChild(opt);" + NL +
            "      }" + NL +
            "      select.value = current;" + NL +
            "    } catch (e) {" + NL +
            "      console.warn('Failed to load ComfyUI checkpoints:', e);" + NL +
            "      select.innerHTML = '';" + NL +
            "      const opt = document.createElement('option');" + NL +
            "      opt.value = '';" + NL +
            "      opt.textContent = 'Failed to load checkpoints (see console)';" + NL +
            "      select.appendChild(opt);" + NL +
            "      select.value = '';" + NL +
            "    }" + NL +
            "  }" + NL + NL
        )

        txt = txt[:pos] + method + txt[pos:]
        changed = True

    # 4) Hook it into provider + family + baseUrl changes and modal open
    if "this.loadComfyCheckpoints();" not in txt.split("imageProviderSelect.addEventListener", 1)[-1]:
        # add into provider change handler
        txt2 = txt.replace(
            "updateImageProviderUI();\n        this.saveAPISettings();",
            "updateImageProviderUI();\n        this.loadComfyCheckpoints();\n        this.saveAPISettings();"
        )
        if txt2 != txt:
            txt = txt2
            changed = True

    if "comfyui-workflow-family" in txt and "loadComfyCheckpoints();" not in txt.split("comfyui-workflow-family")[-1]:
        # Add explicit listeners near the provider block (safe append)
        block_anchor = "    if (imageProviderSelect) {"
        p = txt.find(block_anchor)
        if p != -1 and "comfyuiWorkflowFamilyEl" not in txt:
            ins = (
                NL +
                '    const comfyuiWorkflowFamilyEl = document.getElementById("comfyui-workflow-family");' + NL +
                '    if (comfyuiWorkflowFamilyEl) {' + NL +
                '      comfyuiWorkflowFamilyEl.addEventListener("change", () => {' + NL +
                '        this.loadComfyCheckpoints();' + NL +
                '        this.saveAPISettings();' + NL +
                "      });" + NL +
                "    }" + NL +
                '    const comfyuiBaseUrlEl = document.getElementById("comfyui-base-url");' + NL +
                '    if (comfyuiBaseUrlEl) {' + NL +
                '      comfyuiBaseUrlEl.addEventListener("change", () => {' + NL +
                '        this.loadComfyCheckpoints();' + NL +
                '        this.saveAPISettings();' + NL +
                "      });" + NL +
                "    }" + NL
            )
            # Insert after the provider block's initial state call
            insert_after = "// Initial state\n      updateImageProviderUI();"
            if insert_after in txt:
                txt = txt.replace(insert_after, insert_after + "\n      this.loadComfyCheckpoints();")
                changed = True
            # Append listeners near the provider section end (after initial state block)
            # Find the closing brace for the provider select if-block by inserting after "updateImageProviderUI();"
            # We'll just append near the end of bindEvents before "}" of bindEvents – safe enough.
            end_bind = txt.rfind("  }", 0, txt.find("async checkAPIStatus"))
            if end_bind != -1:
                txt = txt[:end_bind] + ins + txt[end_bind:]
                changed = True

    # Modal open: also load checkpoints
    if "this.loadComfyCheckpoints();" not in txt.split("apiSettingsBtn.addEventListener", 1)[-1]:
        txt2 = txt.replace(
            "this.loadImageSamplers();",
            "this.loadImageSamplers();\n      this.loadComfyCheckpoints();"
        )
        if txt2 != txt:
            txt = txt2
            changed = True

    # 5) Hide SDAPI sampler UI when provider is comfyui (prevents confusion)
    if "samplerGroup.style.display" not in txt:
        # Extend updateImageProviderUI function
        needle = 'if (comfyuiSettings) {\n        comfyuiSettings.style.display = provider === "comfyui" ? "block" : "none";\n      }'
        if needle in txt:
            txt = txt.replace(
                needle,
                needle +
                '\n      const samplerEl = document.getElementById("image-sampler");\n      const samplerGroup = samplerEl?.closest?.(".form-group");\n      if (samplerGroup) samplerGroup.style.display = provider === "comfyui" ? "none" : "block";'
            )
            changed = True

    if changed:
        write_text(MAIN, txt)
        print("main.js: added loadComfyCheckpoints + wiring")
    else:
        print("main.js: no changes needed")
    return changed

def main():
    for p in (INDEX, CFG, MAIN, API, BIND):
        if not p.exists():
            print(f"ERROR: Missing {p}. Run from repo root.")
            return 1

    changes = 0
    changes += 1 if ensure_index_dropdown() else 0
    changes += 1 if ensure_config_ckptname() else 0
    changes += 1 if ensure_bindings_map() else 0
    changes += 1 if ensure_api_values_ckpt() else 0
    changes += 1 if ensure_main_logic() else 0

    print(f"OK: Done. Files changed: {changes}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
