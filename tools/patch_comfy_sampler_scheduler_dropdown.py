from pathlib import Path
import json
import re
import sys

INDEX = Path("index.html")
CFG   = Path("src/scripts/config.js")
MAIN  = Path("src/scripts/main.js")
API   = Path("src/scripts/api.js")
BIND  = Path("public/workflows/comfy/sd_basic.bindings.json")

def read_text(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    s = raw.decode("utf-8", errors="strict").replace("\r\n","\n").replace("\r","\n")
    return s, nl

def write_text(p: Path, s: str, nl: str):
    p.write_bytes(s.replace("\n", nl).encode("utf-8"))

def ensure_index():
    s, nl = read_text(INDEX)
    if 'id="comfyui-sampler"' in s and 'id="comfyui-scheduler"' in s:
        print("index.html: sampler/scheduler already present")
        return False

    # Insert after checkpoint group if present, else after workflow family group
    anchor = 'id="comfyui-checkpoint-group"'
    pos = s.find(anchor)
    if pos != -1:
        after = s.find("</div>", pos)
        after = s.find("</div>", after + 6)  # checkpoint group close
        after = after + len("</div>")
    else:
        wf = s.find('id="comfyui-workflow-family"')
        if wf == -1:
            raise RuntimeError("index.html: can't find comfyui workflow family")
        after = s.find("</div>", wf)
        after = after + len("</div>")

    block = """
                    <div class="form-group" id="comfyui-sampler-group" style="display: none;">
                        <label for="comfyui-sampler" class="label">Sampler</label>
                        <select id="comfyui-sampler" class="input" style="height: 3rem;">
                            <option value="">(use workflow default)</option>
                        </select>
                    </div>

                    <div class="form-group" id="comfyui-scheduler-group" style="display: none;">
                        <label for="comfyui-scheduler" class="label">Scheduler</label>
                        <select id="comfyui-scheduler" class="input" style="height: 3rem;">
                            <option value="">(use workflow default)</option>
                        </select>
                    </div>
""".strip("\n")

    s = s[:after] + "\n" + block + "\n" + s[after:]
    write_text(INDEX, s, nl)
    print("index.html: added ComfyUI sampler/scheduler dropdown markup")
    return True

def ensure_bindings():
    data = json.loads(BIND.read_text(encoding="utf-8"))
    mp = data.get("map", {})
    changed = False

    if "samplerName" not in mp:
        mp["samplerName"] = [{"node":"3", "input":"sampler_name"}]
        changed = True
    if "schedulerName" not in mp:
        mp["schedulerName"] = [{"node":"3", "input":"scheduler"}]
        changed = True

    data["map"] = mp
    defaults = data.get("defaults", {})
    # Keep these null so they won't override unless selected
    if defaults.get("samplerName", "___missing___") is not None:
        defaults["samplerName"] = None; changed = True
    if defaults.get("schedulerName", "___missing___") is not None:
        defaults["schedulerName"] = None; changed = True
    data["defaults"] = defaults

    if changed:
        BIND.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("sd_basic.bindings.json: added samplerName/schedulerName bindings + null defaults")
    else:
        print("sd_basic.bindings.json: no changes needed")
    return changed

def ensure_config():
    s, nl = read_text(CFG)
    changed = False

    # defaults in config
    if "api.image.comfyui" in s and "samplerName" not in s:
        s2 = s.replace('workflowFamily: "sd_basic",', 'workflowFamily: "sd_basic",\n            ckptName: "",\n            samplerName: "",\n            schedulerName: "",')
        if s2 != s:
            s = s2; changed = True

    # loadFromForm: define vars
    if 'getElementById("comfyui-sampler")' not in s:
        s = s.replace(
            'const comfyuiCheckpoint = document\n      .getElementById("comfyui-checkpoint")\n      ?.value?.trim();',
            'const comfyuiCheckpoint = document\n      .getElementById("comfyui-checkpoint")\n      ?.value?.trim();\n    const comfyuiSampler = document\n      .getElementById("comfyui-sampler")\n      ?.value?.trim();\n    const comfyuiScheduler = document\n      .getElementById("comfyui-scheduler")\n      ?.value?.trim();'
        )
        changed = True

    # save into config (Phase 1)
    if "comfyui.samplerName" not in s:
        s = s.replace(
            'this.config.api.image.comfyui.ckptName = comfyuiCheckpoint || "";',
            'this.config.api.image.comfyui.ckptName = comfyuiCheckpoint || "";\n    }\n    if (comfyuiSampler !== undefined) {\n      this.config.api.image.comfyui.samplerName = comfyuiSampler || "";\n    }\n    if (comfyuiScheduler !== undefined) {\n      this.config.api.image.comfyui.schedulerName = comfyuiScheduler || "";\n'
        )
        changed = True

    # saveToForm: set values
    if 'document.getElementById("comfyui-sampler")' not in s.split("saveToForm",1)[-1]:
        s = s.replace(
            'const comfyuiCheckpoint = document.getElementById("comfyui-checkpoint");',
            'const comfyuiCheckpoint = document.getElementById("comfyui-checkpoint");\n      const comfyuiSampler = document.getElementById("comfyui-sampler");\n      const comfyuiScheduler = document.getElementById("comfyui-scheduler");'
        )
        changed = True
        s = s.replace(
            'this.config.api.image.comfyui?.ckptName || "";',
            'this.config.api.image.comfyui?.ckptName || "";\n      if (comfyuiSampler)\n        comfyuiSampler.value = this.config.api.image.comfyui?.samplerName || "";\n      if (comfyuiScheduler)\n        comfyuiScheduler.value = this.config.api.image.comfyui?.schedulerName || "";'
        )
        changed = True

    if changed:
        write_text(CFG, s, nl)
        print("config.js: added comfyui sampler/scheduler persistence")
    else:
        print("config.js: no changes needed")
    return changed

def ensure_api_values():
    s, nl = read_text(API)
    changed = False
    if "samplerName:" in s and "schedulerName:" in s:
        print("api.js: values already include samplerName/schedulerName")
        return False

    # Insert into values object for ComfyUI binding
    m = re.search(r"const values\s*=\s*\{", s)
    if not m:
        raise RuntimeError("api.js: cannot find const values = {")
    ins = """
      // Optional ComfyUI sampler/scheduler overrides (sd_basic KSampler node)
      samplerName: (() => {
        if ((family || "sd_basic") !== "sd_basic") return undefined;
        const v = this.config.get("api.image.comfyui.samplerName");
        const t = v ? String(v).trim() : "";
        return t ? t : undefined;
      })(),
      schedulerName: (() => {
        if ((family || "sd_basic") !== "sd_basic") return undefined;
        const v = this.config.get("api.image.comfyui.schedulerName");
        const t = v ? String(v).trim() : "";
        return t ? t : undefined;
      })(),
""".strip("\n")
    s = s[:m.end()] + "\n" + ins + "\n" + s[m.end():]
    write_text(API, s, nl)
    print("api.js: added samplerName/schedulerName into ComfyUI binding values")
    return True

def ensure_main_loader():
    s, nl = read_text(MAIN)
    changed = False

    if "async loadComfySamplerScheduler()" not in s:
        # Insert just before loadComfyCheckpoints() if present, else before loadImageSamplers()
        anchor = "  async loadComfyCheckpoints() {"
        pos = s.find(anchor)
        if pos == -1:
            pos = s.find("  async loadImageSamplers() {")
            if pos == -1:
                raise RuntimeError("main.js: cannot find insertion anchor for loader")

        method = """
  async loadComfySamplerScheduler() {
    const provider = document.getElementById("image-provider")?.value || "sdapi";
    const family = document.getElementById("comfyui-workflow-family")?.value || "sd_basic";

    const samplerGroup = document.getElementById("comfyui-sampler-group");
    const schedGroup = document.getElementById("comfyui-scheduler-group");
    const samplerSel = document.getElementById("comfyui-sampler");
    const schedSel = document.getElementById("comfyui-scheduler");
    if (!samplerGroup || !schedGroup || !samplerSel || !schedSel) return;

    const shouldShow = provider === "comfyui" && family === "sd_basic";
    samplerGroup.style.display = shouldShow ? "block" : "none";
    schedGroup.style.display = shouldShow ? "block" : "none";
    if (!shouldShow) return;

    const comfyBaseUrl = (document.getElementById("comfyui-base-url")?.value || "").trim()
      || this.config.get("api.image.comfyui.baseUrl");
    if (!comfyBaseUrl) {
      samplerSel.innerHTML = '<option value="">Set ComfyUI Base URL to load samplers</option>';
      schedSel.innerHTML = '<option value="">Set ComfyUI Base URL to load schedulers</option>';
      return;
    }

    const currentSampler = this.config.get("api.image.comfyui.samplerName") || "";
    const currentSched = this.config.get("api.image.comfyui.schedulerName") || "";

    samplerSel.innerHTML = '<option value="">Loading…</option>';
    schedSel.innerHTML = '<option value="">Loading…</option>';

    try {
      const resp = await fetch("/api/comfy/object_info?class=KSampler", {
        method: "GET",
        headers: { "X-API-URL": comfyBaseUrl },
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || resp.statusText);

      let info = null;
      try { info = JSON.parse(text); } catch { info = null; }
      const req = info?.input?.required || {};

      // ComfyUI usually encodes dropdown options as: [ [ "opt1","opt2"... ] ]
      const samplerOpts = (req?.sampler_name?.[0] && Array.isArray(req.sampler_name[0])) ? req.sampler_name[0] : [];
      const schedOpts = (req?.scheduler?.[0] && Array.isArray(req.scheduler[0])) ? req.scheduler[0] : [];

      function fill(selectEl, opts, current) {
        selectEl.innerHTML = "";
        const def = document.createElement("option");
        def.value = "";
        def.textContent = "(use workflow default)";
        selectEl.appendChild(def);

        for (const o of opts) {
          const opt = document.createElement("option");
          opt.value = String(o);
          opt.textContent = String(o);
          selectEl.appendChild(opt);
        }

        // Preserve saved value even if missing from list
        if (current && !opts.includes(current)) {
          const opt = document.createElement("option");
          opt.value = current;
          opt.textContent = `⚠ missing: ${current}`;
          selectEl.appendChild(opt);
        }

        selectEl.value = current || "";
      }

      fill(samplerSel, samplerOpts, currentSampler);
      fill(schedSel, schedOpts, currentSched);
    } catch (e) {
      console.warn("Failed to load ComfyUI sampler/scheduler lists:", e);
      samplerSel.innerHTML = '<option value="">Failed to load samplers (see console)</option>';
      schedSel.innerHTML = '<option value="">Failed to load schedulers (see console)</option>';
    }
  }
""".strip("\n")

        s = s[:pos] + method.replace("\n", "\n") + "\n\n" + s[pos:]
        changed = True

    # Ensure loadComfySamplerScheduler is called in the same places as checkpoints
    if "this.loadComfySamplerScheduler();" not in s:
        # init/save/provider change/family/baseurl change paths already call loadComfyCheckpoints; piggyback
        s = s.replace("this.loadComfyCheckpoints();", "this.loadComfyCheckpoints();\n    this.loadComfySamplerScheduler();")
        changed = True

    if changed:
        write_text(MAIN, s, nl)
        print("main.js: added loader + wired calls")
    else:
        print("main.js: no changes needed")
    return changed

def main():
    for p in (INDEX, CFG, MAIN, API, BIND):
        if not p.exists():
            print(f"ERROR: missing {p} (run from repo root).")
            return 1

    ensure_index()
    ensure_bindings()
    ensure_config()
    ensure_api_values()
    ensure_main_loader()
    print("OK: ComfyUI sampler/scheduler dropdowns added.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
