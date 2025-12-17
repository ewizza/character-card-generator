const express = require("express");
const cors = require("cors");
const fetch = require("node-fetch");
require("dotenv").config({ path: "../.env" });

const app = express();
const PORT = process.env.PORT || 2426;

// Helpers
function normalizeBase(url) {
  return (url || "").trim().replace(/\/+$/, "");
}

// Treat local/private-network APIs as "no key required" by default.
function isLikelyLocalUrl(url) {
  try {
    if (!url || typeof url !== "string") return false;
    const trimmed = url.trim();
    if (!trimmed) return false;
    const withScheme = /^https?:\/\//i.test(trimmed)
      ? trimmed
      : `http://${trimmed}`;
    const u = new URL(withScheme);
    const host = (u.hostname || "").toLowerCase();

    if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0") {
      return true;
    }
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

// KoboldCpp exposes an A1111-compatible SD API at /sdapi/v1/...
function looksLikeSdApi(url) {
  const u = (url || "").toLowerCase();
  return u.includes("/sdapi") || u.endsWith(":5001") || u.includes(":5001/");
}

function parseSize(sizeStr) {
  const m = (sizeStr || "").toLowerCase().match(/(\d+)\s*x\s*(\d+)/);
  if (!m) return { width: 1024, height: 1024 };
  return { width: parseInt(m[1], 10), height: parseInt(m[2], 10) };
}

function buildSdTxt2ImgUrl(apiUrl) {
  let base = normalizeBase(apiUrl);
  if (base.endsWith("/sdapi/v1/txt2img")) return base;
  if (base.endsWith("/sdapi/v1")) return `${base}/txt2img`;
  // If user supplied an OpenAI compat base like .../v1, strip it.
  if (base.endsWith("/v1")) base = base.slice(0, -3);
  // If user supplied something containing /sdapi/..., trim to root.
  if (base.includes("/sdapi/")) base = base.split("/sdapi/")[0];
  return `${base}/sdapi/v1/txt2img`;
}

// Allow CORS from any origin in production (adjust for security as needed)
const allowedOrigins = [
  "http://localhost:2427",
  "http://127.0.0.1:2427",
  process.env.FRONTEND_URL || "http://localhost:2427",
];

// Enable CORS for the frontend
app.use(
  cors({
    origin: allowedOrigins,
    credentials: true,
  }),
);

app.use(express.json());

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Proxy endpoint for text API
app.post("/api/text/chat/completions", async (req, res) => {
  try {
    const { model, messages, max_tokens, temperature, stream } = req.body;

    const apiKey = req.headers["x-api-key"];
    const apiUrl = req.headers["x-api-url"];

    const textKeyRequired = !isLikelyLocalUrl(apiUrl);
    if (textKeyRequired && !apiKey) {
      console.error("Missing API key in request headers (non-local text API)");
      return res.status(401).json({
        error: {
          code: "401",
          message: "API key required",
          details: "Please configure your Text API key in the settings",
        },
      });
    }

    if (!apiUrl) {
      console.error("Missing API URL in request headers");
      return res.status(400).json({
        error: {
          code: "400",
          message: "API URL required",
          details: "Please configure your Text API Base URL in the settings",
        },
      });
    }

    // Append the endpoint path if not already present
    const fullTextUrl = apiUrl.endsWith("/chat/completions")
      ? apiUrl
      : `${apiUrl}/chat/completions`;

    console.log("Proxying text request to:", fullTextUrl);
	//console.log("Request body: ", requestBody);
    console.log("Model:", model);
    console.log("Messages count:", messages?.length || 0);

    // Add OpenRouter-specific headers if using OpenRouter
    const isOpenRouter = apiUrl.includes("openrouter.ai");
    const additionalHeaders = isOpenRouter
      ? {
          "HTTP-Referer": process.env.FRONTEND_URL || "http://localhost:2427",
          "X-Title": "SillyTavern Character Generator",
        }
      : {};

    const requestBody = {
      model,
      messages,
      max_tokens: max_tokens || 1000,
      temperature: temperature || 0.75,
      stream: stream || false,
    };

    let response;
    if (apiKey) {
      // Try Bearer auth first (most common)
      response = await fetch(fullTextUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
          ...additionalHeaders,
        },
        body: JSON.stringify(requestBody),
      });

      // If Bearer fails with 401, try X-API-Key
      if (response.status === 401) {
        console.log("Bearer auth failed, trying X-API-Key...");
        response = await fetch(fullTextUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
            ...additionalHeaders,
          },
          body: JSON.stringify(requestBody),
        });
      }
    } else {
      // Local servers like KoboldCpp commonly don't require auth
      response = await fetch(fullTextUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...additionalHeaders,
        },
        body: JSON.stringify(requestBody),
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Text API error:", response.status, errorText);
      return res.status(response.status).json({
        error: {
          code: response.status.toString(),
          message: `API Error: ${response.statusText}`,
          details: errorText,
        },
      });
    }

    if (stream) {
      // Handle streaming response
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");

      response.body.on("data", (chunk) => {
        res.write(chunk);
      });

      response.body.on("end", () => {
        res.end();
      });
    } else {
      const data = await response.json();
      res.json(data);
    }
  } catch (error) {
    console.error("Proxy error:", error);
    res.status(500).json({
      error: {
        code: "500",
        message: "Internal server error in proxy",
        details: error.message,
      },
    });
  }
});

