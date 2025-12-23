from pathlib import Path
import re

MAIN = Path('src/scripts/main.js')
if not MAIN.exists():
    raise SystemExit('ERROR: src/scripts/main.js not found. Run from repo root.')

raw = MAIN.read_bytes()
NL = '\r\n' if b'\r\n' in raw else '\n'
text = raw.decode('utf-8', errors='strict').replace('\r\n', '\n').replace('\r', '\n')

m_start = re.search(r"\n\s*async\s+loadComfyLoras\(\)\s*\{", text)
if not m_start:
    raise SystemExit('ERROR: Could not find loadComfyLoras() in main.js')

start = m_start.start()

m_end = re.search(r"\n\s*async\s+loadComfyCheckpoints\(\)\s*\{", text[start + 1 :])
end = (start + 1 + m_end.start()) if m_end else len(text)

sub = text[start:end]
orig = sub

# 1) Gate loadComfyLoras behind the modal open flag
if 'if (!this.apiSettingsIsOpen) return;' not in sub[:250]:
    sub2, n = re.subn(
        r"(\n\s*async\s+loadComfyLoras\(\)\s*\{\n)",
        r"\1    if (!this.apiSettingsIsOpen) return;\n",
        sub,
        count=1,
    )
    if n == 0:
        raise SystemExit('ERROR: Failed to insert apiSettingsIsOpen guard in loadComfyLoras()')
    sub = sub2

# 2) Add an 'input' listener as well
if 'addEventListener("input"' not in sub:
    marker = 'select.dataset.boundToggle'
    if marker in sub:
        sub = sub.replace(
            marker,
            'select.addEventListener("input", () => {\n'
            '        if (strengthsGroup) strengthsGroup.style.display = select.value ? "block" : "none";\n'
            '      });\n      ' + marker,
            1,
        )

# 3) Ensure strengths visibility is updated after we set select.value programmatically
if 'select.value = current || ""' in sub:
    already = re.search(
        r"select\.value\s*=\s*current\s*\|\|\s*\"\";\s*\n\s*if\s*\(strengthsGroup\)\s*strengthsGroup\.style\.display\s*=\s*select\.value",
        sub,
    )
    if not already:
        sub = sub.replace(
            'select.value = current || "";',
            'select.value = current || "";\n'
            '      if (strengthsGroup) strengthsGroup.style.display = select.value ? "block" : "none";',
            1,
        )

if sub == orig:
    print('main.js: no changes needed (toggle already present)')
    raise SystemExit(0)

text2 = text[:start] + sub + text[end:]
MAIN.write_bytes(text2.replace('\n', NL).encode('utf-8'))
print('OK: main.js updated so LoRA strengths show/hide immediately and loadComfyLoras is gated by modal open.')
