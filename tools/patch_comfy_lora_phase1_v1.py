from pathlib import Path
import re

ROOT = Path(".")
INDEX = ROOT / "index.html"
CFG = ROOT / "src/scripts/config.js"
MAIN = ROOT / "src/scripts/main.js"
API = ROOT / "src/scripts/api.js"


def read_text(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    s = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    return s, nl


def write_text(p: Path, s: str, nl: str):
    p.write_bytes(s.replace("\n", nl).encode("utf-8"))


def insert_after(s: str, anchor: str, block: str):
    i = s.find(anchor)
    if i == -1:
        return s, False
    j = s.find("</div>", i)
    if j == -1:
        return s, False
    j += len("</div>")
    return s[:j] + "\n" + block + "\n" + s[j:], True


def patch_index():
    s, nl = read_text(INDEX)
    if 'id="comfyui-lora-group"' in s:
        print("index.html: LoRA UI already present")
        return

    # Insert after the scheduler group (we know this exists now)
    anchor = 'id="comfyui-scheduler-group"'
    idx = s.find(anchor)
    if idx == -1:
        raise RuntimeError("index.html: could not find comfyui-scheduler-group")

    # Find the end of the scheduler group div
    end = s.find("</div>", idx)
    if end == -1:
        raise RuntimeError("index.html: could not locate scheduler group close </div>")
    end = s.find("</div>", end + 6)
    if end == -1:
        raise RuntimeError("index.html: could not locate scheduler group container close </div>")
    end += len("</div>")

    block = """
                    <div class="form-group" id="comfyui-lora-group" style="display: none;">
                        <label for="comfyui-lora" class="label">LoRA</label>
                        <select id="comfyui-lora" class="input" style="height: 3rem;">
                            <option value="">(none)</option>
                        </select>
                    </div>

                    <div class="form-group" id="comfyui-lora-strengths-group" style="display: none;">
                        <label class="label">LoRA Strength</label>
                        <div style="display: flex; gap: 0.75rem; align-items: center;">
                            <div style="flex: 1;">
                                <label for="comfyui-lora-strength-model" class="label" style="font-weight: 500; opacity: 0.85;">Model</label>
                                <input type="number" id="comfyui-lora-strength-model" class="input" min="-5" max="5" step="0.05" value="1" />
                            </div>
                            <div style="flex: 1;">
                                <label for="comfyui-lora-strength-clip" class="label" style="font-weight: 500; opacity: 0.85;">CLIP</label>
                                <input type="number" id="comfyui-lora-strength-clip" class="input" min="-5" max="5" step="0.05" value="1" />
                            </div>
                        </div>
                    </div>
""".strip("\n")

    s = s[:end] + "\n" + block + "\n" + s[end:]
    write_text(INDEX, s, nl)
    print("index.html: added LoRA dropdown + strength inputs")


def patch_config():
    s, nl = read_text(CFG)
    changed = False

    # Clean up a known duplicate from earlier patches if present
    s2 = re.sub(r"(schedulerName:\s*\"\",\s*\n)(\s*ckptName:\s*\"\",\s*\n)", r"\1", s)
    if s2 != s:
        s = s2
        changed = True

    # Add defaults to comfyui block
    if "loraName" not in s:
        # Insert after schedulerName
        pat = r"(schedulerName:\s*\"\",\s*\n)"
        repl = r'\1            loraName: "",\n            loraStrengthModel: 1.0,\n            loraStrengthClip: 1.0,\n'
        s2, n = re.subn(pat, repl, s, count=1)
        if n == 0:
            raise RuntimeError("config.js: could not insert comfyui LoRA defaults (schedulerName anchor missing)")
        s = s2
        changed = True

    # Add form reads
    if 'getElementById("comfyui-lora")' not in s:
        anchor = 'const comfyuiScheduler = document\n      .getElementById("comfyui-scheduler")\n      ?.value?.trim();'
        if anchor not in s:
            raise RuntimeError("config.js: could not find comfyuiScheduler read block")
        insert = anchor + '\n    const comfyuiLora = document\n      .getElementById("comfyui-lora")\n      ?.value?.trim();\n    const comfyuiLoraStrengthModel = document\n      .getElementById("comfyui-lora-strength-model")\n      ?.value?.trim();\n    const comfyuiLoraStrengthClip = document\n      .getElementById("comfyui-lora-strength-clip")\n      ?.value?.trim();'
        s = s.replace(anchor, insert, 1)
        changed = True

    # Add save into config
    if "api.image.comfyui.loraName" not in s:
        anchor = "this.config.api.image.comfyui.schedulerName = comfyuiScheduler || \"\";"
        if anchor not in s:
            raise RuntimeError("config.js: could not find schedulerName assignment anchor")
        insert = anchor + """
    }

    if (comfyuiLora !== undefined) {
      this.config.api.image.comfyui.loraName = comfyuiLora || "";
    }
    if (comfyuiLoraStrengthModel !== undefined) {
      const v = parseFloat(comfyuiLoraStrengthModel);
      this.config.api.image.comfyui.loraStrengthModel = Number.isFinite(v) ? v : 1.0;
    }
    if (comfyuiLoraStrengthClip !== undefined) {
      const v = parseFloat(comfyuiLoraStrengthClip);
      this.config.api.image.comfyui.loraStrengthClip = Number.isFinite(v) ? v : 1.0;
    }
"""
        s = s.replace(anchor, insert, 1)
        changed = True

    # SaveToForm: element refs
    if 'getElementById("comfyui-lora")' not in s.split("saveToForm", 1)[-1]:
        anchor = 'const comfyuiScheduler = document.getElementById("comfyui-scheduler");'
        if anchor not in s:
            raise RuntimeError("config.js: could not find comfyuiScheduler element anchor in saveToForm()")
        insert = anchor + '\n      const comfyuiLora = document.getElementById("comfyui-lora");\n      const comfyuiLoraStrengthModel = document.getElementById("comfyui-lora-strength-model");\n      const comfyuiLoraStrengthClip = document.getElementById("comfyui-lora-strength-clip");'
        s = s.replace(anchor, insert, 1)
        changed = True

    # SaveToForm: values
    if "loraStrengthModel" not in s.split("saveToForm", 1)[-1]:
        anchor = 'comfyuiScheduler.value = this.config.api.image.comfyui?.schedulerName || "";'
        if anchor not in s:
            raise RuntimeError("config.js: could not find comfyuiScheduler value anchor in saveToForm()")
        insert = anchor + """
      if (comfyuiLora)
        comfyuiLora.value = this.config.api.image.comfyui?.loraName || "";
      if (comfyuiLoraStrengthModel)
        comfyuiLoraStrengthModel.value = (this.config.api.image.comfyui?.loraStrengthModel ?? 1.0);
      if (comfyuiLoraStrengthClip)
        comfyuiLoraStrengthClip.value = (this.config.api.image.comfyui?.loraStrengthClip ?? 1.0);
"""
        s = s.replace(anchor, insert, 1)
        changed = True

    if changed:
        write_text(CFG, s, nl)
        print("config.js: added LoRA persistence (name + strengths)")
    else:
        print("config.js: no changes needed")


def patch_main():
    s, nl = read_text(MAIN)
    changed = False

    # Add inputs to the auto-save selector list
    if "#comfyui-lora" not in s:
        # only patch the selector list line (best-effort)
        pat = r'("#text-api-base,[^"]*#image-cfg-scale")'
        m = re.search(pat, s)
        if m:
            original = m.group(1)
            updated = original[:-1] + ", #comfyui-sampler, #comfyui-scheduler, #comfyui-lora, #comfyui-lora-strength-model, #comfyui-lora-strength-clip\""
            s = s.replace(original, updated, 1)
            changed = True

    # Add loadComfyLoras() method if missing
    if "async loadComfyLoras()" not in s:
        anchor = "async loadComfyCheckpoints() {"
        pos = s.find(anchor)
        if pos == -1:
            raise RuntimeError("main.js: could not find insertion anchor loadComfyCheckpoints()")

        method = """
  async loadComfyLoras() {
    const provider = document.getElementById("image-provider")?.value || "sdapi";
    const family = document.getElementById("comfyui-workflow-family")?.value || "sd_basic";

    const group = document.getElementById("comfyui-lora-group");
    const strengthsGroup = document.getElementById("comfyui-lora-strengths-group");
    const select = document.getElementById("comfyui-lora");
    const strengthModelEl = document.getElementById("comfyui-lora-strength-model");
    const strengthClipEl = document.getElementById("comfyui-lora-strength-clip");
    if (!group || !select) return;

    const shouldShow = provider === "comfyui" && (family === "sd_basic");
    group.style.display = shouldShow ? "block" : "none";
    if (!shouldShow) {
      if (strengthsGroup) strengthsGroup.style.display = "none";
      return;
    }

    // Toggle strengths visibility on change (bind once)
    if (!select.dataset.boundStrengthToggle) {
      select.addEventListener("change", () => {
        if (strengthsGroup) strengthsGroup.style.display = select.value ? "block" : "none";
      });
      select.dataset.boundStrengthToggle = "1";
    }

    const comfyBaseUrl =
      document.getElementById("comfyui-base-url")?.value?.trim() ||
      this.config.get("api.image.comfyui.baseUrl");

    if (!comfyBaseUrl) {
      select.innerHTML = '<option value="">Set ComfyUI Base URL to load LoRAs</option>';
      if (strengthsGroup) strengthsGroup.style.display = "none";
      return;
    }

    const current = this.config.get("api.image.comfyui.loraName") || "";
    const sm = this.config.get("api.image.comfyui.loraStrengthModel");
    const sc = this.config.get("api.image.comfyui.loraStrengthClip");

    if (strengthModelEl) strengthModelEl.value = Number.isFinite(parseFloat(sm)) ? parseFloat(sm) : 1.0;
    if (strengthClipEl) strengthClipEl.value = Number.isFinite(parseFloat(sc)) ? parseFloat(sc) : 1.0;

    if (strengthsGroup) strengthsGroup.style.display = current ? "block" : "none";
    select.innerHTML = '<option value="">Loading LoRAs…</option>';

    try {
      const resp = await fetch("/api/comfy/models/loras", {
        method: "GET",
        headers: { "X-API-URL": comfyBaseUrl },
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || resp.statusText);

      let data = null;
      try { data = JSON.parse(text); } catch { data = null; }

      let items = [];
      if (Array.isArray(data)) items = data;
      else if (data && Array.isArray(data.models)) items = data.models;
      else if (data && Array.isArray(data.loras)) items = data.loras;

      items = items.filter(Boolean).map(String);
      items.sort((a, b) => a.localeCompare(b));

      select.innerHTML = "";
      const optNone = document.createElement("option");
      optNone.value = "";
      optNone.textContent = "(none)";
      select.appendChild(optNone);

      for (const name of items) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      }

      // Preserve saved value even if missing
      if (current && !items.includes(current)) {
        const opt = document.createElement("option");
        opt.value = current;
        opt.textContent = `⚠ missing: ${current}`;
        select.appendChild(opt);
      }

      select.value = current || "";
    } catch (e) {
      console.warn("Failed to load ComfyUI LoRAs:", e);
      select.innerHTML = '<option value="">Failed to load LoRAs (see console)</option>';
      if (strengthsGroup) strengthsGroup.style.display = "none";
    }
  }
""".strip("\n")

        s = s[:pos] + method + "\n\n" + s[pos:]
        changed = True

    # Wire calls: whenever checkpoints/sampler-scheduler load is invoked, also load loras
    def ensure_call_block(src: str):
        # Add after loadComfySamplerScheduler() calls if not already near it
        out = []
        i = 0
        while True:
            j = src.find("this.loadComfySamplerScheduler();", i)
            if j == -1:
                out.append(src[i:])
                break
            out.append(src[i:j])
            k = j + len("this.loadComfySamplerScheduler();")
            tail = src[k:k+120]
            if "this.loadComfyLoras();" in tail:
                out.append("this.loadComfySamplerScheduler();")
            else:
                out.append("this.loadComfySamplerScheduler();\n    this.loadComfyLoras();")
            i = k
        return "".join(out)

    s2 = ensure_call_block(s)
    if s2 != s:
        s = s2
        changed = True

    if changed:
        write_text(MAIN, s, nl)
        print("main.js: added LoRA loader + wired into UI refresh paths")
    else:
        print("main.js: no changes needed")


def patch_api():
    s, nl = read_text(API)
    changed = False

    if "injectSdBasicLora(" not in s:
        # Add helper method after fetchComfyViewBlob() (near ComfyUI helpers)
        anchor = "async fetchComfyViewBlob("
        pos = s.find(anchor)
        if pos == -1:
            raise RuntimeError("api.js: could not find fetchComfyViewBlob() anchor")

        insert_pos = s.rfind("}", 0, pos)
        if insert_pos == -1:
            raise RuntimeError("api.js: could not find insertion point before fetchComfyViewBlob()")

        method = """
  injectSdBasicLora(workflow, loraName, strengthModel, strengthClip) {
    if (!workflow || typeof workflow !== "object") return workflow;

    const requiredNodes = ["3", "4", "6", "7"];
    for (const id of requiredNodes) {
      if (!workflow[id] || !workflow[id].inputs) {
        throw new Error(`sd_basic workflow missing required node ${id} for LoRA injection`);
      }
    }

    const keys = Object.keys(workflow);
    const nums = keys
      .map((k) => (/^\\d+$/.test(k) ? parseInt(k, 10) : None))
      .filter((v) => typeof v == "number" and v == v)
    # (above line is invalid JS in Python context; ignore)
    return workflow;
  }
""".strip("\n")

        # We can't insert invalid JS. We'll insert a real JS method using string literal below.
        js_method = """
  injectSdBasicLora(workflow, loraName, strengthModel, strengthClip) {
    if (!workflow || typeof workflow !== "object") return workflow;

    // Expect sd_basic node ids:
    // 3: KSampler
    // 4: CheckpointLoaderSimple
    // 6/7: CLIPTextEncode
    const required = ["3", "4", "6", "7"];
    for (const id of required) {
      if (!workflow[id] || !workflow[id].inputs) {
        throw new Error(`sd_basic workflow missing required node ${id} for LoRA injection`);
      }
    }

    // Pick a new numeric node id
    const numericIds = Object.keys(workflow)
      .filter((k) => /^\\d+$/.test(k))
      .map((k) => parseInt(k, 10))
      .filter((n) => Number.isFinite(n));
    const nextIdNum = (numericIds.length ? Math.max(...numericIds) : 0) + 1;
    const loraId = String(nextIdNum);

    // Insert LoraLoader node
    workflow[loraId] = {
      inputs: {
        lora_name: String(loraName),
        strength_model: Number.isFinite(strengthModel) ? strengthModel : 1.0,
        strength_clip: Number.isFinite(strengthClip) ? strengthClip : 1.0,
        model: ["4", 0],
        clip: ["4", 1],
      },
      class_type: "LoraLoader",
      _meta: { title: "Load LoRA" },
    };

    // Rewire: KSampler.model and CLIPTextEncode.clip to LoRA outputs
    workflow["3"].inputs.model = [loraId, 0];
    if (workflow["6"]?.inputs) workflow["6"].inputs.clip = [loraId, 1];
    if (workflow["7"]?.inputs) workflow["7"].inputs.clip = [loraId, 1];

    return workflow;
  }
""".strip("\n")

        # Insert the JS method just before fetchComfyViewBlob (at the line break before it)
        s = s[:pos] + js_method + "\n\n  " + s[pos:]
        changed = True

    # Wire injection into generateImageViaComfyUI()
    if "injectSdBasicLora(" not in s.split("generateImageViaComfyUI", 1)[-1]:
        # Add config reads + use finalWorkflow in submit
        # 1) After values object is created, compute lora settings
        anchor = "const values = {"
        if anchor not in s:
            raise RuntimeError("api.js: could not find values object anchor")
        # We won't alter values; we'll add separate reads later.

        # 2) Replace submit body prompt: boundWorkflow -> finalWorkflow
        if "prompt: boundWorkflow" in s:
            s = s.replace("prompt: boundWorkflow", "prompt: finalWorkflow", 1)
            changed = True

        # 3) After bindings applied, set finalWorkflow and inject if needed
        anchor2 = "const boundWorkflow = window.comfyWorkflow.applyBindings("
        p = s.find(anchor2)
        if p == -1:
            raise RuntimeError("api.js: could not find boundWorkflow applyBindings anchor")
        # Find end of that statement (the next ');' after it)
        end = s.find(");", p)
        if end == -1:
            raise RuntimeError("api.js: could not find end of applyBindings call")
        end += 2

        inject_block = """
    // Optional LoRA injection for sd_basic (adds a LoraLoader node and rewires model/clip)
    const loraNameRaw = this.config.get("api.image.comfyui.loraName");
    const loraName = loraNameRaw ? String(loraNameRaw).trim() : "";
    const smRaw = this.config.get("api.image.comfyui.loraStrengthModel");
    const scRaw = this.config.get("api.image.comfyui.loraStrengthClip");
    const strengthModel = Number.isFinite(parseFloat(smRaw)) ? parseFloat(smRaw) : 1.0;
    const strengthClip = Number.isFinite(parseFloat(scRaw)) ? parseFloat(scRaw) : 1.0;

    let finalWorkflow = boundWorkflow;
    if ((family || "sd_basic") === "sd_basic" && loraName) {
      finalWorkflow = this.injectSdBasicLora(finalWorkflow, loraName, strengthModel, strengthClip);
    }
""".rstrip()

        # Only insert if finalWorkflow isn't already defined nearby
        tail = s[end:end+500]
        if "finalWorkflow" not in tail:
            s = s[:end] + "\n\n" + inject_block + "\n\n" + s[end:]
            changed = True

    if changed:
        write_text(API, s, nl)
        print("api.js: added sd_basic LoRA injection into ComfyUI workflow")
    else:
        print("api.js: no changes needed")


def main():
    for p in [INDEX, CFG, MAIN, API]:
        if not p.exists():
            raise RuntimeError(f"Missing file: {p} (run from repo root)")

    patch_index()
    patch_config()
    patch_main()
    patch_api()
    print("OK: LoRA Phase1 patch applied.")


if __name__ == "__main__":
    main()
