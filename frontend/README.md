# LightRAG WebUI

A modern, modular web interface for LightRAG Knowledge Graph built with Vite + TypeScript.

## Features

- 📊 **Real-time Stats Dashboard** - Monitor documents, entities, relationships, and chunks
- 📥 **File Upload** - Support for multiple files and folders with duplicate detection
- 🔍 **Smart Querying** - Hybrid, Local, and Global query modes
- 🔗 **Query with Files** - Upload and query documents in one flow
- ⚡ **Auto-refresh** - Live stats updates with configurable intervals
- 🛡️ **XSS Protection** - All user input is properly escaped
- 📱 **Responsive Design** - Works on desktop and mobile

## Tech Stack

- **Build Tool**: [Vite](https://vitejs.dev/) - Fast dev server and optimized builds
- **Language**: [TypeScript](https://www.typescriptlang.org/) - Type safety and better DX
- **Architecture**: Modular components with clean separation of concerns
- **State Management**: Lightweight custom store (no external dependencies)
- **Styling**: CSS with custom properties (variables) for theming

## Project Structure

```
web_ui_vite/
├── src/
│   ├── api/              # API client and types
│   │   ├── client.ts     # HTTP request functions
│   │   ├── types.ts      # TypeScript interfaces
│   │   └── index.ts      # Re-exports
│   ├── components/       # UI components
│   │   ├── tabs/         # Tab components (Ingest, Query, etc.)
│   │   ├── FileList.ts   # File list renderer
│   │   ├── ProgressBar.ts # Progress indicator
│   │   └── StatsCard.ts  # Stats dashboard
│   ├── stores/           # State management
│   │   └── appStore.ts   # Central state store
│   ├── utils/            # Utility functions
│   │   ├── helpers.ts    # General utilities
│   │   ├── dom.ts        # DOM manipulation
│   │   └── index.ts      # Re-exports
│   ├── config.ts         # App configuration
│   ├── styles.css        # Global styles
│   └── main.ts           # Entry point
├── public/               # Static assets
├── tests/                # Test files
├── index.html            # HTML template
├── package.json          # Dependencies
├── vite.config.js        # Vite configuration
├── tsconfig.json         # TypeScript config
└── README.md             # This file
```

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) 18+ or [Bun](https://bun.sh/)
- LightRAG backend running on `http://localhost:8002`

### Installation

```bash
# Navigate to project
cd web_ui_vite

# Install dependencies
npm install

# Or with Bun
bun install
```

### Development

```bash
# Start dev server (port 8080)
npm run dev

# Or with Bun
bun run dev
```

The dev server will:
- Serve the UI on http://localhost:8080
- Proxy API calls to http://localhost:8002
- Enable Hot Module Replacement (HMR)

### Build for Production

```bash
# Create optimized build
npm run build

# Preview production build
npm run preview
```

## Configuration

### Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8002` | LightRAG backend URL |

### Code Style

```bash
# Run linter
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format
```

## Architecture Decisions

### Why Vite?

- **Fast HMR** - Instant updates during development
- **Optimized Builds** - Automatic code splitting and minification
- **TypeScript First** - Native TS support without complex setup
- **Modern ESM** - Uses native ES modules

### Why No Framework?

This project uses vanilla TypeScript with a component-based architecture:

- **Smaller Bundle** - No framework overhead (~0KB vs ~40KB for React)
- **Full Control** - No abstraction layers
- **Easy to Understand** - No framework-specific knowledge required
- **Sufficient for This Use Case** - Simple UI doesn't need complex state management

### State Management

Custom lightweight store in `src/stores/appStore.ts`:

```typescript
// Get state
const files = getSelectedFiles();

// Update state
addSelectedFile(file);

// Subscribe to changes
const unsubscribe = subscribe(() => {
  console.log('State changed!');
});
```

## API Endpoints

The WebUI communicates with the LightRAG backend:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/kg/stats` | GET | Knowledge graph statistics |
| `/api/v1/documents/stats` | GET | Document count |
| `/api/v1/documents` | GET | List documents |
| `/api/v1/documents/upload/json` | POST | Upload document |
| `/api/v1/documents/{id}/status` | GET | Check indexing status |
| `/api/v1/chat` | POST | Send query |
| `/api/v1/chat/with-doc` | POST | Query with file context |
| `/api/v1/clear` | DELETE | Clear all data |

## Browser Support

- Chrome/Edge 90+
- Firefox 90+
- Safari 15+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### v1.0.0

- Initial release
- Migrated from monolithic HTML to modular Vite architecture
- Added TypeScript for type safety
- Improved state management
- Better error handling and retry logic
- XSS protection
