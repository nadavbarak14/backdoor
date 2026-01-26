# Basketball Analytics Frontend

React-based single-page application for browsing basketball analytics data.

## Purpose

Provides a modern, interactive UI for:
- Browsing leagues, seasons, teams, players, and games
- Viewing player stats and game box scores
- Running data syncs with real-time progress

## Tech Stack

| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool and dev server |
| TanStack Query | Data fetching and caching |
| React Router | Client-side routing |
| Tailwind CSS | Styling |
| Lucide Icons | Icon library |

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running at http://localhost:8000

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend runs at http://localhost:3000 and proxies API requests to the backend.

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── README.md           # This file
├── package.json        # Dependencies and scripts
├── vite.config.ts      # Vite configuration with API proxy
├── index.html          # HTML entry point
├── src/
│   ├── main.tsx        # React entry point
│   ├── App.tsx         # Root component with providers
│   ├── router.tsx      # React Router configuration
│   ├── index.css       # Tailwind CSS imports
│   ├── api/
│   │   └── client.ts   # API fetch functions
│   ├── hooks/
│   │   └── useApi.ts   # TanStack Query hooks
│   ├── types/
│   │   └── index.ts    # TypeScript type definitions
│   ├── components/
│   │   ├── Layout.tsx  # Main layout with sidebar
│   │   └── ui.tsx      # Reusable UI components
│   └── pages/
│       ├── Dashboard.tsx
│       ├── LeagueList.tsx
│       ├── LeagueDetail.tsx
│       ├── TeamList.tsx
│       ├── TeamDetail.tsx
│       ├── PlayerList.tsx
│       ├── PlayerDetail.tsx
│       ├── GameList.tsx
│       ├── GameDetail.tsx
│       └── SyncPage.tsx
```

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Overview with stats and recent activity |
| `/leagues` | League List | All leagues with season counts |
| `/leagues/:id` | League Detail | League info and seasons |
| `/teams` | Team List | Searchable team list |
| `/teams/:id` | Team Detail | Team roster and games |
| `/players` | Player List | Searchable player list |
| `/players/:id` | Player Detail | Stats and game log |
| `/games` | Game List | All games with scores |
| `/games/:id` | Game Detail | Full box score |
| `/sync` | Sync Page | Trigger syncs with progress |

## API Integration

The frontend connects to the FastAPI backend via the Vite dev proxy:

- All `/api/*` requests are proxied to `http://localhost:8000`
- SSE streaming is used for real-time sync progress
- TanStack Query caches responses for 5 minutes

## Data Flow

```
User Action
    ↓
React Component
    ↓
useApi Hook (TanStack Query)
    ↓
API Client (fetch)
    ↓
Vite Proxy
    ↓
FastAPI Backend
```

## Development Tips

1. **Start both servers**: Run the FastAPI backend and Vite frontend
2. **API docs**: Check http://localhost:8000/docs for API reference
3. **Hot reload**: Both frontend and backend support hot reload
4. **Query caching**: Use React Query DevTools to inspect cache

## Related Documentation

- [API Documentation](../docs/api/README.md)
- [Architecture](../docs/architecture.md)
- [Sync Documentation](../docs/sync/architecture.md)
