/**
 * Search Autocomplete API Route Handler
 *
 * Proxies autocomplete search requests to the backend FastAPI server.
 *
 * @module app/api/v1/search/autocomplete/route
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:9000";

/**
 * GET /api/v1/search/autocomplete
 *
 * Proxies autocomplete queries to the backend search service.
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const q = searchParams.get("q") || "";
    const limit = searchParams.get("limit") || "10";

    const backendResponse = await fetch(
      `${BACKEND_URL}/api/v1/search/autocomplete?q=${encodeURIComponent(q)}&limit=${limit}`
    );

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      return NextResponse.json(
        { error: "Backend request failed", details: errorText },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Search autocomplete error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend", details: String(error) },
      { status: 500 }
    );
  }
}
