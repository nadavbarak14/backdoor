/**
 * Browse Team Players API Route Handler
 *
 * Proxies browse players requests to the backend FastAPI server.
 *
 * @module app/api/v1/browse/teams/[id]/players/route
 */

import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:9000";

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * Transform snake_case keys to camelCase in browse response.
 */
function transformBrowseResponse(data: {
  items: Array<{ has_children?: boolean; [key: string]: unknown }>;
  parent: { [key: string]: unknown } | null;
}) {
  return {
    items: data.items.map((item) => ({
      id: item.id,
      type: item.type,
      name: item.name,
      hasChildren: item.has_children ?? false,
    })),
    parent: data.parent,
  };
}

/**
 * GET /api/v1/browse/teams/[id]/players
 *
 * Returns players for a specific team.
 */
export async function GET(_request: Request, { params }: RouteParams) {
  try {
    const { id } = await params;
    const backendResponse = await fetch(
      `${BACKEND_URL}/api/v1/browse/teams/${id}/players`
    );

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      return NextResponse.json(
        { error: "Backend request failed", details: errorText },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(transformBrowseResponse(data));
  } catch (error) {
    console.error("Browse players error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend", details: String(error) },
      { status: 500 }
    );
  }
}
