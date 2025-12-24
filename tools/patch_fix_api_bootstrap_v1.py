from __future__ import annotations

from pathlib import Path

ROOT = Path('.')
CFG = ROOT / 'src' / 'scripts' / 'config.js'
INDEX = ROOT / 'index.html'


def read_text(p: Path) -> tuple[str, str]:
    raw = p.read_bytes()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    s = raw.decode('utf-8', errors='strict')
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    return s, nl


def write_text(p: Path, s: str, nl: str) -> None:
    p.write_bytes(s.replace('\n', nl).encode('utf-8'))


def find_method_block(src: str, signature: str) -> tuple[int, int]:
    """Find a JS method block by its signature like 'loadFromForm() {' and return (start,end)."""
    start = src.find(signature)
    if start == -1:
        raise RuntimeError(f"Could not find method signature: {signature}")

    # Find the first opening brace after the signature
    brace_open = src.find('{', start)
    if brace_open == -1:
        raise RuntimeError(f"Could not find '{{' for method: {signature}")

    i = brace_open
    depth = 0
    in_str = None  # type: str | None
    escape = False
    while i < len(src):
        ch = src[i]

        if in_str is not None:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue

        if ch in ('"', "'", '`'):
            in_str = ch
            i += 1
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1

    raise RuntimeError(f"Unterminated brace block for method: {signature}")


def patch_config_loadFromForm() -> bool:
    s, nl = read_text(CFG)

    start, end = find_method_block(s, 'loadFromForm()')

    new_block = '''loadFromForm() {
    // Text API
    const textBaseUrl = document.getElementById("text-api-base")?.value?.trim();
    const textApiKey = document.getElementById("text-api-key")?.value?.trim();
    const textModel = document.getElementById("text-model")?.value?.trim();

    if (textBaseUrl !== undefined) this.config.api.text.baseUrl = textBaseUrl;
    if (textApiKey !== undefined) this.config.api.text.apiKey = textApiKey;
    if (textModel !== undefined) this.config.api.text.model = textModel;

    // Image common
    const imageBaseUrl = document.getElementById("image-api-base")?.value?.trim();
    const imageApiKey = document.getElementById("image-api-key")?.value?.trim();
    const imageModel = document.getElementById("image-model")?.value?.trim();
    const imageWidth = document.getElementById("image-width")?.value?.trim();
    const imageHeight = document.getElementById("image-height")?.value?.trim();
    const imageSampler = document.getElementById("image-sampler")?.value?.trim();
    const imageSteps = document.getElementById("image-steps")?.value?.trim();
    const imageCfgScale = document.getElementById("image-cfg-scale")?.value?.trim();

    // Provider + ComfyUI (Phase 1)
    const imageProvider = document.getElementById("image-provider")?.value?.trim();
    const comfyuiBaseUrl = document.getElementById("comfyui-base-url")?.value?.trim();
    const comfyuiWorkflowFamily = document.getElementById("comfyui-workflow-family")?.value?.trim();
    const comfyuiCheckpoint = document.getElementById("comfyui-checkpoint")?.value?.trim();
    const comfyuiSampler = document.getElementById("comfyui-sampler")?.value?.trim();
    const comfyuiScheduler = document.getElementById("comfyui-scheduler")?.value?.trim();
    const comfyuiLora = document.getElementById("comfyui-lora")?.value?.trim();
    const comfyuiLoraStrengthModel = document.getElementById("comfyui-lora-strength-model")?.value?.trim();
    const comfyuiLoraStrengthClip = document.getElementById("comfyui-lora-strength-clip")?.value?.trim();

    if (imageBaseUrl !== undefined) this.config.api.image.baseUrl = imageBaseUrl;
    if (imageApiKey !== undefined) this.config.api.image.apiKey = imageApiKey;
    if (imageModel !== undefined) this.config.api.image.model = imageModel;

    if (imageWidth !== undefined) {
      this.config.api.image.width = this.normalizeImageDimension(
        imageWidth,
        this.config.api.image.width,
      );
    }

    if (imageHeight !== undefined) {
      this.config.api.image.height = this.normalizeImageDimension(
        imageHeight,
        this.config.api.image.height,
      );
    }

    if (imageSampler !== undefined) this.config.api.image.sampler = imageSampler;

    if (imageSteps !== undefined) {
      this.config.api.image.steps = this.normalizeSteps(
        imageSteps,
        this.config.api.image.steps,
      );
    }

    if (imageCfgScale !== undefined) {
      this.config.api.image.cfgScale = this.normalizeCfgScale(
        imageCfgScale,
        this.config.api.image.cfgScale,
      );
    }

    if (imageProvider !== undefined && imageProvider) {
      this.config.api.image.provider = imageProvider;
    }

    if (!this.config.api.image.comfyui) {
      this.config.api.image.comfyui = {
        baseUrl: "http://127.0.0.1:8188",
        workflowFamily: "sd_basic",
        ckptName: "",
        samplerName: "",
        schedulerName: "",
        loraName: "",
        loraStrengthModel: 1.0,
        loraStrengthClip: 1.0,
      };
    }

    if (comfyuiBaseUrl !== undefined && comfyuiBaseUrl) {
      this.config.api.image.comfyui.baseUrl = comfyuiBaseUrl;
    }

    if (comfyuiWorkflowFamily !== undefined && comfyuiWorkflowFamily) {
      this.config.api.image.comfyui.workflowFamily = comfyuiWorkflowFamily;
    }

    if (comfyuiCheckpoint !== undefined) {
      this.config.api.image.comfyui.ckptName = comfyuiCheckpoint || "";
    }

    if (comfyuiSampler !== undefined) {
      this.config.api.image.comfyui.samplerName = comfyuiSampler || "";
    }

    if (comfyuiScheduler !== undefined) {
      this.config.api.image.comfyui.schedulerName = comfyuiScheduler || "";
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

    // Toggles
    const persistApiKeys = document.getElementById("persist-api-keys")?.checked;
    if (persistApiKeys !== undefined) {
      this.config.app.persistApiKeys = persistApiKeys;
      this.updateStorageMethod();
    }

    const enableImageGeneration = document.getElementById("enable-image-generation")?.checked;
    if (enableImageGeneration !== undefined) {
      this.config.app.enableImageGeneration = enableImageGeneration;
    }
  }'''

    new_s = s[:start] + new_block + s[end:]

    # Clean up orphaned duplicate blocks left by earlier broken patches
    stray_start = '\n\nif (imageSteps !== undefined) {'
    j = new_s.find(stray_start)
    if j != -1:
        k = new_s.find('\n  get(path) {', j)
        if k != -1:
            new_s = new_s[:j] + '\n\n' + new_s[k:]

    if new_s == s:
        print('config.js: loadFromForm already matches expected block (no changes).')
        return False

    write_text(CFG, new_s, nl)
    print('config.js: repaired loadFromForm() (fixes syntax + duplicate blocks).')
    return True


def patch_index_status_text() -> bool:
    if not INDEX.exists():
        return False
    s, nl = read_text(INDEX)
    old = 'API Status: Checking...'
    if old not in s:
        return False
    new_s = s.replace(old, 'API Status: Not checked', 1)
    write_text(INDEX, new_s, nl)
    print('index.html: default API status text set to "Not checked".')
    return True


def main() -> int:
    if not CFG.exists():
        print('ERROR: src/scripts/config.js not found. Run this from repo root.')
        return 1

    changed = False
    changed |= patch_config_loadFromForm()
    changed |= patch_index_status_text()

    if changed:
        print('OK: API bootstrap fix applied.')
    else:
        print('No changes were necessary.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
