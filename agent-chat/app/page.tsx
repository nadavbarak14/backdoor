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

import { useEffect, useState } from "react";
import { useChat } from "@ai-sdk/react";
import {
  ChatContainer,
  ChatInput,
  MessageList,
  WelcomeScreen,
} from "@/components/chat";
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

  // Initialize session ID on client side
  useEffect(() => {
    setSessionId(getSessionId());
  }, []);

  const {
    messages,
    input,
    setInput,
    handleSubmit: submitChat,
    isLoading,
    setMessages,
  } = useChat({
    api: `${API_URL}/api/v1/chat/stream`,
    headers: sessionId
      ? {
          "X-Session-ID": sessionId,
        }
      : undefined,
    streamProtocol: "data",
  });

  /**
   * Handles form submission for chat messages.
   */
  const handleSubmit = () => {
    if (!input.trim()) return;
    submitChat();
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
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isLoading}
          onClear={messages.length > 0 ? handleClearConversation : undefined}
        />
      }
    >
      {chatMessages.length === 0 ? (
        <WelcomeScreen onPromptSelect={handleQuickPrompt} />
      ) : (
        <MessageList messages={chatMessages} isLoading={isLoading} />
      )}
    </ChatContainer>
  );
}
