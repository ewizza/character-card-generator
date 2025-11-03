// Configuration file for SillyTavern Character Generator
class Config {
  constructor() {
    this.config = this.getDefaultConfig();
    this.debugMode = false; // Toggle for verbose logging
    this.loadConfig().catch(console.error);
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
          baseUrl: "",
          apiKey: "",
          model: "",
          size: "",
          timeout: 60000,
        },
      },
      app: {
        maxRetries: 3,
        retryDelay: 1000,
        debugMode: false,
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
    const savedConfig = localStorage.getItem("charGeneratorConfig");
    if (savedConfig) {
      try {
        const saved = JSON.parse(savedConfig);
        this.config = this.deepMerge(this.config, saved);
        this.log("Loaded config from localStorage:", saved);
      } catch (error) {
        console.warn("Failed to load saved config:", error);
      }
    }

    // Load debug mode setting
    this.debugMode = this.config.app.debugMode || false;

    this.log("Final config:", this.config);
    this.log(
      "Text API Key (first 10 chars):",
      this.config.api.text.apiKey
        ? `${this.config.api.text.apiKey.substring(0, 10)}...`
        : "null",
    );
    this.log("Text API Key length:", this.config.api.text.apiKey?.length || 0);
  }

  loadFromForm() {
    // Load text API settings from form
    const textBaseUrl = document.getElementById("text-api-base")?.value?.trim();
    const textApiKey = document.getElementById("text-api-key")?.value?.trim();
    const textModel = document.getElementById("text-model")?.value?.trim();

    if (textBaseUrl !== undefined) this.config.api.text.baseUrl = textBaseUrl;
    if (textApiKey !== undefined) this.config.api.text.apiKey = textApiKey;
    if (textModel !== undefined) this.config.api.text.model = textModel;

    // No special handling needed when using proxy server

    // Load image API settings from form
    const imageBaseUrl = document
      .getElementById("image-api-base")
      ?.value?.trim();
    const imageApiKey = document.getElementById("image-api-key")?.value?.trim();
    const imageModel = document.getElementById("image-model")?.value?.trim();
    const imageSize = document.getElementById("image-size")?.value?.trim();

    if (imageBaseUrl !== undefined)
      this.config.api.image.baseUrl = imageBaseUrl;
    if (imageApiKey !== undefined) this.config.api.image.apiKey = imageApiKey;
    if (imageModel !== undefined) this.config.api.image.model = imageModel;
    if (imageSize !== undefined) this.config.api.image.size = imageSize;
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
    localStorage.setItem("charGeneratorConfig", JSON.stringify(this.config));
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
      const imageApiKey = document.getElementById("image-api-key");
      const imageModel = document.getElementById("image-model");
      const imageSize = document.getElementById("image-size");

      if (imageBaseUrl)
        imageBaseUrl.value = this.config.api.image.baseUrl || "";
      if (imageApiKey) imageApiKey.value = this.config.api.image.apiKey || "";
      if (imageModel) imageModel.value = this.config.api.image.model || "";
      if (imageSize) imageSize.value = this.config.api.image.size || "";
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
    if (!this.config.api.text.apiKey) {
      errors.push("Text API key is required");
    }
    if (!this.config.api.text.model) {
      errors.push("Text model is required");
    }

    return errors;
  }
}

// Export singleton instance
window.config = new Config();