// Proxy endpoint for image API
app.post("/api/image/generations", async (req, res) => {
  try {
    const { model, prompt, size } = req.body;

    const apiKey = req.headers["x-api-key"];
    const apiUrl = req.headers["x-api-url"];

    if (!apiUrl) {
      console.error("Missing API URL in request headers");
      return res.status(400).json({
        error: {
          code: "400",
          message: "Image API URL required",
          details: "Please configure your Image API Base URL in the settings",
        },
      });
    }

    // For local endpoints, we can optimistically try SDAPI first and fall back
    // to OpenAI-style /images/generations if SDAPI isn't present.
    const preferSdApi = looksLikeSdApi(apiUrl) || isLikelyLocalUrl(apiUrl);
    const imageKeyRequired = !isLikelyLocalUrl(apiUrl) && !preferSdApi;
    if (imageKeyRequired && !apiKey) {
      console.error("Missing API key in request headers (non-local image API)");
      return res.status(401).json({
        error: {
          code: "401",
          message: "Image API key required",
          details: "Please configure your Image API key in the settings",
        },
      });
    }

    // KoboldCpp Stable Diffusion API (A1111-compatible) adapter
    if (preferSdApi) {
      const { width, height } = parseSize(req.body.size || size);
      const n = Math.max(1, Number(req.body.n || 1));

      const payload = {
        prompt: prompt || req.body.prompt,
        negative_prompt: req.body.negative_prompt,
        width,
        height,
        steps: req.body.steps ?? 30,
        cfg_scale: req.body.cfg_scale ?? 8,
        sampler_name: req.body.sampler_name ?? "Euler",
        seed: req.body.seed,
        batch_size: n,
      };

      const sdUrl = buildSdTxt2ImgUrl(apiUrl);
      console.log("Proxying SDAPI image request to:", sdUrl);
	  console.log("Payload: ", payload);

      const response = await fetch(sdUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        // If SDAPI isn't available, fall back to OpenAI-style images endpoint.
        if (response.status === 404 || response.status === 405 || response.status === 501) {
          console.log(
            `SDAPI not available (HTTP ${response.status}). Falling back to /images/generations...`,
          );
        } else {
          const errorText = await response.text();
          console.error("SDAPI error:", response.status, errorText);
          return res.status(response.status).json({
            error: {
              code: response.status.toString(),
              message: `SDAPI Error: ${response.statusText}`,
              details: errorText,
            },
          });
        }
      } else {
        const data = await response.json();
        const images = Array.isArray(data?.images) ? data.images : [];
        if (images.length === 0) {
          return res.status(500).json({
            error: {
              code: "500",
              message: "SDAPI returned no images",
              details: JSON.stringify(data),
            },
          });
        }

        // Return OpenAI-like format so the frontend doesn't need to change
        return res.json({
          data: images.slice(0, n).map((b64) => ({
            url: b64.startsWith("data:") ? b64 : `data:image/png;base64,${b64}`,
          })),
        });
      }
    }

    // Append the endpoint path if not already present
    const fullImageUrl = apiUrl.endsWith("/images/generations")
      ? apiUrl
      : `${apiUrl}/images/generations`;

    console.log("Proxying image request to:", fullImageUrl);
    console.log("Model:", model);
    console.log("Prompt length:", prompt?.length || 0);

    // Use simplified format for all models, but forward all parameters
    // This supports APIs like NanoGPT that need n, response_format, etc.
    const requestBody = {
      ...req.body,
    };

    // Ensure model is set (should be from req.body, but just in case)
    if (!requestBody.model) requestBody.model = model;
    if (!requestBody.prompt) requestBody.prompt = prompt;

    // Add size only if provided by the client and not already in body
    if (size && !requestBody.size) {
      requestBody.size = size;
    }

    // Add OpenRouter-specific headers if using OpenRouter
    const isOpenRouter = apiUrl.includes("openrouter.ai");
    const additionalHeaders = isOpenRouter
      ? {
          "HTTP-Referer": process.env.FRONTEND_URL || "http://localhost:2427",
          "X-Title": "SillyTavern Character Generator",
        }
      : {};

    let response;
    if (apiKey) {
      // Try Bearer auth first (most common for image APIs)
      response = await fetch(fullImageUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
          ...additionalHeaders,
        },
        body: JSON.stringify(requestBody),
      });

      // If Bearer fails with 401, try X-API-Key
      if (response.status === 401) {
        console.log("Bearer auth failed for image API, trying X-API-Key...");
        response = await fetch(fullImageUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
            ...additionalHeaders,
          },
          body: JSON.stringify(requestBody),
        });
      }
    } else {
      // Local servers may not require auth
      response = await fetch(fullImageUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...additionalHeaders,
        },
        body: JSON.stringify(requestBody),
      });
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Image API error:", response.status, errorText);
      return res.status(response.status).json({
        error: {
          code: response.status.toString(),
          message: `Image API Error: ${response.statusText}`,
          details: errorText,
        },
      });
    }

    const data = await response.json();

    // Handle different response formats flexibly
    // Just pass through whatever the image API returns
    res.json(data);
  } catch (error) {
    console.error("Image proxy error:", error);
    res.status(500).json({
      error: {
        code: "500",
        message: "Internal server error in image proxy",
        details: error.message,
      },
    });
  }
});

