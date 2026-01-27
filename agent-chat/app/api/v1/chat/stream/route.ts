/**
 * Chat Stream API Route Handler
 *
 * Proxies streaming chat requests to the backend FastAPI server.
 * Uses proper streaming support to avoid buffering issues with Next.js rewrites.
 *
 * @module app/api/v1/chat/stream/route
 */

import { NextRequest } from "next/server";

// Backend URL for server-side calls (not exposed to client)
// Defaults to localhost:9000 for local development
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:9000";

/**
 * POST /api/v1/chat/stream
 *
 * Proxies chat messages to the backend and streams the response.
 * Passes through the X-Session-ID header for conversation history.
 */
export async function POST(request: NextRequest) {
  try {
    const sessionId = request.headers.get("X-Session-ID");
    const body = await request.json();

    // Forward request to backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(sessionId && { "X-Session-ID": sessionId }),
      },
      body: JSON.stringify(body),
    });

    // Check for errors
    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error("Backend error:", backendResponse.status, errorText);
      return new Response(
        JSON.stringify({ error: "Backend request failed", details: errorText }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Check if we have a body to stream
    if (!backendResponse.body) {
      return new Response(
        JSON.stringify({ error: "No response body from backend" }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Stream the response back to the client
    // Using TransformStream to ensure proper streaming without buffering
    const { readable, writable } = new TransformStream();

    // Pipe the backend response to our transform stream
    // Silently handle aborted connections (user navigated away, mobile disconnect)
    backendResponse.body.pipeTo(writable).catch(() => {
      // Connection aborted - this is normal, don't log as error
    });

    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "X-Vercel-AI-Data-Stream": "v1",
      },
    });
  } catch (error) {
    console.error("Chat stream error:", error);
    return new Response(
      JSON.stringify({ error: "Failed to connect to backend", details: String(error) }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
