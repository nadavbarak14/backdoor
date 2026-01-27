# Agent Chat

AI-powered chat interface for the Basketball Analytics Platform.

## Purpose

This is the frontend chat application that provides an AI agent interface for querying basketball analytics data. Built with Next.js, Vercel AI SDK, and shadcn/ui.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `app/` | Next.js App Router pages and layouts |
| `app/page.tsx` | Main chat interface page |
| `app/layout.tsx` | Root layout with metadata |
| `app/globals.css` | Global styles and CSS variables |
| `components/ui/` | shadcn/ui components (button, input, card, scroll-area) |
| `lib/utils.ts` | Utility functions (cn for className merging) |
| `components.json` | shadcn/ui configuration |

## Tech Stack

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui
- **AI Integration**: Vercel AI SDK (`ai` package)
- **Package Manager**: pnpm

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm (`npm install -g pnpm`)

### Installation

```bash
# Navigate to the agent-chat directory
cd agent-chat

# Install dependencies
pnpm install

# Copy environment variables
cp .env.local.example .env.local

# Edit .env.local with your backend URL
```

### Environment Variables

Create a `.env.local` file based on `.env.local.example`:

```bash
# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# API endpoints (optional, defaults to /api/v1)
NEXT_PUBLIC_API_BASE_PATH=/api/v1
```

### Development

```bash
# Start development server (runs on port 3001)
pnpm dev
```

Open [http://localhost:3001](http://localhost:3001) in your browser.

### Build

```bash
# Build for production
pnpm build

# Start production server
pnpm start
```

### Linting

```bash
pnpm lint
```

## Available shadcn/ui Components

The following components are pre-installed:

- `Button` - Action buttons with variants
- `Input` - Text input fields
- `Card` - Card container components
- `ScrollArea` - Scrollable content areas

To add more components:

```bash
pnpm dlx shadcn@latest add [component-name]
```

## Dependencies

### Internal Dependencies

- Depends on the Basketball Analytics backend API

### External Dependencies

| Package | Purpose |
|---------|---------|
| `ai` | Vercel AI SDK for chat functionality |
| `lucide-react` | Icon library |
| `class-variance-authority` | Component variant styling |
| `clsx` | Conditional className utility |
| `tailwind-merge` | Tailwind class merging |

## Related Documentation

- [Vercel AI SDK Documentation](https://sdk.vercel.ai/docs)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [Next.js Documentation](https://nextjs.org/docs)
