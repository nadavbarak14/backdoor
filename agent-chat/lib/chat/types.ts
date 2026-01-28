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
  /** Handler for clearing the conversation (shows clear button when provided) */
  onClear?: () => void;
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

// =============================================================================
// @-Mention Types
// =============================================================================

/**
 * Types of entities that can be mentioned with @.
 */
export type EntityType = "player" | "team" | "season" | "league";

/**
 * A search result from the autocomplete API.
 *
 * @property id - UUID of the entity
 * @property type - Type of entity (player, team, season, league)
 * @property name - Display name
 * @property context - Additional context (e.g., team name for a player)
 *
 * @example
 * ```ts
 * const result: MentionEntity = {
 *   id: "550e8400-e29b-41d4-a716-446655440000",
 *   type: "player",
 *   name: "Stephen Curry",
 *   context: "Golden State Warriors"
 * };
 * ```
 */
export interface MentionEntity {
  id: string;
  type: EntityType;
  name: string;
  context?: string;
}

/**
 * A browse item in the hierarchical navigation.
 *
 * @property id - UUID of the entity
 * @property type - Type of entity
 * @property name - Display name
 * @property hasChildren - Whether this item can be expanded
 */
export interface BrowseItem {
  id: string;
  type: EntityType;
  name: string;
  hasChildren: boolean;
}

/**
 * Parent info for breadcrumb navigation in browse mode.
 */
export interface BrowseParent {
  id: string;
  type: EntityType;
  name: string;
}

/**
 * Response from the autocomplete API.
 */
export interface AutocompleteResponse {
  results: MentionEntity[];
}

/**
 * Response from the browse API.
 */
export interface BrowseResponse {
  items: BrowseItem[];
  parent: BrowseParent | null;
}

/**
 * A mention that has been inserted into the input.
 *
 * @property id - UUID of the mentioned entity
 * @property type - Type of entity
 * @property displayName - Name shown in the input
 * @property startIndex - Start position in the input text
 * @property endIndex - End position in the input text
 */
export interface Mention {
  id: string;
  type: EntityType;
  displayName: string;
  startIndex: number;
  endIndex: number;
}

/**
 * Props for the MentionPicker component.
 */
export interface MentionPickerProps {
  /** Whether the picker is open */
  isOpen: boolean;
  /** Current search query (text after @) */
  searchQuery: string;
  /** Handler when an entity is selected */
  onSelect: (entity: MentionEntity) => void;
  /** Handler to close the picker */
  onClose: () => void;
  /** Position for the dropdown */
  position?: { top: number; left: number };
}

/**
 * Props for the SearchResults component.
 */
export interface SearchResultsProps {
  /** Search results to display */
  results: MentionEntity[];
  /** Loading state */
  isLoading: boolean;
  /** Currently highlighted index for keyboard navigation */
  highlightedIndex: number;
  /** Handler when a result is selected */
  onSelect: (entity: MentionEntity) => void;
  /** Handler when highlighted index changes */
  onHighlightChange: (index: number) => void;
}

/**
 * Props for the BrowsePanel component.
 */
export interface BrowsePanelProps {
  /** Current items at this level */
  items: BrowseItem[];
  /** Parent for breadcrumb */
  parent: BrowseParent | null;
  /** Loading state */
  isLoading: boolean;
  /** Handler when navigating into an item */
  onNavigate: (item: BrowseItem) => void;
  /** Handler when selecting an item (for leaf nodes) */
  onSelect: (item: BrowseItem) => void;
  /** Handler to go back to parent */
  onBack: () => void;
}
