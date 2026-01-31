/**
 * Chat API Proxy Route
 *
 * Proxies chat requests to the Python backend, allowing the frontend
 * to call the same origin and avoid CORS issues.
 */

import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:9000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return new Response(`Backend error: ${response.status}`, {
        status: response.status,
      });
    }

    // Stream the response back to the client
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return new Response("Failed to connect to backend", { status: 502 });
  }
}
