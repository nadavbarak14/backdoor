/**
 * ChatInput Component
 *
 * Text input with send button for composing chat messages.
 * Supports keyboard submission and disabled state.
 *
 * @module components/chat/ChatInput
 */

"use client";

import { useCallback } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ChatInputProps } from "@/lib/chat/types";
import { INPUT_PLACEHOLDER } from "@/lib/chat/constants";

/**
 * Renders a chat input field with send button.
 *
 * Features:
 * - Enter key submits the message
 * - Send button disabled when input is empty
 * - Accessible with proper ARIA attributes
 * - 44px minimum touch target for mobile
 *
 * @param value - Current input value
 * @param onChange - Handler for input changes
 * @param onSubmit - Handler for form submission
 * @param disabled - Whether the input is disabled
 * @param placeholder - Placeholder text
 *
 * @example
 * ```tsx
 * <ChatInput
 *   value={input}
 *   onChange={setInput}
 *   onSubmit={handleSubmit}
 *   disabled={isLoading}
 * />
 * ```
 */
export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = INPUT_PLACEHOLDER,
  className,
  ...props
}: ChatInputProps & Omit<React.ComponentProps<"form">, keyof ChatInputProps>) {
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!value.trim() || disabled) return;
      onSubmit();
    },
    [value, disabled, onSubmit]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!value.trim() || disabled) return;
        onSubmit();
      }
    },
    [value, disabled, onSubmit]
  );

  const isSubmitDisabled = !value.trim() || disabled;

  return (
    <form
      data-slot="chat-input"
      onSubmit={handleSubmit}
      className={cn("input-form", className)}
      {...props}
    >
      <div className="input-wrapper">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="chat-input"
          aria-label="Chat message input"
        />
        <Button
          type="submit"
          className="send-button"
          disabled={isSubmitDisabled}
          aria-label={isSubmitDisabled ? "Cannot send empty message" : "Send message"}
        >
          <Send className="send-icon" aria-hidden="true" />
          <span>SEND</span>
        </Button>
      </div>
    </form>
  );
}
