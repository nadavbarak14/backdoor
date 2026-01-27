/**
 * ChatMessage Component
 *
 * Renders an individual chat message with appropriate styling for user
 * or assistant roles. Supports markdown rendering for assistant messages.
 *
 * @module components/chat/ChatMessage
 */

"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { ChatMessageProps } from "@/lib/chat/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check } from "lucide-react";

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
 * Copy button component for copying message content to clipboard.
 */
function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="copy-button"
      aria-label={copied ? "Copied" : "Copy message"}
      title={copied ? "Copied!" : "Copy to clipboard"}
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-500" />
      ) : (
        <Copy className="w-4 h-4" />
      )}
    </button>
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
              remarkPlugins={[remarkGfm]}
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
                // Style tables
                table: ({ children }) => (
                  <div className="overflow-x-auto my-3">
                    <table className="w-full border-collapse text-sm">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-[var(--bg-secondary)] border-b border-[var(--border-subtle)]">
                    {children}
                  </thead>
                ),
                th: ({ children }) => (
                  <th className="px-3 py-2 text-left text-[var(--text-secondary)] font-semibold">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 border-b border-[var(--border-subtle)]">
                    {children}
                  </td>
                ),
                // Style lists
                ul: ({ children }) => (
                  <ul className="list-disc list-inside my-2 space-y-1">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside my-2 space-y-1">
                    {children}
                  </ol>
                ),
                // Style blockquotes
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-[var(--accent-primary)] pl-4 my-2 italic text-[var(--text-secondary)]">
                    {children}
                  </blockquote>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            message.content
          )}
        </div>
        <div data-slot="message-meta" className="flex items-center gap-2 mt-1">
          <span data-slot="message-time" className="message-time">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
          {isAssistant && <CopyButton content={message.content} />}
        </div>
      </div>
    </div>
  );
}
