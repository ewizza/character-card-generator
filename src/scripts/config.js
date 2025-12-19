// Configuration file for SillyTavern Character Generator
const LOCAL_STORAGE_KEY = "charGeneratorConfig";
const SESSION_STORAGE_KEYS = {
  textApiKey: "charGeneratorConfig:textApiKey",
  imageApiKey: "charGeneratorConfig:imageApiKey",
};

class Config {
  constructor() {
    this.config = this.getDefaultConfig();
    this.debugMode = false; // Toggle for verbose logging
    this.loadConfig().catch(console.error);
  }

  // Treat local/private-network APIs as "no key required" by default.
  // This enables KoboldCpp (and other local servers) which often do not use API keys.
  isLikelyLocalApi(url) {
    try {
      if (!url || typeof url !== "string") return false;
      const trimmed = url.trim();
      if (!trimmed) return false;

      // Ensure URL parser has a scheme
      const withScheme = /^https?:\/\//i.test(trimmed)
        ? trimmed
        : `http://${trimmed}`;
      const u = new URL(withScheme);
      const host = (u.hostname || "").toLowerCase();

      if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0") {
        return true;
      }
      // RFC1918
      if (/^10\./.test(host)) return true;
      if (/^192\.168\./.test(host)) return true;
      const m172 = host.match(/^172\.(\d+)\./);
      if (m172) {
        const second = parseInt(m172[1], 10);
        if (second >= 16 && second <= 31) return true;
      }

      return false;
    } catch {
      return false;
    }
  }

  getDefaultConfig() {
    return {
      api: {
        text: {
          baseUrl: "",
          apiKey: "",
          model: "",
          timeout: 60000,
        },
        image: {
          // Phase 1: allow selecting between SDAPI-style endpoints (Kobold/A1111)
          // and ComfyUI (Basic workflows). Later phases will expand this.
          provider: "sdapi",
          baseUrl: "",
          apiKey: "",
          model: "",
          width: 1024,
          height: 1024,
          sampler: "Euler",
          steps: 28,
          cfgScale: 7,
          timeout: 60000,

          // ComfyUI settings (Phase 1 scaffolding)
          comfyui: {
            baseUrl: "http://127.0.0.1:8188",
            workflowFamily: "sd_basic",
          },
        },
      },
      app: {
        maxRetries: 3,
        retryDelay: 1000,
        debugMode: false,
        persistApiKeys: false,
        enableImageGeneration: true,
      },
      prompts: {
        selectedPresetId: "third_person",
        customPresets: {},
      },
    };
  }

  // Toggle debug mode for verbose logging
  setDebugMode(enabled) {
    this.debugMode = enabled;
    this.config.app.debugMode = enabled;
    this.saveConfig();
    console.log(`Debug mode ${enabled ? "enabled" : "disabled"}`);
  }

  getDebugMode() {
    return this.debugMode || this.config.app.debugMode || false;
  }

  log(...args) {
    if (this.getDebugMode()) {
      console.log(...args);
    }
  }

  async loadConfig() {
    // Load from localStorage
    const savedConfig = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (savedConfig) {
      try {
        const saved = JSON.parse(savedConfig);
        this.stripPersistedApiKeys(saved);
        this.config = this.deepMerge(this.config, saved);
        this.migrateLegacyImageSize();
        this.logRedacted("Loaded config from storage:", saved);
      } catch (error) {
        console.warn("Failed to load saved config:", error);
      }
    }

    this.restoreSensitiveValuesFromSession();

    // Load debug mode setting
    this.debugMode = this.config.app.debugMode || false;

    this.logRedacted("Final config:", this.config);
  }

  loadFromForm() {
    // Load text API settings from form
    const textBaseUrl = document.getElementById("text-api-base")?.value?.trim();
    const textApiKey = document.getElementById("text-api-key")?.value?.trim();
    const textModel = document.getElementById("text-model")?.value?.trim();
    const imageSteps = document.getElementById("image-steps")?.value?.trim();
    const imageCfgScale = document.getElementById("image-cfg-scale")?.value?.trim();


    if (textBaseUrl !== undefined) this.config.api.text.baseUrl = textBaseUrl;
    if (textApiKey !== undefined) this.config.api.text.apiKey = textApiKey;
    if (textModel !== undefined) this.config.api.text.model = textModel;
    if (imageSteps !== undefined) this.config.api.image.steps = this.normalizeSteps(imageSteps, this.config.api.image.steps);
    if (imageCfgScale !== undefined) this.config.api.image.cfgScale = this.normalizeCfgScale(imageCfgScale, this.config.api.image.cfgScale);


    // No special handling needed when using proxy server

    // Load image API settings from form
    const imageBaseUrl = document
      .getElementById("image-api-base")
      ?.value?.trim();
    const imageApiKey = document.getElementById("image-api-key")?.value?.trim();
    const imageModel = document.getElementById("image-model")?.value?.trim();
    const imageWidth = document.getElementById("image-width")?.value?.trim();
    const imageHeight = document.getElementById("image-height")?.value?.trim();
    const imageSampler = document.getElementById("image-sampler")?.value?.trim();

    // Provider (Phase 1 scaffolding)
    const imageProvider = document
      .getElementById("image-provider")
      ?.value?.trim();
    const comfyuiBaseUrl = document
      .getElementById("comfyui-base-url")
      ?.value?.trim();
    const comfyuiWorkflowFamily = document
      .getElementById("comfyui-workflow-family")
      ?.value?.trim();

    if (imageBaseUrl !== undefined)
      this.config.api.image.baseUrl = imageBaseUrl;
    if (imageProvider !== undefined && imageProvider) {
      this.config.api.image.provider = imageProvider;
    }
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

    // ComfyUI settings (Phase 1 scaffolding)
    if (comfyuiBaseUrl !== undefined && comfyuiBaseUrl) {
      this.config.api.image.comfyui.baseUrl = comfyuiBaseUrl;
    }
    if (comfyuiWorkflowFamily !== undefined && comfyuiWorkflowFamily) {
      this.config.api.image.comfyui.workflowFamily = comfyuiWorkflowFamily;
    }

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

    // Load toggle states
    const persistApiKeys = document.getElementById("persist-api-keys")?.checked;
    if (persistApiKeys !== undefined) {
      this.config.app.persistApiKeys = persistApiKeys;
      // Update storage method when toggle changes
      this.updateStorageMethod();
    }

    const enableImageGeneration = document.getElementById(
      "enable-image-generation",
    )?.checked;
    if (enableImageGeneration !== undefined)
      this.config.app.enableImageGeneration = enableImageGeneration;
  }

  get(path) {
    return path.split(".").reduce((obj, key) => obj && obj[key], this.config);
  }

  set(path, value) {
    const keys = path.split(".");
    const lastKey = keys.pop();
    const target = keys.reduce((obj, key) => {
      if (!obj[key]) obj[key] = {};
      return obj[key];
    }, this.config);
    target[lastKey] = value;
    this.saveConfig();
  }

  saveConfig() {
    const persistableConfig = this.getSanitizedConfigForStorage();
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(persistableConfig));
    this.persistSensitiveValuesToSession();
  }

  saveToForm() {
    // Wait for DOM to be ready
    setTimeout(() => {
      // Save text API to form
      const textBaseUrl = document.getElementById("text-api-base");
      const textApiKey = document.getElementById("text-api-key");
      const textModel = document.getElementById("text-model");

      if (textBaseUrl) textBaseUrl.value = this.config.api.text.baseUrl || "";
      if (textApiKey) textApiKey.value = this.config.api.text.apiKey || "";
      if (textModel) textModel.value = this.config.api.text.model || "";

      // Save image API to form
      const imageBaseUrl = document.getElementById("image-api-base");
      const imageProvider = document.getElementById("image-provider");
      const imageApiKey = document.getElementById("image-api-key");
      const imageModel = document.getElementById("image-model");
      const imageWidth = document.getElementById("image-width");
      const imageHeight = document.getElementById("image-height");
      const imageSampler = document.getElementById("image-sampler");
      const imageSteps = document.getElementById("image-steps");
      const imageCfgScale = document.getElementById("image-cfg-scale");

      const comfyuiBaseUrl = document.getElementById("comfyui-base-url");
      const comfyuiWorkflowFamily = document.getElementById(
        "comfyui-workflow-family",
      );

      if (imageSteps) imageSteps.value = this.config.api.image.steps ?? 28;
      if (imageCfgScale) imageCfgScale.value = this.config.api.image.cfgScale ?? 7;
      if (imageBaseUrl) imageBaseUrl.value = this.config.api.image.baseUrl || "";
      if (imageProvider)
        imageProvider.value = this.config.api.image.provider || "sdapi";
      if (imageApiKey) imageApiKey.value = this.config.api.image.apiKey || "";
      if (imageModel) imageModel.value = this.config.api.image.model || "";
      if (imageWidth)
        imageWidth.value = this.config.api.image.width || 1024;
      if (imageHeight)
        imageHeight.value = this.config.api.image.height || 1024;
      if (imageSampler)
        imageSampler.value = this.config.api.image.sampler || "Euler";

      if (comfyuiBaseUrl)
        comfyuiBaseUrl.value = this.config.api.image.comfyui?.baseUrl || "";
      if (comfyuiWorkflowFamily)
        comfyuiWorkflowFamily.value =
          this.config.api.image.comfyui?.workflowFamily || "sd_basic";

      // Save toggle states
      const persistApiKeys = document.getElementById("persist-api-keys");
      if (persistApiKeys)
        persistApiKeys.checked = this.config.app.persistApiKeys || false;

      const enableImageGeneration = document.getElementById(
        "enable-image-generation",
      );
      if (enableImageGeneration)
        enableImageGeneration.checked =
          this.config.app.enableImageGeneration !== false;
    }, 100);
  }

  deepMerge(target, source) {
    const output = { ...target };
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach((key) => {
        if (this.isObject(source[key])) {
          if (!(key in target)) {
            Object.assign(output, { [key]: source[key] });
          } else {
            output[key] = this.deepMerge(target[key], source[key]);
          }
        } else {
          Object.assign(output, { [key]: source[key] });
        }
      });
    }
    return output;
  }

  normalizeImageDimension(value, fallback = 1024) {
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed)) return fallback;
    const clamped = Math.min(2048, Math.max(64, parsed));
    return Math.round(clamped / 64) * 64;
  }

  normalizeSteps(value, fallback = 28) {
    const parsed = parseInt(value, 10);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(150, Math.max(1, parsed));
  }

