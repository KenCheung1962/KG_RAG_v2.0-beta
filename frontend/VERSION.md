# KG RAG WebUI v1.1-beta

## Version History

### v1.1-beta (2026-03-12)
- **Error Handling**: Global error handlers + toast notifications
- **Loading States**: Skeleton loaders for stats
- **Accessibility**: ARIA labels, keyboard navigation, focus indicators
- **E2E Tests**: Playwright setup (10/12 passing)
- **Bug Fix**: Stats display not updating after skeleton load

### v1.0-beta (2026-03-11)
- Initial Vite + TypeScript rewrite
- Modular architecture (API, Components, Stores, Utils)

## Running

```bash
cd /Users/ken/clawd_workspace/projects/KG_RAG/v1.1-beta
npm install
npm run dev
# Opens at http://localhost:8081/
```

## API Server

Required: `http://localhost:8002` (pgvector API)
