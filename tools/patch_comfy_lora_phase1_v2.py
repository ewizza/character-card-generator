from pathlib import Path
import re
import sys

INDEX = Path("index.html")
CFG   = Path("src/scripts/config.js")
MAIN  = Path("src/scripts/main.js")
API   = Path("src/scripts/api.js")

def read_text(p: Path):
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    s = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    return s, nl

def write_text(p: Path, s: str, nl: str):
    p.write_bytes(s.replace("\n", nl).encode("utf-8"))

def patch_index():
    s, nl = read_text(INDEX)

    if 'id="comfyui-lora-group"' in s:
        print("index.html: LoRA UI already present")
        return

    anchor = '<div class="form-group" id="comfyui-scheduler-group"'
    i = s.find(anchor)
    if i == -1:
        raise RuntimeError("index.html: cannot find comfyui-scheduler-group (did Step 2 land?)")

    # Insert right after the scheduler group's closing </div>
    j = s.find("</div>", i)
    if j == -1:
        raise RuntimeError("index.html: cannot find closing </div> for scheduler group")
    j += len("</div>")

    block = """
                    <div class="form-group" id="comfyui-lora-group" style="display: none;">
                        <label for="comfyui-lora" class="label">LoRA</label>
                        <select id="comfyui-lora" class="input" style="height: 3rem;">
                            <option value="">(none)</option>
                        </select>
                        <p style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">
                            📦 Loaded from ComfyUI <code>/models/loras</code>.
                        </p>
                    </div>

                    <div class="form-group" id="comfyui-lora-strengths-group" style="display: none;">
                        <label class="label">LoRA Strength</label>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                            <div>
                                <label for="comfyui-lora-strength-model" class="label" style="font-size: 0.75rem;">Model</label>
                                <input type="number" id="comfyui-lora-strength-model" class="input" min="-5" max="5" step="0.05" value="1" />
                            </div>
                            <div>
                                <label for="comfyui-lora-strength-clip" class="label" style="font-size: 0.75rem;">CLIP</label>
                                <input type="number" id="comfyui-lora-strength-clip" class="input" min="-5" max="5" step="0.05" value="1" />
                            </div>
                        </div>
                    </div>
""".rstrip("\n")

    s = s[:j] + "\n" + block + "\n" + s[j:]
    write_text(INDEX, s, nl)
    print("index.html: inserted LoRA dropdown + strength inputs")

