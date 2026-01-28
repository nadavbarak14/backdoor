/**
 * Mention Utilities
 *
 * Helper functions for working with @-mentions in the chat input.
 *
 * @module lib/chat/mention-utils
 */

import type { Mention, MentionEntity } from "./types";

/**
 * Detect if the cursor is in a mention trigger position.
 * Returns the query text after @ if triggered, null otherwise.
 *
 * @param text - Full input text
 * @param cursorPosition - Current cursor position
 * @param existingMentions - Already completed mentions to exclude
 * @returns The mention query (text after @) or null
 *
 * @example
 * ```ts
 * detectMentionTrigger("Hello @ste", 10, []) // "ste"
 * detectMentionTrigger("Hello @stephen curry is", 16, []) // "stephen curry"
 * detectMentionTrigger("Hello world", 5, []) // null
 * ```
 */
export function detectMentionTrigger(
  text: string,
  cursorPosition: number,
  existingMentions: Mention[] = []
): string | null {
  // Look backwards from cursor for @
  const textBeforeCursor = text.slice(0, cursorPosition);

  // Find the last @ that isn't already part of a completed mention
  const lastAtIndex = textBeforeCursor.lastIndexOf("@");

  if (lastAtIndex === -1) {
    return null;
  }

  // Check if @ is at start or preceded by whitespace
  if (lastAtIndex > 0 && !/\s/.test(textBeforeCursor[lastAtIndex - 1])) {
    return null;
  }

  // Check if this @ is the start of an existing completed mention
  for (const mention of existingMentions) {
    if (mention.startIndex === lastAtIndex) {
      // This @ is part of a completed mention
      // Only trigger if cursor is inside the mention text (editing it)
      // If cursor is after the mention, don't trigger
      if (cursorPosition > mention.endIndex) {
        return null;
      }
    }
  }

  // Extract query (text between @ and cursor)
  const query = textBeforeCursor.slice(lastAtIndex + 1);

  // If query contains certain characters, it's not a mention trigger
  if (query.includes("@") || query.includes("\n")) {
    return null;
  }

  // If query ends with space and matches a completed mention, don't trigger
  // This handles the case right after inserting a mention
  for (const mention of existingMentions) {
    if (query.trim() === mention.displayName) {
      return null;
    }
  }

  return query;
}

/**
 * Insert a mention into the text, replacing the @query.
 *
 * @param text - Current input text
 * @param cursorPosition - Current cursor position
 * @param entity - Entity to insert as mention
 * @returns Object with new text and cursor position
 *
 * @example
 * ```ts
 * const result = insertMention(
 *   "Hello @ste",
 *   10,
 *   { id: "123", type: "player", name: "Stephen Curry" }
 * );
 * // result.text = "Hello @Stephen Curry "
 * // result.cursorPosition = 22
 * ```
 */
export function insertMention(
  text: string,
  cursorPosition: number,
  entity: MentionEntity
): { text: string; cursorPosition: number; mention: Mention } {
  const textBeforeCursor = text.slice(0, cursorPosition);
  const textAfterCursor = text.slice(cursorPosition);

  // Find the @ that started this mention
  const lastAtIndex = textBeforeCursor.lastIndexOf("@");

  if (lastAtIndex === -1) {
    throw new Error("No @ trigger found");
  }

  // Build the mention text (just the display name, not the @)
  const mentionText = `@${entity.name}`;

  // Build the new text
  const beforeAt = text.slice(0, lastAtIndex);
  const newText = beforeAt + mentionText + " " + textAfterCursor.trimStart();

  // Calculate new cursor position (after the mention and space)
  const newCursorPosition = lastAtIndex + mentionText.length + 1;

  // Create the mention object
  const mention: Mention = {
    id: entity.id,
    type: entity.type,
    displayName: entity.name,
    startIndex: lastAtIndex,
    endIndex: lastAtIndex + mentionText.length,
  };

  return {
    text: newText,
    cursorPosition: newCursorPosition,
    mention,
  };
}

/**
 * Transform the display text to the format sent to the AI.
 * Replaces @DisplayName with @type:id for each mention.
 *
 * @param text - Display text with @names
 * @param mentions - Array of mention objects
 * @returns Transformed text with @type:id format
 *
 * @example
 * ```ts
 * const mentions = [
 *   { id: "123", type: "player", displayName: "Stephen Curry", startIndex: 6, endIndex: 21 }
 * ];
 * transformForSend("Hello @Stephen Curry!", mentions);
 * // Returns: "Hello @player:123!"
 * ```
 */
export function transformForSend(text: string, mentions: Mention[]): string {
  if (mentions.length === 0) {
    return text;
  }

  let result = text;

  // Replace each @DisplayName with @type:id using string matching
  // This is more robust than using indices which can get out of sync
  for (const mention of mentions) {
    const mentionText = `@${mention.displayName}`;
    const replacement = `@${mention.type}:${mention.id}`;
    result = result.replace(mentionText, replacement);
  }

  return result;
}

/**
 * Parse mention markers from text to reconstruct mention objects.
 * Used when loading saved messages that contain @type:id format.
 *
 * @param text - Text containing @type:id markers
 * @returns Array of partial mention objects found
 *
 * @example
 * ```ts
 * parseMentionMarkers("Hello @player:123 and @team:456!");
 * // Returns: [
 * //   { type: "player", id: "123", startIndex: 6, endIndex: 17 },
 * //   { type: "team", id: "456", startIndex: 22, endIndex: 32 }
 * // ]
 * ```
 */
export function parseMentionMarkers(
  text: string
): Array<{ type: string; id: string; startIndex: number; endIndex: number }> {
  const regex = /@(player|team|season|league):([a-f0-9-]+)/gi;
  const mentions: Array<{
    type: string;
    id: string;
    startIndex: number;
    endIndex: number;
  }> = [];

  let match;
  while ((match = regex.exec(text)) !== null) {
    mentions.push({
      type: match[1].toLowerCase(),
      id: match[2],
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    });
  }

  return mentions;
}

/**
 * Get entity type icon name for styling.
 *
 * @param type - Entity type
 * @returns Icon identifier
 */
export function getEntityTypeColor(type: string): string {
  switch (type) {
    case "player":
      return "text-blue-400";
    case "team":
      return "text-green-400";
    case "season":
      return "text-purple-400";
    case "league":
      return "text-amber-400";
    default:
      return "text-gray-400";
  }
}