// Proxy endpoint for fetching images (CORS bypass)
app.get("/api/proxy-image", async (req, res) => {
  try {
    const imageUrl = req.query.url;

    if (!imageUrl) {
      return res.status(400).json({
        error: {
          code: "400",
          message: "Image URL required",
          details: "Please provide a URL parameter with the image URL",
        },
      });
    }

    console.log("Proxying image request for:", imageUrl);

    const response = await fetch(imageUrl);

    if (!response.ok) {
      console.error(
        "Failed to fetch image:",
        response.status,
        response.statusText,
      );
      return res.status(response.status).json({
        error: {
          code: response.status.toString(),
          message: `Failed to fetch image: ${response.statusText}`,
          details: `Image URL: ${imageUrl}`,
        },
      });
    }

    // Get the image as a buffer
    const imageBuffer = await response.buffer();

    // Set appropriate headers
    const contentType = response.headers.get("content-type") || "image/jpeg";
    res.setHeader("Content-Type", contentType);
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Cache-Control", "public, max-age=31536000");

    // Send the image
    res.send(imageBuffer);
  } catch (error) {
    console.error("Image proxy error:", error);
    res.status(500).json({
      error: {
        code: "500",
        message: "Internal server error in image proxy",
        details: error.message,
      },
    });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Proxy server running on http://localhost:${PORT}`);
  console.log(`📡 Ready to proxy requests to configured APIs`);
  console.log(`🔑 API URLs will be provided via request headers`);
});