def patch_config():
    s, nl = read_text(CFG)
    changed = False

    # Remove the accidental duplicate ckptName line in defaults (safe cleanup)
    s2 = re.sub(r"\n\s*ckptName:\s*\"\",\s*\n\s*samplerName:\s*\"\",\s*\n\s*schedulerName:\s*\"\",\s*\n\s*ckptName:\s*\"\",\s*\n",
                "\n            ckptName: \"\",\n            samplerName: \"\",\n            schedulerName: \"\",\n",
                s, count=1)
    if s2 != s:
        s = s2
        changed = True

    # Add comfyui defaults if missing
    if "loraName" not in s:
        anchor = 'schedulerName: "",'
        if anchor not in s:
            raise RuntimeError("config.js: cannot find schedulerName default anchor")
        insert = 'schedulerName: "",\n            loraName: "",\n            loraStrengthModel: 1.0,\n            loraStrengthClip: 1.0,'
        s = s.replace(anchor, insert, 1)
        changed = True

    # loadFromForm: read elements
    if 'getElementById("comfyui-lora")' not in s:
        anchor = 'const comfyuiScheduler = document\n      .getElementById("comfyui-scheduler")\n      ?.value?.trim();'
        if anchor not in s:
            raise RuntimeError("config.js: cannot find comfyuiScheduler read anchor in loadFromForm()")
        insert = anchor + '\n    const comfyuiLora = document\n      .getElementById("comfyui-lora")\n      ?.value?.trim();\n    const comfyuiLoraStrengthModel = document\n      .getElementById("comfyui-lora-strength-model")\n      ?.value?.trim();\n    const comfyuiLoraStrengthClip = document\n      .getElementById("comfyui-lora-strength-clip")\n      ?.value?.trim();'
        s = s.replace(anchor, insert, 1)
        changed = True

    # loadFromForm: persist into config
    if "api.image.comfyui.loraName" not in s:
        anchor = 'this.config.api.image.comfyui.schedulerName = comfyuiScheduler || "";'
        if anchor not in s:
            raise RuntimeError("config.js: cannot find schedulerName assignment anchor in loadFromForm()")
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

    # saveToForm: add element refs
    if 'document.getElementById("comfyui-lora")' not in s.split("saveToForm", 1)[-1]:
        anchor = 'const comfyuiScheduler = document.getElementById("comfyui-scheduler");'
        if anchor not in s:
            raise RuntimeError("config.js: cannot find comfyuiScheduler element anchor in saveToForm()")
        insert = anchor + '\n      const comfyuiLora = document.getElementById("comfyui-lora");\n      const comfyuiLoraStrengthModel = document.getElementById("comfyui-lora-strength-model");\n      const comfyuiLoraStrengthClip = document.getElementById("comfyui-lora-strength-clip");'
        s = s.replace(anchor, insert, 1)
        changed = True

    # saveToForm: set values
    if "loraStrengthModel" not in s.split("saveToForm", 1)[-1]:
        anchor = 'if (comfyuiScheduler)\n        comfyuiScheduler.value = this.config.api.image.comfyui?.schedulerName || "";'
        if anchor not in s:
            raise RuntimeError("config.js: cannot find comfyuiScheduler value set anchor in saveToForm()")
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

    # Add lora inputs to auto-save list
    if "#comfyui-lora" not in s:
        sel_anchor = "#comfyui-checkpoint"
        if sel_anchor in s:
            # append lora selectors near other comfy selectors
            s = s.replace(
                "#comfyui-checkpoint,",
                "#comfyui-checkpoint, #comfyui-sampler, #comfyui-scheduler, #comfyui-lora, #comfyui-lora-strength-model, #comfyui-lora-strength-clip,",
                1
            )
            changed = True

    # Add method if missing
    if "async loadComfyLoras()" not in s:
        insert_before = "async loadComfyCheckpoints() {"
        pos = s.find(insert_before)
        if pos == -1:
            raise RuntimeError("main.js: cannot find loadComfyCheckpoints() to insert before")

        method = """
  async loadComfyLoras() {
    const provider = document.getElementById("image-provider")?.value || "sdapi";
    const family = document.getElementById("comfyui-workflow-family")?.value || "sd_basic";

    const group = document.getElementById("comfyui-lora-group");
    const strengthsGroup = document.getElementById("comfyui-lora-strengths-group");
    const select = document.getElementById("comfyui-lora");
    const smEl = document.getElementById("comfyui-lora-strength-model");
    const scEl = document.getElementById("comfyui-lora-strength-clip");
    if (!group || !select) return;

    const shouldShow = provider === "comfyui" && family === "sd_basic";
    group.style.display = shouldShow ? "block" : "none";
    if (!shouldShow) {
      if (strengthsGroup) strengthsGroup.style.display = "none";
      return;
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
    const sm = parseFloat(this.config.get("api.image.comfyui.loraStrengthModel"));
    const sc = parseFloat(this.config.get("api.image.comfyui.loraStrengthClip"));
    if (smEl) smEl.value = Number.isFinite(sm) ? sm : 1.0;
    if (scEl) scEl.value = Number.isFinite(sc) ? sc : 1.0;

    if (strengthsGroup) strengthsGroup.style.display = current ? "block" : "none";

    if (!select.dataset.boundToggle) {
      select.addEventListener("change", () => {
        if (strengthsGroup) strengthsGroup.style.display = select.value ? "block" : "none";
      });
      select.dataset.boundToggle = "1";
    }

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
      const none = document.createElement("option");
      none.value = "";
      none.textContent = "(none)";
      select.appendChild(none);

      for (const name of items) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      }

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

        s = s[:pos] + method + "\n\n  " + s[pos:]
        changed = True

    # Wire calls wherever sampler/scheduler is refreshed
    def add_after_calls(text: str, call: str, add: str) -> str:
        out = []
        i = 0
        while True:
            j = text.find(call, i)
            if j == -1:
                out.append(text[i:])
                break
            out.append(text[i:j])
            k = j + len(call)
            tail = text[k:k+200]
            if add in tail:
                out.append(call)
            else:
                out.append(call + "\n    " + add)
            i = k
        return "".join(out)

    s2 = add_after_calls(s, "this.loadComfySamplerScheduler();", "this.loadComfyLoras();")
    if s2 != s:
        s = s2
        changed = True

    if changed:
        write_text(MAIN, s, nl)
        print("main.js: added loadComfyLoras() + wired refresh calls")
    else:
        print("main.js: no changes needed")

def patch_api():
    s, nl = read_text(API)
    changed = False

    if "injectSdBasicLora(" not in s:
        # Insert helper method just before fetchComfyViewBlob
        anchor = "async fetchComfyViewBlob("
        pos = s.find(anchor)
        if pos == -1:
            raise RuntimeError("api.js: cannot find fetchComfyViewBlob() anchor")

        helper = """
  injectSdBasicLora(workflow, loraName, strengthModel, strengthClip) {
    if (!workflow || typeof workflow !== "object") return workflow;

    // sd_basic expects: 3=KSampler, 4=CheckpointLoaderSimple, 6/7=CLIPTextEncode
    const required = ["3", "4", "6", "7"];
    for (const id of required) {
      if (!workflow[id] || !workflow[id].inputs) {
        throw new Error(`sd_basic workflow missing required node ${id} for LoRA injection`);
      }
    }

    const numericIds = Object.keys(workflow)
      .filter((k) => /^\\d+$/.test(k))
      .map((k) => parseInt(k, 10))
      .filter((n) => Number.isFinite(n));
    const nextId = String((numericIds.length ? Math.max(...numericIds) : 0) + 1);

    workflow[nextId] = {
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

    workflow["3"].inputs.model = [nextId, 0];
    workflow["6"].inputs.clip = [nextId, 1];
    workflow["7"].inputs.clip = [nextId, 1];

    return workflow;
  }

""".lstrip("\n")

        s = s[:pos] + helper + s[pos:]
        changed = True

    # Ensure we submit finalWorkflow not boundWorkflow
    if "prompt: boundWorkflow" in s:
        s = s.replace("prompt: boundWorkflow", "prompt: finalWorkflow", 1)
        changed = True

    # Insert finalWorkflow selection after applyBindings call
    if "let finalWorkflow = boundWorkflow;" not in s:
        anchor = "const boundWorkflow = window.comfyWorkflow.applyBindings("
        p = s.find(anchor)
        if p == -1:
            raise RuntimeError("api.js: cannot find applyBindings() anchor")
        end = s.find(");", p)
        if end == -1:
            raise RuntimeError("api.js: cannot find end of applyBindings() call")
        end += 2

        inject = """
    // Optional LoRA injection for sd_basic (adds LoraLoader node and rewires model/clip)
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

"""
        s = s[:end] + "\n\n" + inject + s[end:]
        changed = True

    if changed:
        write_text(API, s, nl)
        print("api.js: added sd_basic LoRA injection + submission wiring")
    else:
        print("api.js: no changes needed")

def main():
    for p in (INDEX, CFG, MAIN, API):
        if not p.exists():
            print(f"ERROR: missing {p} (run from repo root).")
            return 1

    patch_index()
    patch_config()
    patch_main()
    patch_api()

    print("OK: LoRA Phase1 v2 applied.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
