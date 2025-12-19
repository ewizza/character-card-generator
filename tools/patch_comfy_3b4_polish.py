from pathlib import Path
import re
import sys

ROOT = Path(".")
API = ROOT / "src/scripts/api.js"
MAIN = ROOT / "src/scripts/main.js"
HTML = ROOT / "index.html"

def detect_nl(raw: bytes) -> str:
    return "\r\n" if b"\r\n" in raw else "\n"

def load_text(path: Path):
    raw = path.read_bytes()
    NL = detect_nl(raw)
    txt = raw.decode("utf-8", errors="strict")
    return txt, NL

def save_text(path: Path, txt: str):
    path.write_text(txt, encoding="utf-8", newline="")

def patch_index(txt: str, NL: str):
    changed = False

    # Sampler label clarifier
    if '<label for="image-sampler" class="label">Sampler</label>' in txt:
        txt = txt.replace(
            '<label for="image-sampler" class="label">Sampler</label>',
            '<label for="image-sampler" class="label">Sampler (SDAPI only)</label>',
        )
        changed = True

    # FLUX label clarifier
    if 'value="flux_basic">FLUX</option>' in txt:
        txt = txt.replace(
            'value="flux_basic">FLUX</option>',
            'value="flux_basic">FLUX (requires export)</option>',
        )
        changed = True

    # ComfyUI Base URL help text (Docker/WSL)
    if "host.docker.internal" not in txt:
        m = re.search(r'(<input[^>]*id="comfyui-base-url"[^>]*?/?>)', txt)
        if m:
            insert = (
                m.group(1)
                + NL
                + '                        <p style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">'
                + NL
                + '                            💡 If the app/proxy runs in Docker, use <code>http://host.docker.internal:8188</code>. If ComfyUI is in WSL2, ensure port 8188 is reachable from Windows.'
                + NL
                + "                        </p>"
            )
            txt = txt[: m.start(1)] + insert + txt[m.end(1) :]
            changed = True

    return txt, changed

def patch_main(txt: str, NL: str):
    changed = False

    # Hide sampler form-group when provider = comfyui
    if "samplerGroup.style.display" in txt:
        return txt, False

    target = 'comfyuiSettings.style.display = provider === "comfyui" ? "block" : "none";'
    idx = txt.find(target)
    if idx != -1:
        line_end = txt.find(NL, idx)
        if line_end == -1:
            line_end = idx + len(target)

        insertion = (
            NL
            + "      // Hide SDAPI-only controls when using ComfyUI (Phase 1)."
            + NL
            + '      const samplerEl = document.getElementById("image-sampler");'
            + NL
            + '      const samplerGroup = samplerEl?.closest?.(".form-group");'
            + NL
            + '      if (samplerGroup) samplerGroup.style.display = provider === "comfyui" ? "none" : "block";'
        )
        txt = txt[:line_end] + insertion + txt[line_end:]
        changed = True

    return txt, changed

