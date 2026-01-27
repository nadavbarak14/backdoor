"use client";

/**
 * Chat Page
 *
 * Main chat interface for the BACKDOOR AI Analytics application.
 * Manages message state and orchestrates the modular chat components.
 *
 * @module app/page
 */

import { useState } from "react";
import {
  ChatContainer,
  ChatInput,
  MessageList,
  WelcomeScreen,
} from "@/components/chat";
import type { Message } from "@/lib/chat/types";
import { SIMULATED_AI_RESPONSE } from "@/lib/chat/constants";

/**
 * Main chat page component.
 *
 * Handles:
 * - Message state management
 * - User message submission
 * - Simulated AI responses (to be replaced with real API)
 * - Typing indicator state
 */
export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  /**
   * Handles message submission.
   * Adds user message to the list and triggers simulated AI response.
   */
  const handleSubmit = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    // Simulate AI response (will be replaced with actual API call)
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: SIMULATED_AI_RESPONSE,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  /**
   * Handles quick prompt selection from welcome screen.
   * Populates the input with the selected prompt.
   */
  const handleQuickPrompt = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <ChatContainer
      footer={
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isTyping}
        />
      }
    >
      {messages.length === 0 ? (
        <WelcomeScreen onPromptSelect={handleQuickPrompt} />
      ) : (
        <MessageList messages={messages} isLoading={isTyping} />
      )}
    </ChatContainer>
  );
}
