from pathlib import Path
import re
import sys

MAIN = Path("src/scripts/main.js")

if not MAIN.exists():
    print("ERROR: src/scripts/main.js not found. Run this from the repo root.")
    sys.exit(1)

raw = MAIN.read_bytes()
nl = "\r\n" if b"\r\n" in raw else "\n"
s = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")

needle = 'if (!select.addEventListener("input", () => {'
if needle not in s:
    print("OK: main.js does not contain the broken LoRA toggle block (nothing to fix).")
    sys.exit(0)

fix_count = 0
while needle in s:
    start = s.find(needle)

    # Find the end of the broken if-block by locating the dataset assignment then the closing brace.
    end_anchor = 'select.dataset.boundToggle = "1";'
    end_anchor_pos = s.find(end_anchor, start)
    if end_anchor_pos == -1:
        print("ERROR: Found broken block start but not the dataset assignment anchor.")
        sys.exit(1)

    # End at the next closing brace after the dataset assignment (this closes the if block).
    end = s.find("}", end_anchor_pos)
    if end == -1:
        print("ERROR: Could not find end of broken if-block.")
        sys.exit(1)
    end += 1

    # Replace from the start of the line containing the broken 'if' through the end brace.
    line_start = s.rfind("\n", 0, start) + 1

    # Determine indentation from the original line
    indent = re.match(r"(\s*)", s[line_start:start]).group(1)

    replacement = "\n".join([
        f"{indent}if (!select.dataset.boundToggle) {{",
        f"{indent}  const toggleStrengths = () => {{",
        f"{indent}    if (strengthsGroup) strengthsGroup.style.display = select.value ? \"block\" : \"none\";",
        f"{indent}  }};",
        f"{indent}  // Change covers mouse selection; input helps with some browser/select behaviors",
        f"{indent}  select.addEventListener(\"change\", toggleStrengths);",
        f"{indent}  select.addEventListener(\"input\", toggleStrengths);",
        f"{indent}  select.dataset.boundToggle = \"1\";",
        f"{indent}}}",
    ])

    s = s[:line_start] + replacement + s[end:]
    fix_count += 1

MAIN.write_bytes(s.replace("\n", nl).encode("utf-8"))
print(f"OK: Repaired broken LoRA strengths toggle block in main.js (patched {fix_count} occurrence(s)).")