normalizeCfgScale(value, fallback = 7) {
    const parsed = parseFloat(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(30, Math.max(1, parsed));
  }


  migrateLegacyImageSize() {
    const imageConfig = this.config?.api?.image;
    if (!imageConfig) return;

    if (imageConfig.size && (!imageConfig.width || !imageConfig.height)) {
      const match = imageConfig.size
        .toLowerCase()
        .match(/(\d+)\s*x\s*(\d+)/);
      if (match) {
        imageConfig.width = this.normalizeImageDimension(match[1], 1024);
        imageConfig.height = this.normalizeImageDimension(match[2], 1024);
      }
    }

    if (imageConfig.size) {
      delete imageConfig.size;
    }
  }

  isObject(item) {
    return item && typeof item === "object" && !Array.isArray(item);
  }

  async waitForConfig() {
    await new Promise((resolve) => setTimeout(resolve, 100));
    return this.config;
  }

  validateConfig() {
    const errors = [];

    // Text API validation
    if (!this.config.api.text.baseUrl) {
      errors.push("Text API base URL is required");
    }
    const textKeyRequired = !this.isLikelyLocalApi(this.config.api.text.baseUrl);
    if (textKeyRequired && !this.config.api.text.apiKey) {
      errors.push("Text API key is required");
    }
    if (!this.config.api.text.model) {
      errors.push("Text model is required");
    }

    // Image API validation (only when image generation is enabled)
    if (this.config.app.enableImageGeneration !== false) {
      if (!this.config.api.image.baseUrl) {
        errors.push("Image API base URL is required (or disable image generation)");
      }
      const imageKeyRequired =
        this.config.api.image.baseUrl &&
        !this.isLikelyLocalApi(this.config.api.image.baseUrl);
      if (imageKeyRequired && !this.config.api.image.apiKey) {
        errors.push("Image API key is required");
      }
    }

    return errors;
  }

  getSanitizedConfigForStorage() {
    const configCopy = JSON.parse(JSON.stringify(this.config));
    if (configCopy.api?.text) {
      configCopy.api.text.apiKey = "";
    }
    if (configCopy.api?.image) {
      configCopy.api.image.apiKey = "";
    }
    return configCopy;
  }

  persistSensitiveValuesToSession() {
    if (this.config.app.persistApiKeys) {
      // Store in localStorage when persistence is enabled
      this.persistLocalStorageValue(
        SESSION_STORAGE_KEYS.textApiKey,
        this.config.api.text.apiKey,
      );
      this.persistLocalStorageValue(
        SESSION_STORAGE_KEYS.imageApiKey,
        this.config.api.image.apiKey,
      );
    } else {
      // Store in sessionStorage when persistence is disabled
      this.persistSessionValue(
        SESSION_STORAGE_KEYS.textApiKey,
        this.config.api.text.apiKey,
      );
      this.persistSessionValue(
        SESSION_STORAGE_KEYS.imageApiKey,
        this.config.api.image.apiKey,
      );
    }
  }

  persistSessionValue(key, value) {
    try {
      if (value) {
        sessionStorage.setItem(key, value);
      } else {
        sessionStorage.removeItem(key);
      }
    } catch (error) {
      console.warn(
        "Unable to persist sensitive config to sessionStorage:",
        error,
      );
    }
  }

  persistLocalStorageValue(key, value) {
    try {
      if (value) {
        localStorage.setItem(key, value);
      } else {
        localStorage.removeItem(key);
      }
    } catch (error) {
      console.warn(
        "Unable to persist sensitive config to localStorage:",
        error,
      );
    }
  }

  restoreSensitiveValuesFromSession() {
    if (this.config.app.persistApiKeys) {
      // Restore from localStorage when persistence is enabled
      const textKey = this.getLocalStorageValue(
        SESSION_STORAGE_KEYS.textApiKey,
      );
      if (textKey !== null) {
        this.config.api.text.apiKey = textKey;
      }
      const imageKey = this.getLocalStorageValue(
        SESSION_STORAGE_KEYS.imageApiKey,
      );
      if (imageKey !== null) {
        this.config.api.image.apiKey = imageKey;
      }
    } else {
      // Restore from sessionStorage when persistence is disabled
      const textKey = this.getSessionValue(SESSION_STORAGE_KEYS.textApiKey);
      if (textKey !== null) {
        this.config.api.text.apiKey = textKey;
      }
      const imageKey = this.getSessionValue(SESSION_STORAGE_KEYS.imageApiKey);
      if (imageKey !== null) {
        this.config.api.image.apiKey = imageKey;
      }
    }
  }

  getSessionValue(key) {
    try {
      return sessionStorage.getItem(key);
    } catch (error) {
      console.warn(
        "Unable to read sensitive config from sessionStorage:",
        error,
      );
      return null;
    }
  }

  getLocalStorageValue(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.warn("Unable to read sensitive config from localStorage:", error);
      return null;
    }
  }

  stripPersistedApiKeys(savedConfig) {
    if (!this.isObject(savedConfig)) {
      return;
    }

    if (savedConfig?.api?.text?.apiKey) {
      console.warn(
        "Discarded persisted text API key. Keys are now stored only for the current session.",
      );
      savedConfig.api.text.apiKey = "";
    }

    if (savedConfig?.api?.image?.apiKey) {
      console.warn(
        "Discarded persisted image API key. Keys are now stored only for the current session.",
      );
      savedConfig.api.image.apiKey = "";
    }
  }

  clearStoredConfig() {
    localStorage.removeItem(LOCAL_STORAGE_KEY);
    Object.values(SESSION_STORAGE_KEYS).forEach((key) => {
      try {
        sessionStorage.removeItem(key);
      } catch (error) {
        console.warn(
          "Unable to clear sessionStorage for sensitive config:",
          error,
        );
      }
    });
    Object.values(SESSION_STORAGE_KEYS).forEach((key) => {
      try {
        localStorage.removeItem(key);
      } catch (error) {
        console.warn(
          "Unable to clear localStorage for sensitive config:",
          error,
        );
      }
    });
  }

  redactSensitiveData(data) {
    if (Array.isArray(data)) {
      return data.map((item) => this.redactSensitiveData(item));
    }

    if (!this.isObject(data)) {
      return data;
    }

    const redacted = {};
    Object.keys(data).forEach((key) => {
      if (key.toLowerCase().includes("apikey")) {
        redacted[key] = data[key] ? "[REDACTED]" : "";
      } else {
        redacted[key] = this.redactSensitiveData(data[key]);
      }
    });
    return redacted;
  }

  logRedacted(message, data) {
    if (this.getDebugMode()) {
      console.log(message, this.redactSensitiveData(data));
    }
  }

  updateStorageMethod() {
    // When changing persistence setting, migrate keys between storage methods
    if (this.config.app.persistApiKeys) {
      // Move from sessionStorage to localStorage
      const textKey = this.getSessionValue(SESSION_STORAGE_KEYS.textApiKey);
      const imageKey = this.getSessionValue(SESSION_STORAGE_KEYS.imageApiKey);

      if (textKey) {
        this.persistLocalStorageValue(SESSION_STORAGE_KEYS.textApiKey, textKey);
        sessionStorage.removeItem(SESSION_STORAGE_KEYS.textApiKey);
      }
      if (imageKey) {
        this.persistLocalStorageValue(
          SESSION_STORAGE_KEYS.imageApiKey,
          imageKey,
        );
        sessionStorage.removeItem(SESSION_STORAGE_KEYS.imageApiKey);
      }
    } else {
      // Move from localStorage to sessionStorage
      const textKey = this.getLocalStorageValue(
        SESSION_STORAGE_KEYS.textApiKey,
      );
      const imageKey = this.getLocalStorageValue(
        SESSION_STORAGE_KEYS.imageApiKey,
      );

      if (textKey) {
        this.persistSessionValue(SESSION_STORAGE_KEYS.textApiKey, textKey);
        localStorage.removeItem(SESSION_STORAGE_KEYS.textApiKey);
      }
      if (imageKey) {
        this.persistSessionValue(SESSION_STORAGE_KEYS.imageApiKey, imageKey);
        localStorage.removeItem(SESSION_STORAGE_KEYS.imageApiKey);
      }
    }
  }
}

// Export singleton instance
window.config = new Config();
