/**
 * ChatMessage Component
 *
 * Renders an individual chat message with appropriate styling for user
 * or assistant roles. Supports markdown rendering for assistant messages.
 *
 * @module components/chat/ChatMessage
 */

"use client";

import { cn } from "@/lib/utils";
import type { ChatMessageProps } from "@/lib/chat/types";
import ReactMarkdown from "react-markdown";

/**
 * AI assistant avatar icon displayed next to assistant messages.
 */
function AssistantAvatar() {
  return (
    <div data-slot="message-avatar" className="message-avatar">
      <svg viewBox="0 0 24 24" className="ai-icon" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12 L11 15 L16 9" />
      </svg>
    </div>
  );
}

/**
 * Renders a single chat message with role-specific styling.
 *
 * - User messages appear on the right with an orange gradient background
 * - Assistant messages appear on the left with an avatar and dark background
 * - Assistant messages render markdown content
 *
 * @param message - The message object to render
 *
 * @example
 * ```tsx
 * <ChatMessage
 *   message={{
 *     id: "1",
 *     role: "user",
 *     content: "Who are the top scorers?",
 *     timestamp: new Date()
 *   }}
 * />
 * ```
 */
export function ChatMessage({ message, className, ...props }: ChatMessageProps) {
  const isAssistant = message.role === "assistant";

  return (
    <div
      data-slot="chat-message"
      className={cn("message", message.role, className)}
      {...props}
    >
      {isAssistant && <AssistantAvatar />}
      <div data-slot="message-content" className="message-content">
        <div data-slot="message-bubble" className="message-bubble">
          {isAssistant ? (
            <ReactMarkdown
              components={{
                // Ensure links open in new tab
                a: ({ children, ...linkProps }) => (
                  <a
                    {...linkProps}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--accent-primary)] hover:underline"
                  >
                    {children}
                  </a>
                ),
                // Style code blocks
                code: ({ children, ...codeProps }) => (
                  <code
                    {...codeProps}
                    className="bg-[var(--bg-secondary)] px-1.5 py-0.5 rounded text-[var(--accent-blue)] font-mono text-sm"
                  >
                    {children}
                  </code>
                ),
                // Style pre blocks for code
                pre: ({ children, ...preProps }) => (
                  <pre
                    {...preProps}
                    className="bg-[var(--bg-secondary)] p-3 rounded-lg my-2 overflow-x-auto"
                  >
                    {children}
                  </pre>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            message.content
          )}
        </div>
        <span data-slot="message-time" className="message-time">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
