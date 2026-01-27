/**
 * Chat Type Definitions
 *
 * Core TypeScript interfaces for the chat system including messages,
 * quick prompts, and component props.
 *
 * @module lib/chat/types
 */

import type { LucideIcon } from "lucide-react";

/**
 * Represents a chat message between user and assistant.
 *
 * @property id - Unique identifier for the message
 * @property role - Whether this is a user or assistant message
 * @property content - The text content of the message (may contain markdown)
 * @property timestamp - When the message was created
 *
 * @example
 * ```ts
 * const message: Message = {
 *   id: "msg-123",
 *   role: "user",
 *   content: "Who are the top scorers?",
 *   timestamp: new Date()
 * };
 * ```
 */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

/**
 * Quick prompt suggestion shown in the welcome screen.
 *
 * @property icon - Lucide icon component to display
 * @property label - Short button label
 * @property prompt - Full prompt text to insert into input
 *
 * @example
 * ```ts
 * const prompt: QuickPrompt = {
 *   icon: TrendingUp,
 *   label: "Top Scorers",
 *   prompt: "Who are the top scorers this season?"
 * };
 * ```
 */
export interface QuickPrompt {
  icon: LucideIcon;
  label: string;
  prompt: string;
}

/**
 * Props for the ChatMessage component.
 */
export interface ChatMessageProps extends React.ComponentProps<"div"> {
  /** The message to render */
  message: Message;
}

/**
 * Props for the MessageList component.
 */
export interface MessageListProps {
  /** Array of messages to display */
  messages: Message[];
  /** Whether to show the typing indicator */
  isLoading?: boolean;
}

/**
 * Props for the ChatInput component.
 */
export interface ChatInputProps {
  /** Current input value */
  value: string;
  /** Handler for input changes */
  onChange: (value: string) => void;
  /** Handler for form submission */
  onSubmit: () => void;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * Props for the WelcomeScreen component.
 */
export interface WelcomeScreenProps {
  /** Handler when a quick prompt is selected */
  onPromptSelect: (prompt: string) => void;
}

/**
 * Props for the ChatContainer component.
 */
export interface ChatContainerProps {
  /** Child content to render in the main area */
  children: React.ReactNode;
  /** Footer content (typically the input area) */
  footer?: React.ReactNode;
}
