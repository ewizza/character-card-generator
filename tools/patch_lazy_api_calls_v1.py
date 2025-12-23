from pathlib import Path
import re

MAIN = Path("src/scripts/main.js")

if not MAIN.exists():
    raise SystemExit("Run from repo root (src/scripts/main.js not found)")

raw = MAIN.read_bytes()
NL = "\r\n" if b"\r\n" in raw else "\n"
s = raw.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
changed = False

def must_sub(pattern, repl, flags=0, count=1, label=""):
    global s, changed
    s2, n = re.subn(pattern, repl, s, flags=flags, count=count)
    if n == 0:
        raise SystemExit(f"Patch failed: {label or pattern}")
    s = s2
    changed = True

def opt_sub(pattern, repl, flags=0, count=1):
    global s, changed
    s2, n = re.subn(pattern, repl, s, flags=flags, count=count)
    if n:
        s = s2
        changed = True
    return n

# 0) Add instance flag if missing
if "this.apiSettingsIsOpen" not in s:
    n = opt_sub(r"(this\.isGenerating\s*=\s*false\s*;)", r"\1\n\n    this.apiSettingsIsOpen = false;", count=1)
    if not n:
        raise SystemExit("main.js: couldn't insert apiSettingsIsOpen (anchor not found)")

# 1) Remove startup API calls in init() and set status text to idle
init_pat = re.compile(
    r"(async\s+init\(\)\s*\{[\s\S]*?\n\s*this\.initPromptPresets\(\);\s*)([\s\S]*?)(\n\s*\}\n\s*\n\s*\n\s*bindEvents\(\)\s*\{)",
    re.M
)
m = init_pat.search(s)
if not m:
    raise SystemExit("main.js: couldn't locate init() for patching")

prefix, mid, suffix = m.group(1), m.group(2), m.group(3)

mid_new = """
    // Don't attempt any outbound API calls until the user opens API Settings.
    const statusText = document.querySelector("#api-status .status-text");
    if (statusText) statusText.textContent = "API Status: Not checked";
""".rstrip()

s = s[:m.start()] + prefix + "\n" + mid_new + "\n" + suffix + s[m.end():]
changed = True

# 2) Replace checkAPIStatus() fully (timeout + only runs when modal open)
must_sub(
    r"(async\s+checkAPIStatus\(\)\s*\{)[\s\S]*?(\n\s*\}\n\s*saveAPISettings\(\))",
    r"""async checkAPIStatus() {
    const statusElement = document.getElementById("api-status");
    if (!statusElement) return;

    const indicator = statusElement.querySelector(".status-indicator");
    const text = statusElement.querySelector(".status-text");
    if (!indicator || !text) return;

    // Only check when the API settings modal is open.
    if (!this.apiSettingsIsOpen) {
      text.textContent = "API Status: Not checked";
      return;
    }

    text.textContent = "API Status: Checking...";
    indicator.className = "status-indicator";

    try {
      const timeoutMs = 5000;
      const result = await Promise.race([
        this.apiHandler.testConnection(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Connection check timed out")), timeoutMs),
        ),
      ]);

      if (result && result.success) {
        indicator.className = "status-indicator status-online";
        text.textContent = "API Status: Connected";
      } else {
        indicator.className = "status-indicator status-offline";
        text.textContent = `API Status: ${result?.error || "Not configured"}`;
      }
    } catch (error) {
      indicator.className = "status-indicator status-offline";
      text.textContent = `API Status: ${error?.message || error}`;
    }
  }

  saveAPISettings()""",
    flags=re.M,
    count=1,
    label="checkAPIStatus() region"
)

# 3) Replace saveAPISettings() so it does NOTHING unless modal open
must_sub(
    r"\n\s*saveAPISettings\(\)\s*\{[\s\S]*?\n\s*\}\n",
    """
  saveAPISettings() {
    this.config.loadFromForm();
    this.config.saveConfig();

    // Do not connect to any APIs unless the API settings modal is open.
    if (!this.apiSettingsIsOpen) return;

    this.checkAPIStatus();

    const provider =
      document.getElementById("image-provider")?.value ||
      this.config.get("api.image.provider") ||
      "sdapi";

    if (provider === "comfyui") {
      this.loadComfyCheckpoints();
      this.loadComfySamplerScheduler();
      if (typeof this.loadComfyLoras === "function") this.loadComfyLoras();
    } else {
      this.loadImageSamplers();
    }
  }
""".rstrip() + "\n",
    flags=re.M,
    count=1,
    label="saveAPISettings()"
)

# 4) Patch API Settings modal open/close handlers to toggle apiSettingsIsOpen
must_sub(
    r'apiSettingsBtn\.addEventListener\("click",\s*\(\)\s*=>\s*\{[\s\S]*?\}\);\s*',
    """apiSettingsBtn.addEventListener("click", () => {
      modalOverlay.classList.add("show");
      document.body.style.overflow = "hidden"; // Prevent background scrolling
      this.apiSettingsIsOpen = true;

      // Only now do we attempt outbound API calls / dynamic lists.
      this.checkAPIStatus();

      const provider =
        document.getElementById("image-provider")?.value ||
        this.config.get("api.image.provider") ||
        "sdapi";

      if (provider === "comfyui") {
        this.loadComfyCheckpoints();
        this.loadComfySamplerScheduler();
        if (typeof this.loadComfyLoras === "function") this.loadComfyLoras();
      } else {
        this.loadImageSamplers();
      }
    });

""",
    flags=re.M,
    count=1,
    label="API Settings open handler"
)

must_sub(
    r'const closeModal = \(\) => \{[\s\S]*?\};',
    """const closeModal = () => {
      modalOverlay.classList.remove("show");
      document.body.style.overflow = ""; // Restore scrolling
      this.apiSettingsIsOpen = false;
    };""",
    flags=re.M,
    count=1,
    label="closeModal()"
)

# 5) Gate list-loading methods so they NEVER fetch while modal closed
def gate_method(name):
    global s, changed
    pat = re.compile(rf"(async\s+{re.escape(name)}\(\)\s*\{{)", re.M)
    m = pat.search(s)
    if not m:
        return
    after = s[m.end():m.end()+250]
    if "if (!this.apiSettingsIsOpen) return;" in after:
        return
    s = s[:m.end()] + "\n\n    if (!this.apiSettingsIsOpen) return;" + s[m.end():]
    changed = True

for fn in ["loadImageSamplers", "loadComfySamplerScheduler", "loadComfyCheckpoints"]:
    gate_method(fn)

if changed:
    MAIN.write_bytes(s.replace("\n", NL).encode("utf-8"))
    print("main.js: Lazy API gating applied (no outbound calls until API Settings is opened).")
else:
    print("main.js: No changes needed.")
