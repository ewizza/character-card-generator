# SillyTavern Character Generator

A web application for generating SillyTavern character cards with AI. Create rich, detailed characters for your storytelling and roleplaying adventures using powerful AI language models.

## 🚀 Quick Start

### Docker Deployment (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd character-card-generator

# Create environment file (optional)
cp .env.template .env
# Edit .env with your custom ports if needed

# Build and start with Docker
docker-compose up -d --build

# Access the application
open http://localhost:2427
```

### Local Development

```bash
# Clone and install
git clone <your-repo-url>
cd character-card-generator
npm install
cd proxy && npm install && cd ..

# Create environment file (optional)
cp .env.template .env

# Start development servers
npm run dev

# Access the application
open http://localhost:2427
```

## ⚙️ Configuration

### Port Configuration

The application uses configurable ports to avoid conflicts with other services:

- **Frontend Port**: `2427` (configurable via `FRONTEND_PORT`)
- **Proxy Port**: `2426` (configurable via `PROXY_PORT`)

### Environment Variables

Create a `.env` file from `.env.template`:

```bash
# Frontend port (default: 2427)
FRONTEND_PORT=2427

# Proxy port (default: 2426)
PROXY_PORT=2426

# Frontend URL (auto-generated)
FRONTEND_URL=http://localhost:2427
```

### Custom Port Example

To use different ports (e.g., if 2427 is occupied):

```bash
# Set custom ports in .env
FRONTEND_PORT=3000
PROXY_PORT=3001
FRONTEND_URL=http://localhost:3000

# Restart the application
npm run dev  # or docker-compose up -d --build
```

## 🔧 Development Scripts

```bash
# Development (both frontend + proxy)
npm run dev

# Production-like setup
npm run start

# Frontend only
npm run frontend

# Proxy server only
npm run server

# Python server (alternative)
npm run serve
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Browser       │───▶│   Frontend      │───▶│   Proxy Server  │───▶│   External APIs │
│                 │    │   (Port 2427)   │    │   (Port 2426)   │    │   (OpenAI, etc)│
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

- **Frontend**: Static HTML/JS/CSS served by nginx (Docker) or http-server (local)
- **Proxy Server**: Node.js Express server that handles API requests to external AI services
- **External APIs**: Your configured AI services (OpenAI, Anthropic, etc.)

## 🔌 API Configuration

1. Open the application in your browser
2. Click the settings gear icon
3. Configure your API settings:
   - **Text API**: OpenAI, Anthropic, or compatible API for character generation
   - **Image API**: DALL-E, Midjourney, or compatible API for character portraits

### Required Settings

- **Text API Base URL**: Your API endpoint (e.g., `https://api.openai.com/v1`)
- **Text API Key**: Your API key
- **Text Model**: Model name (e.g., `gpt-3.5-turbo`)
- **Image API Base URL**: Image API endpoint
- **Image API Key**: Your image API key
- **Image Model**: Image model (e.g., `dall-e-3`)

## 🐳 Docker Deployment

### Single Command Deployment

```bash
# Default ports (2427 for frontend, 2426 for proxy)
docker-compose up -d --build
```

### Custom Ports with Docker

```bash
# Create .env file with custom ports
echo "FRONTEND_PORT=3000" > .env
echo "PROXY_PORT=3001" >> .env

# Deploy with custom ports
docker-compose up -d --build
```

### Docker Management

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build

# Access containers
docker-compose exec frontend sh
docker-compose exec proxy sh
```

## 🚨 Troubleshooting

### Port Already in Use

```bash
# Kill processes on default ports
npx kill-port 2427
npx kill-port 2426

# Or use custom ports in .env
FRONTEND_PORT=3000
PROXY_PORT=3001
```

### API Connection Issues

```bash
# Check proxy server health
curl http://localhost:2426/health

# Check frontend accessibility
curl http://localhost:2427

# Restart services
npm run dev  # local
# or
docker-compose up -d --build  # Docker
```

### CORS Errors

The proxy server automatically allows requests from the configured frontend port. If you're still getting CORS errors:

1. Verify both servers are running
2. Check port configuration in `.env`
3. Ensure frontend URL matches your setup

## 🔒 Security Notes

- API keys are stored in browser session/local storage (not in environment variables)
- The proxy server runs as non-root user in Docker
- CORS is properly configured for security
- No sensitive data is logged

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test with both local development and Docker: `npm run dev` and `docker-compose up -d --build`
5. Submit a pull request

## 📁 Project Structure

```
character-card-generator/
├── src/
│   ├── scripts/
│   │   ├── api.js          # API communication
│   │   ├── config.js       # Configuration management
│   │   ├── main.js         # Main application logic
│   │   └── ...             # Other utilities
│   └── styles/
│       └── main.css        # Application styles
├── proxy/
│   ├── server.js           # Express proxy server
│   └── package.json        # Proxy dependencies
├── .docker/
│   └── nginx/              # Docker nginx configuration
├── index.html              # Main HTML file
├── package.json            # Dependencies and scripts
├── docker-compose.yml      # Docker orchestration
├── Dockerfile*             # Docker build files
├── .env.template           # Environment variables template
└── README.md               # This file
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Report bugs and feature requests via GitHub issues
- **Documentation**: Check this README and the `LOCAL_DEVELOPMENT.md` file
- **Community**: Join discussions in the repository's discussions section

---

**Enjoy creating amazing characters with AI! 🎭✨**