def patch_api(txt: str, NL: str):
    changed = False

    # Remove sampler from values object in generateImageViaComfyUI (avoid SDAPI title-case mismatch)
    m = re.search(r"const values\s*=\s*\{([\s\S]*?)\};", txt)
    if m:
        block = m.group(0)
        if "sampler:" in block:
            # remove any line containing sampler:
            new_block = re.sub(rf"{re.escape(NL)}[^\n\r]*sampler\s*:[^\n\r]*", "", block)
            if new_block != block:
                txt = txt[: m.start()] + new_block + txt[m.end() :]
                changed = True

    # Make promptId re-assignable (some users later add retry; harmless now)
    if "const promptId = submitJson?.prompt_id;" in txt:
        txt = txt.replace("const promptId = submitJson?.prompt_id;", "let promptId = submitJson?.prompt_id;")
        changed = True

    # Improve submit error message with node_errors summary (if not already present)
    if "node_errors" not in txt:
        pat = r"if\s*\(!submitResponse\.ok\)\s*\{[\s\S]*?\}"
        mm = re.search(pat, txt)
        if mm:
            blk = mm.group(0)
            if "ComfyUI submit failed" in blk and "nodeErrorSummary" not in blk:
                blk2 = re.sub(
                    r"(const details\s*=\s*submitJson\?\.[\s\S]*?;)",
                    r"\1"
                    + NL
                    + "      const nodeErrors = submitJson?.node_errors;"
                    + NL
                    + '      let nodeErrorSummary = "";'
                    + NL
                    + "      if (nodeErrors && typeof nodeErrors === \"object\") {"
                    + NL
                    + "        const parts = [];"
                    + NL
                    + "        for (const [nodeId, info] of Object.entries(nodeErrors)) {"
                    + NL
                    + "          const errs = Array.isArray(info?.errors) ? info.errors : [];"
                    + NL
                    + "          for (const e of errs.slice(0, 2)) {"
                    + NL
                    + "            const msg = e?.message || e?.type || \"error\";"
                    + NL
                    + "            const det = e?.details ? ` (${e.details})` : \"\";"
                    + NL
                    + "            parts.push(`node ${nodeId}: ${msg}${det}`);"
                    + NL
                    + "          }"
                    + NL
                    + "        }"
                    + NL
                    + "        if (parts.length) nodeErrorSummary = `\\n` + parts.join(\"\\n\");"
                    + NL
                    + "      }",
                    blk,
                )
                blk2 = blk2.replace("${details}`", "${details}${nodeErrorSummary}`")
                if blk2 != blk:
                    txt = txt[: mm.start()] + blk2 + txt[mm.end() :]
                    changed = True

    # Use configured image timeout for Comfy polling (minimum 120s), if 3b-2 helpers exist
    if "waitForComfyOutput(" in txt and "pollTimeoutMs" not in txt:
        call_m = re.search(r"await\s+this\.waitForComfyOutput\([^\)]*\)\s*;", txt)
        if call_m:
            ls = txt.rfind(NL, 0, call_m.start())
            ls = 0 if ls == -1 else ls + len(NL)
            indent = re.match(r"\s*", txt[ls:call_m.start()]).group(0)

            poll_def = (
                indent + "const pollTimeoutMs = (() => {" + NL
                + indent + "  const t = parseInt(this.config.get(\"api.image.timeout\"), 10);" + NL
                + indent + "  const base = Number.isFinite(t) ? t : 120000;" + NL
                + indent + "  return Math.max(120000, base);" + NL
                + indent + "})();" + NL
            )
            txt = txt[:ls] + poll_def + txt[ls:]
            changed = True

            txt2 = re.sub(r"timeoutMs\s*:\s*120000", "timeoutMs: pollTimeoutMs", txt)
            if txt2 != txt:
                txt = txt2
                changed = True

    return txt, changed

def main():
    for p in (API, MAIN, HTML):
        if not p.exists():
            print(f"ERROR: Missing {p}. Run from repo root.")
            return 1

    api_txt, api_nl = load_text(API)
    main_txt, main_nl = load_text(MAIN)
    html_txt, html_nl = load_text(HTML)

    html_txt2, ch_html = patch_index(html_txt, html_nl)
    main_txt2, ch_main = patch_main(main_txt, main_nl)
    api_txt2, ch_api = patch_api(api_txt, api_nl)

    if ch_html:
        save_text(HTML, html_txt2)
    if ch_main:
        save_text(MAIN, main_txt2)
    if ch_api:
        save_text(API, api_txt2)

    print("OK: 3b-4 polish applied:")
    print(f" - index.html: {'changed' if ch_html else 'no change'}")
    print(f" - src/scripts/main.js: {'changed' if ch_main else 'no change'}")
    print(f" - src/scripts/api.js: {'changed' if ch_api else 'no change'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
