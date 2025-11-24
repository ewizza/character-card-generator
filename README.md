# 🎭 SillyTavern Character Generator

A web application for generating detailed SillyTavern character cards using AI. Create rich character profiles with AI-generated descriptions, personalities, scenarios, and custom artwork.

## ✨ Features

### 🤖 AI-Powered Generation
- **Comprehensive Character Creation**: Generate complete character cards with descriptions, personalities, scenarios, and first messages
- **Streaming Output**: Watch your character come to life with real-time streaming generation
- **Multiple Text APIs**: Works with OpenAI, OpenRouter, and other OpenAI-compatible APIs
- **Advanced Image Generation**: Create stunning character artwork using AI image models
- **Intelligent Prompt Crafting**: Automatically generates optimized image prompts from character descriptions

### 🎨 Image Customization
- **Multiple Generation Options**: 
  - Generate new prompts without creating images
  - Generate images from current or custom prompts
  - Upload your own character images
- **Advanced Prompt Editing**: Fine-tune image prompts with a editor
- **Automatic Prompt Optimization**: AI-powered prompt shortening for optimal results
- **Format Support**: PNG and JPEG image uploads

### 📚 Lorebook Integration
- **World Info Support**: Upload SillyTavern World Info JSON files
- **Context-Aware Generation**: Characters are generated with knowledge of your world's lore
- **Rich World Building**: Integrate custom races, cultures, magic systems, and more

### ⚙️ Flexible Configuration
- **Point of View Selection**: Choose between first-person or third-person narration
- **Editable Fields**: Edit any generated field before downloading
- **Field Reset**: Individual reset buttons to restore AI-generated content
- **API Persistence**: Optional browser storage for API credentials
- **Image Generation Toggle**: Enable/disable automatic image generation to save costs

### 💾 Export Options
- **PNG Character Cards**: Download as SillyTavern-compatible PNG cards with embedded metadata
- **JSON Export**: Export character data as pure JSON
- **Full Compatibility**: Works seamlessly with SillyTavern

### 🌐 Deployment
- **Docker Support**: Easy deployment with Docker Compose
- **Local Development**: Run directly with Node.js
- **CORS Proxy**: Built-in proxy server for API requests

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Tremontaine/character-card-generator
   cd character-card-generator
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env if you want to change default ports
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:2427
   - Backend API: http://localhost:2426

### Option 2: Direct Installation

1. **Install dependencies**:
   ```bash
   npm install
   cd proxy && npm install
   cd ..
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Access the application**:
   - Frontend: http://localhost:2427
   - Backend API: http://localhost:2426

## 📖 Usage Guide

### Initial Setup

1. **Configure API Settings**:
   - Click the "⚙️ API Settings" button in the footer
   - Enter your Text API credentials:
     - **API Base URL**: Your text generation API endpoint (e.g., OpenAI, OpenRouter)
     - **API Key**: Your API key
     - **Model**: Model name (e.g., `gpt-5`)
   
   - *Optional*: Configure Image API settings:
     - **Image API Base URL**: Image generation endpoint
     - **Image API Key**: Image API key
     - **Image Model**: Image model name (e.g., `dall-e-3`, `bytedance/seedream-4`)
     - **Image Size**: Desired image dimensions (e.g., `768x1024`)

2. **Toggle Settings**:
   - **API Key Persistence**: Enable to save API keys across browser sessions
   - **Image Generation**: Disable to skip automatic image generation

### Creating a Character

1. **Enter Character Concept**:
   - Describe your character idea in the "Character Concept" field
   - Example: *"A stoic elven ranger who protects the northern forests, haunted by the loss of her twin sister"*

2. **Optional Settings**:
   - **Character Name**: Leave blank for AI-generated name, or specify your own
   - **Point of View**: Choose first-person ("I am...") or third-person ("She is...")
   - **Lorebook**: Upload a SillyTavern World Info JSON file to incorporate world lore

3. **Generate**:
   - Click "Generate Character"
   - Watch the streaming output as your character is created
   - Use the "Stop" button to halt generation at any time

### Customizing Results

#### Editing Character Fields
- All generated fields are editable:
  - **Description**: Character's physical appearance and background
  - **Personality**: Character traits and behavioral patterns
  - **Scenario**: The situation in which the character is introduced
  - **First Message**: Opening dialogue or narration
- Click "🔄 Reset" buttons to restore original AI-generated content

#### Image Customization

**Regenerate Prompt Only**:
- Click "💡 Prompt" to generate a new image prompt without creating an image
- Review the prompt in the "✏️ Edit Image Prompt" section

**Regenerate Image**:
- Click "🖼️ Image" to generate a new image using the current prompt
- Or expand "✏️ Edit Image Prompt" to customize the prompt first
- Maximum 1000 characters for custom prompts

**Upload Custom Image**:
- Click "📁 Upload" to use your own character artwork
- Supports PNG and JPEG formats

### Exporting

1. **Download Character Card** (Recommended):
   - Click "Download Character Card (PNG)"
   - Creates a SillyTavern-compatible PNG with embedded character data
   - Import directly into SillyTavern

2. **Download JSON**:
   - Click "Download Character JSON"
   - Exports character data as JSON for manual editing or backup

## 🔧 Environment Configuration

The `.env` file supports the following settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_PORT` | `2427` | Port for the frontend web interface |
| `PROXY_PORT` | `2426` | Port for the backend proxy server |
| `FRONTEND_URL` | Auto-generated | Frontend URL for CORS headers |

Example `.env`:
```env
FRONTEND_PORT=2427
PROXY_PORT=2426
# FRONTEND_URL=http://localhost:2427
```

## 🛠️ Technical Details

### Architecture
- **Frontend**: Vanilla HTML/CSS/JavaScript with modern ES6+ features
- **Backend**: Node.js proxy server for secure API communication
- **Styling**: Custom CSS with Inter font, glassmorphism effects, and smooth animations
- **Storage**: Browser localStorage for configuration persistence

### Components
- **Character Generator** (`character-generator.js`): Core generation logic with streaming support
- **Image Generator** (`image-generator.js`): Image prompt creation and generation
- **PNG Encoder** (`png-encoder.js`): Embeds character data in PNG metadata
- **API Handler** (`api.js`): Unified API communication layer
- **Config Manager** (`config.js`): Settings and persistence management

### API Compatibility
The application works with any OpenAI-compatible API:
- OpenAI (GPT-5.1, DALL-E)
- OpenRouter (Claude, Gemini, etc.)
- Local LLMs with OpenAI-compatible endpoints
- Custom API providers

## 🐳 Docker Details

### Services
The `docker-compose.yml` defines three services:

1. **frontend**: Serves the static web interface
2. **proxy**: Backend proxy for API requests

### Building
```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build frontend
```

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f frontend
```

## 📝 License

MIT License - See `LICENSE` file for details

## 🔗 Links

- [SillyTavern](https://github.com/SillyTavern/SillyTavern)
- [OpenAI API](https://platform.openai.com/docs/api-reference)

---

**Note**: This application requires active API credentials for text and image generation. API usage may incur costs based on your provider's pricing.
