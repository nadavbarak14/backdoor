/**
 * Session Management Module
 *
 * Provides helper functions for managing chat session IDs.
 * Sessions are stored in sessionStorage to persist across page refreshes
 * but clear when the browser tab is closed.
 *
 * @module lib/session
 */

const SESSION_STORAGE_KEY = "chat-session-id";

/**
 * Generate a UUID v4.
 * Uses crypto.randomUUID if available, otherwise falls back to a manual implementation.
 */
const generateUUID = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

/**
 * Get or create a session ID.
 *
 * Retrieves the existing session ID from sessionStorage, or generates
 * a new UUID if no session exists.
 *
 * @returns The current session ID
 *
 * @example
 * const sessionId = getSessionId();
 * // Returns existing ID or generates new one like "550e8400-e29b-41d4-a716-446655440000"
 */
export const getSessionId = (): string => {
  if (typeof window === "undefined") {
    // SSR: return a placeholder that will be replaced client-side
    return "";
  }

  let sessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = generateUUID();
    sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
};

/**
 * Clear the current session.
 *
 * Removes the session ID from sessionStorage. The next call to
 * getSessionId() will generate a new session ID.
 *
 * Use this when the user wants to start a fresh conversation.
 *
 * @example
 * clearSession();
 * // Session ID is now removed, next getSessionId() will create new one
 */
export const clearSession = (): void => {
  if (typeof window === "undefined") {
    return;
  }
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
};

/**
 * Check if a session exists.
 *
 * @returns True if a session ID exists in storage
 *
 * @example
 * if (hasSession()) {
 *   console.log("Resuming existing conversation");
 * }
 */
export const hasSession = (): boolean => {
  if (typeof window === "undefined") {
    return false;
  }
  return sessionStorage.getItem(SESSION_STORAGE_KEY) !== null;
};
