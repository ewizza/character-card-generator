// ComfyUI workflow binding helper (Phase 1)
//
// This module applies a "bindings" map to an API-format ComfyUI workflow JSON.
// It is intentionally simple and file-driven so Phase 2 can extend it without refactoring.

(() => {
  function deepClone(obj) {
    if (typeof structuredClone === "function") return structuredClone(obj);
    return JSON.parse(JSON.stringify(obj));
  }

  function createRandomSeed() {
    // 0..2147483647 (fits into 32-bit signed int range many samplers/tools expect)
    return Math.floor(Math.random() * 2147483648);
  }

  function mergeDefaults(defaults, values) {
    const out = { ...(defaults || {}) };
    for (const [k, v] of Object.entries(values || {})) {
      if (v !== undefined && v !== null) out[k] = v;
    }
    return out;
  }

  /**
   * Apply bindings to a ComfyUI workflow template.
   *
   * @param {Object} workflowTemplate API-format workflow JSON (nodes keyed by id).
   * @param {Object} bindings Bindings JSON ({ map, defaults, ... }).
   * @param {Object} values Normalized generation request (prompt, negativePrompt, width, height, steps, cfgScale, sampler, scheduler, seed, batchSize).
   * @returns {Object} New workflow JSON ready for POST /prompt.
   */
  function applyBindings(workflowTemplate, bindings, values) {
    if (!workflowTemplate || typeof workflowTemplate !== "object") {
      throw new Error("ComfyUI workflow template is missing or invalid");
    }
    if (!bindings || typeof bindings !== "object") {
      throw new Error("ComfyUI bindings are missing or invalid");
    }
    if (bindings.disabled) {
      throw new Error(
        bindings.note ||
          "This workflow is disabled. Please provide an API-format workflow and bindings.",
      );
    }

    const workflow = deepClone(workflowTemplate);
    const merged = mergeDefaults(bindings.defaults, values);

    // Seed: treat -1 as "random" (common UX pattern)
    if (merged.seed === -1 || merged.seed === "-1") {
      merged.seed = createRandomSeed();
    }

    const map = bindings.map || {};
    for (const [field, targets] of Object.entries(map)) {
      if (!Array.isArray(targets) || targets.length === 0) continue;
      const value = merged[field];
      if (value === undefined || value === null) continue;

      for (const t of targets) {
        const nodeId = String(t.node);
        const inputName = t.input;
        if (!nodeId || !inputName) continue;

        const node = workflow[nodeId];
        if (!node || typeof node !== "object") {
          throw new Error(
            `Bindings refer to missing node id ${nodeId} (field: ${field})`,
          );
        }
        node.inputs = node.inputs || {};
        node.inputs[inputName] = value;
      }
    }

    return workflow;
  }

  // Expose for later Phase 1b wiring.
  window.comfyWorkflow = window.comfyWorkflow || {};
  window.comfyWorkflow.applyBindings = applyBindings;
  window.comfyWorkflow.createRandomSeed = createRandomSeed;
  window.comfyWorkflow.deepClone = deepClone;
})();
