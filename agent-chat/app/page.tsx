"use client";

/**
 * Chat Page
 *
 * Main chat interface for the BACKDOOR AI Analytics application.
 * Manages message state via Vercel AI SDK's useChat hook with
 * session-based conversation history.
 *
 * @module app/page
 */

import { useState, useEffect, useRef } from "react";
import { useChat } from "@ai-sdk/react";
import {
  ChatContainer,
  MentionInput,
  MessageList,
  WelcomeScreen,
} from "@/components/chat";
import { RefreshCw } from "lucide-react";
import type { Message } from "@/lib/chat/types";
import { API_URL } from "@/lib/chat/constants";
import { clearSession, getSessionId } from "@/lib/session";

/**
 * Main chat page component.
 *
 * Handles:
 * - Message state management via useChat hook
 * - Session-based conversation history
 * - Real-time streaming from the AI backend
 * - Clear conversation functionality
 */
export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>("");
  const [isHydrated, setIsHydrated] = useState(false);

  // Store the transformed message (with @type:id) to send to backend
  // while UI shows the display version (with @Name)
  const pendingTransformedMessage = useRef<string | null>(null);

  // Initialize session ID on client side after hydration
  useEffect(() => {
    const id = getSessionId();
    setSessionId(id);
    setIsHydrated(true);
  }, []);

  const {
    messages,
    input,
    setInput,
    append,
    isLoading,
    setMessages,
    error,
    reload,
  } = useChat({
    api: `${API_URL}/api/v1/chat/stream`,
    // Pass session ID in both header and body for reliability through proxy
    headers: sessionId
      ? {
          "X-Session-ID": sessionId,
        }
      : undefined,
    body: sessionId
      ? {
          session_id: sessionId,
        }
      : undefined,
    streamProtocol: "data",
    onError: (err) => {
      console.error("Chat error:", err);
    },
    // Transform the last user message to use @type:id format before sending
    experimental_prepareRequestBody: ({ messages: chatMessages }) => {
      const transformedMessages = chatMessages.map((msg, idx) => {
        // Only transform the last user message if we have a pending transformation
        if (
          idx === chatMessages.length - 1 &&
          msg.role === "user" &&
          pendingTransformedMessage.current
        ) {
          const transformed = {
            ...msg,
            content: pendingTransformedMessage.current,
          };
          pendingTransformedMessage.current = null; // Clear after use
          return transformed;
        }
        return msg;
      });

      return {
        messages: transformedMessages,
        session_id: sessionId,
      };
    },
  });

  /**
   * Handles form submission for chat messages.
   * Receives the transformed message with @type:id format for the backend,
   * but displays the original input (with @Name) in the UI.
   */
  const handleSubmit = (transformedMessage?: string) => {
    if (!isHydrated) return;

    const displayMessage = input.trim();
    if (!displayMessage) return;

    // Store the transformed message (with @type:id) to send to backend
    // If no transformation needed, send the display message as-is
    pendingTransformedMessage.current = transformedMessage || displayMessage;

    // Append the DISPLAY message (with @Name) so UI looks friendly
    append({
      role: "user",
      content: displayMessage,
    });

    // Clear the input
    setInput("");
  };

  /**
   * Handles quick prompt selection from welcome screen.
   * Populates the input with the selected prompt.
   */
  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt);
  };

  /**
   * Clears the current conversation and starts a new session.
   */
  const handleClearConversation = () => {
    clearSession();
    setMessages([]);
    setSessionId(getSessionId());
  };

  // Convert useChat messages to our Message type
  const chatMessages: Message[] = messages.map((msg) => ({
    id: msg.id,
    role: msg.role as "user" | "assistant",
    content: msg.content,
    timestamp: msg.createdAt || new Date(),
  }));

  return (
    <ChatContainer
      footer={
        <MentionInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isLoading || !isHydrated}
          onClear={messages.length > 0 ? handleClearConversation : undefined}
        />
      }
    >
      {chatMessages.length === 0 ? (
        <WelcomeScreen onPromptSelect={handleQuickPrompt} />
      ) : (
        <MessageList messages={chatMessages} isLoading={isLoading} />
      )}
      {error && (
        <div className="error-container">
          <p>Something went wrong. Please try again.</p>
          <button onClick={() => reload()} className="retry-button">
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      )}
    </ChatContainer>
  );
}
