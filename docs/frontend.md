# Frontend Application

## Overview

The Basketball Analytics Platform includes a React-based single-page application (SPA) for browsing and managing basketball data. The frontend provides an intuitive interface for exploring leagues, teams, players, games, and triggering data syncs with real-time progress tracking.

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 7.x | Build tool and dev server |
| TanStack Query | 5.x | Server state management |
| React Router | 7.x | Client-side routing |
| Tailwind CSS | 4.x | Utility-first styling |
| Lucide React | - | Icon library |

## Project Structure

```
frontend/
├── README.md               # Frontend-specific documentation
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite config with API proxy
├── index.html              # HTML entry point
├── src/
│   ├── main.tsx            # React entry point
│   ├── App.tsx             # Root component with providers
│   ├── router.tsx          # Route definitions
│   ├── index.css           # Tailwind CSS
│   ├── api/
│   │   └── client.ts       # API fetch functions
│   ├── hooks/
│   │   └── useApi.ts       # TanStack Query hooks
│   ├── types/
│   │   └── index.ts        # TypeScript types
│   ├── components/
│   │   ├── Layout.tsx      # App shell with sidebar
│   │   └── ui.tsx          # Reusable UI components
│   └── pages/
│       ├── Dashboard.tsx   # Home with overview stats
│       ├── LeagueList.tsx  # All leagues
│       ├── LeagueDetail.tsx # League with seasons
│       ├── TeamList.tsx    # Teams with search
│       ├── TeamDetail.tsx  # Team roster and games
│       ├── PlayerList.tsx  # Players with filters
│       ├── PlayerDetail.tsx # Player stats and history
│       ├── GameList.tsx    # Games list
│       ├── GameDetail.tsx  # Box score view
│       └── SyncPage.tsx    # Sync with SSE progress
```

## Pages and Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Overview with entity counts and recent sync activity |
| `/leagues` | League List | All leagues with season counts |
| `/leagues/:id` | League Detail | League info and links to seasons |
| `/teams` | Team List | Searchable/filterable team list |
| `/teams/:id` | Team Detail | Team roster and game history |
| `/players` | Player List | Searchable/filterable player list |
| `/players/:id` | Player Detail | Career stats, team history, game log |
| `/games` | Game List | All games with scores |
| `/games/:id` | Game Detail | Full box score with player links |
| `/sync` | Sync | Trigger syncs with real-time progress |

## Features

### Data Browsing
- **Hierarchical navigation**: League → Season → Teams → Players → Games
- **Entity linking**: Click any team/player name to navigate to their page
- **Search and filters**: Find teams by name, players by position
- **Pagination**: Handle large datasets efficiently

### Sync Management
- **Source selection**: Choose from Winner, Euroleague, NBA
- **Season input**: Specify which season to sync
- **Real-time progress**: SSE streaming shows sync progress live
- **Skip detection**: Shows how many games are already synced
- **Error handling**: Displays errors without stopping the sync

### UI Components
- **Responsive layout**: Sidebar navigation, mobile-friendly
- **Loading states**: Spinners during data fetching
- **Error handling**: User-friendly error messages
- **Empty states**: Helpful messages when no data exists

## Development

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running at http://localhost:8000

### Getting Started

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The dev server runs at http://localhost:3000 with hot module replacement.

### API Proxy

The Vite dev server proxies `/api/*` requests to the backend:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### Building for Production

```bash
npm run build    # Creates dist/ folder
npm run preview  # Preview production build
```

## API Integration

### Data Fetching

The frontend uses TanStack Query for data fetching with automatic caching:

```typescript
// Example: Fetching players
const { data, isLoading, error } = usePlayers({ search: 'Jordan' });
```

### SSE Streaming for Sync

Sync progress uses Server-Sent Events for real-time updates:

```typescript
for await (const { event, data } of streamSync(source, seasonId)) {
  switch (event) {
    case 'start':
      // Sync started, total games known
      break;
    case 'progress':
      // Currently syncing a game
      break;
    case 'synced':
      // Game successfully synced
      break;
    case 'complete':
      // Sync finished
      break;
  }
}
```

## Related Documentation

- [API Reference](api/README.md) - Backend API documentation
- [Sync Architecture](sync/architecture.md) - How data sync works
- [Frontend README](../frontend/README.md) - Detailed frontend docs
