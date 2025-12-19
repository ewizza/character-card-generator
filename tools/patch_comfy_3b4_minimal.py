from pathlib import Path
import re
import sys

ROOT = Path(".")
API = ROOT / "src/scripts/api.js"
MAIN = ROOT / "src/scripts/main.js"
HTML = ROOT / "index.html"

def load(path: Path):
    raw = path.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    txt = raw.decode("utf-8", errors="strict")
    return txt, nl

def save(path: Path, txt: str):
    path.write_text(txt, encoding="utf-8", newline="")

def patch_index(txt: str, NL: str):
    changed = False
    if "host.docker.internal" in txt:
        return txt, False

    m = re.search(r'(<input[^>]*id="comfyui-base-url"[^>]*?/?>)', txt)
    if not m:
        return txt, False

    insert = (
        m.group(1) + NL +
        '                        <p style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">' + NL +
        '                            💡 If the app/proxy runs in Docker, use <code>http://host.docker.internal:8188</code> (Windows). If ComfyUI is in WSL2, ensure port 8188 is reachable from Windows.' + NL +
        "                        </p>"
    )
    txt = txt[:m.start(1)] + insert + txt[m.end(1):]
    return txt, True

def patch_main(txt: str, NL: str):
    # Hide sampler group when provider=ComfyUI
    if "samplerGroup.style.display" in txt:
        return txt, False

    target = 'comfyuiSettings.style.display = provider === "comfyui" ? "block" : "none";'
    idx = txt.find(target)
    if idx == -1:
        return txt, False

    line_end = txt.find(NL, idx)
    if line_end == -1:
        line_end = idx + len(target)

    insertion = (
        NL +
        "      // Phase 1: SDAPI sampler UI does not apply to ComfyUI." + NL +
        '      const samplerEl = document.getElementById("image-sampler");' + NL +
        '      const samplerGroup = samplerEl?.closest?.(".form-group");' + NL +
        '      if (samplerGroup) samplerGroup.style.display = provider === "comfyui" ? "none" : "block";'
    )
    txt = txt[:line_end] + insertion + txt[line_end:]
    return txt, True

def patch_api(txt: str, NL: str):
    changed = False

    # Add node_errors summary to submit failure if not present
    if "nodeErrorSummary" not in txt:
        m = re.search(r"if\s*\(!submitResponse\.ok\)\s*\{([\s\S]*?)\n\s*\}", txt)
        if m and "ComfyUI submit failed" in m.group(0):
            blk = m.group(0)
            if "submitJson?.node_errors" not in blk:
                # Insert summary builder after details is created
                blk2 = re.sub(
                    r"(const details\s*=\s*submitJson\?\.[^\n]*;)",
                    r"\1" + NL +
                    "      const nodeErrors = submitJson?.node_errors;" + NL +
                    '      let nodeErrorSummary = "";' + NL +
                    '      if (nodeErrors && typeof nodeErrors === "object") {' + NL +
                    "        const parts = [];" + NL +
                    "        for (const [nodeId, info] of Object.entries(nodeErrors)) {" + NL +
                    "          const errs = Array.isArray(info?.errors) ? info.errors : [];" + NL +
                    "          for (const e of errs.slice(0, 2)) {" + NL +
                    "            const msg = e?.message || e?.type || \"error\";" + NL +
                    "            const det = e?.details ? ` (${e.details})` : \"\";" + NL +
                    "            parts.push(`node ${nodeId}: ${msg}${det}`);" + NL +
                    "          }" + NL +
                    "        }" + NL +
                    "        if (parts.length) nodeErrorSummary = `\\n` + parts.join(\"\\n\");" + NL +
                    "      }",
                    blk,
                )
                blk2 = blk2.replace("${details}`", "${details}${nodeErrorSummary}`")
                if blk2 != blk:
                    txt = txt.replace(blk, blk2)
                    changed = True

    # Use configured timeout for Comfy polling (min 120s)
    if "waitForComfyOutput(" in txt and "pollTimeoutMs" not in txt:
        call_m = re.search(r"await\s+this\.waitForComfyOutput\([^\)]*\)\s*;", txt)
        if call_m:
            ls = txt.rfind(NL, 0, call_m.start())
            ls = 0 if ls == -1 else ls + len(NL)
            indent = re.match(r"\s*", txt[ls:call_m.start()]).group(0)

            poll_def = (
                indent + "const pollTimeoutMs = (() => {" + NL +
                indent + "  const t = parseInt(this.config.get(\"api.image.timeout\"), 10);" + NL +
                indent + "  const base = Number.isFinite(t) ? t : 120000;" + NL +
                indent + "  return Math.max(120000, base);" + NL +
                indent + "})();" + NL
            )
            txt = txt[:ls] + poll_def + txt[ls:]
            txt = re.sub(r"timeoutMs\s*:\s*120000", "timeoutMs: pollTimeoutMs", txt)
            changed = True

    return txt, changed

def main():
    for p in (API, MAIN, HTML):
        if not p.exists():
            print(f"ERROR: Missing {p}. Run from repo root.")
            return 1

    api, nl_api = load(API)
    mainjs, nl_main = load(MAIN)
    html, nl_html = load(HTML)

    html2, ch1 = patch_index(html, nl_html)
    main2, ch2 = patch_main(mainjs, nl_main)
    api2, ch3 = patch_api(api, nl_api)

    if ch1: save(HTML, html2)
    if ch2: save(MAIN, main2)
    if ch3: save(API, api2)

    print("OK: minimal 3b-4 applied:")
    print(f" - index.html: {'changed' if ch1 else 'no change'}")
    print(f" - src/scripts/main.js: {'changed' if ch2 else 'no change'}")
    print(f" - src/scripts/api.js: {'changed' if ch3 else 'no change'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
