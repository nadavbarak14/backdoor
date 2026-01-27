/**
 * MessageList Component
 *
 * Scrollable container for chat messages with auto-scroll behavior
 * and typing indicator support.
 *
 * @module components/chat/MessageList
 */

"use client";

import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { MessageListProps } from "@/lib/chat/types";
import { ChatMessage } from "./ChatMessage";
import { StreamingIndicator } from "./StreamingIndicator";

/**
 * AI assistant avatar icon for the typing indicator.
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
 * Renders a scrollable list of chat messages.
 *
 * Features:
 * - Auto-scrolls to bottom when new messages arrive
 * - Shows typing indicator when isLoading is true
 * - Smooth scroll behavior for better UX
 *
 * @param messages - Array of messages to display
 * @param isLoading - Whether to show the typing indicator
 *
 * @example
 * ```tsx
 * <MessageList
 *   messages={messages}
 *   isLoading={isTyping}
 * />
 * ```
 */
export function MessageList({
  messages,
  isLoading = false,
  className,
  ...props
}: MessageListProps & React.ComponentProps<"div">) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div
      data-slot="message-list"
      className={cn("messages-container", className)}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
      {...props}
    >
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}

      {isLoading && (
        <div className="message assistant">
          <AssistantAvatar />
          <div className="message-content">
            <StreamingIndicator />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} aria-hidden="true" />
    </div>
  );
}
