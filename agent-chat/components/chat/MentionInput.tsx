"use client";

/**
 * MentionInput Component
 *
 * Enhanced chat input with @-mention support.
 * Wraps the base ChatInput and adds:
 * - @ trigger detection
 * - MentionPicker dropdown
 * - Mention insertion and tracking
 * - Message transformation on send
 *
 * @module components/chat/MentionInput
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { Send, Trash2, AtSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MentionPicker } from "./MentionPicker";
import { INPUT_PLACEHOLDER } from "@/lib/chat/constants";
import {
  detectMentionTrigger,
  insertMention,
  transformForSend,
} from "@/lib/chat/mention-utils";
import type { Mention, MentionEntity } from "@/lib/chat/types";

interface MentionInputProps {
  /** Current input value */
  value: string;
  /** Handler for input changes */
  onChange: (value: string) => void;
  /** Handler for form submission - receives transformed message */
  onSubmit: (transformedMessage: string) => void;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Handler for clearing the conversation */
  onClear?: () => void;
  /** Additional class names */
  className?: string;
}

/**
 * MentionInput provides chat input with @-mention autocomplete.
 *
 * @example
 * ```tsx
 * <MentionInput
 *   value={input}
 *   onChange={setInput}
 *   onSubmit={(msg) => sendMessage(msg)}
 *   disabled={isLoading}
 *   onClear={handleClear}
 * />
 * ```
 */
export function MentionInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = INPUT_PLACEHOLDER,
  onClear,
  className,
}: MentionInputProps) {
  const [showPicker, setShowPicker] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [cursorPosition, setCursorPosition] = useState(0);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  /**
   * Handle input changes and detect @ trigger.
   */
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      const newCursor = e.target.selectionStart || 0;

      onChange(newValue);
      setCursorPosition(newCursor);

      // Detect @ trigger
      const query = detectMentionTrigger(newValue, newCursor);
      if (query !== null) {
        setMentionQuery(query);
        setShowPicker(true);
      } else {
        setShowPicker(false);
        setMentionQuery("");
      }

      // Clean up mentions that were deleted
      setMentions((prev) =>
        prev.filter((m) => {
          const mentionText = `@${m.displayName}`;
          const inText = newValue.includes(mentionText);
          return inText;
        })
      );
    },
    [onChange]
  );

  /**
   * Handle mention selection from picker.
   */
  const handleMentionSelect = useCallback(
    (entity: MentionEntity) => {
      const result = insertMention(value, cursorPosition, entity);

      onChange(result.text);
      setMentions((prev) => [...prev, result.mention]);
      setShowPicker(false);
      setMentionQuery("");

      // Focus input and set cursor position
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.setSelectionRange(
            result.cursorPosition,
            result.cursorPosition
          );
        }
      }, 0);
    },
    [value, cursorPosition, onChange]
  );

  /**
   * Handle form submission with message transformation.
   */
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!value.trim() || disabled) return;

      // Transform message: replace @DisplayName with @type:id
      const transformedMessage = transformForSend(value, mentions);
      onSubmit(transformedMessage);

      // Clear mentions after send
      setMentions([]);
    },
    [value, disabled, mentions, onSubmit]
  );

  /**
   * Handle keyboard events.
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // If picker is open, let it handle navigation keys
      if (showPicker) {
        if (["ArrowUp", "ArrowDown", "Enter", "Escape", "Tab"].includes(e.key)) {
          // Don't prevent default for these - picker handles them
          return;
        }
      }

      // Submit on Enter (without shift)
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!value.trim() || disabled) return;

        const transformedMessage = transformForSend(value, mentions);
        onSubmit(transformedMessage);
        setMentions([]);
      }

      // Open picker with @ key (handled by input change, but we can also trigger manually)
      if (e.key === "@") {
        // Let the character be typed, then check trigger
      }
    },
    [showPicker, value, disabled, mentions, onSubmit]
  );

  /**
   * Close picker when clicking outside.
   */
  const handleClosePicker = useCallback(() => {
    setShowPicker(false);
    setMentionQuery("");
  }, []);

  /**
   * Manually trigger the mention picker.
   */
  const handleTriggerMention = useCallback(() => {
    if (inputRef.current) {
      const cursor = inputRef.current.selectionStart || value.length;
      const before = value.slice(0, cursor);
      const after = value.slice(cursor);

      // Insert @ at cursor
      const newValue = before + "@" + after;
      onChange(newValue);
      setCursorPosition(cursor + 1);
      setMentionQuery("");
      setShowPicker(true);

      // Focus and position cursor after @
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.setSelectionRange(cursor + 1, cursor + 1);
        }
      }, 0);
    }
  }, [value, onChange]);

  /**
   * Track cursor position on selection change.
   */
  const handleSelect = useCallback(
    (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
      const target = e.target as HTMLTextAreaElement;
      setCursorPosition(target.selectionStart || 0);
    },
    []
  );

  const isSubmitDisabled = !value.trim() || disabled;

  return (
    <form
      data-slot="mention-input"
      onSubmit={handleSubmit}
      className={cn("input-form", className)}
    >
      <div ref={containerRef} className="input-wrapper relative">
        {onClear && (
          <Button
            type="button"
            variant="ghost"
            className="clear-button"
            onClick={onClear}
            disabled={disabled}
            aria-label="Clear conversation"
          >
            <Trash2 className="clear-icon" aria-hidden="true" />
          </Button>
        )}

        {/* @ trigger button */}
        <Button
          type="button"
          variant="ghost"
          className="mention-trigger-button"
          onClick={handleTriggerMention}
          disabled={disabled}
          aria-label="Mention player, team, or league"
          style={{
            position: "absolute",
            left: onClear ? "52px" : "12px",
            top: "50%",
            transform: "translateY(-50%)",
            padding: "4px",
            height: "32px",
            width: "32px",
            zIndex: 10,
          }}
        >
          <AtSign className="h-4 w-4 text-[var(--text-secondary)]" aria-hidden="true" />
        </Button>

        <textarea
          ref={inputRef}
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onSelect={handleSelect}
          placeholder={placeholder}
          disabled={disabled}
          className="chat-input resize-none"
          aria-label="Chat message input"
          rows={1}
          style={{
            paddingLeft: onClear ? "88px" : "48px",
            minHeight: "48px",
            maxHeight: "120px",
          }}
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

        {/* Mention Picker */}
        <MentionPicker
          isOpen={showPicker}
          searchQuery={mentionQuery}
          onSelect={handleMentionSelect}
          onClose={handleClosePicker}
        />
      </div>
    </form>
  );
}
