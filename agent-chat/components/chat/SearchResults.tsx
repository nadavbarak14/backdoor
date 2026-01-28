"use client";

/**
 * SearchResults Component
 *
 * Displays autocomplete search results for the @-mention picker.
 * Supports keyboard navigation and mouse selection.
 *
 * @module components/chat/SearchResults
 */

import { useEffect, useRef } from "react";
import { User, Users, Calendar, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EntityType, SearchResultsProps } from "@/lib/chat/types";

/**
 * Get the icon for an entity type.
 */
function getEntityIcon(type: EntityType) {
  switch (type) {
    case "player":
      return User;
    case "team":
      return Users;
    case "season":
      return Calendar;
    case "league":
      return Trophy;
    default:
      return User;
  }
}

/**
 * Get the label for an entity type.
 */
function getEntityLabel(type: EntityType): string {
  switch (type) {
    case "player":
      return "Player";
    case "team":
      return "Team";
    case "season":
      return "Season";
    case "league":
      return "League";
    default:
      return type;
  }
}

/**
 * SearchResults displays autocomplete results with keyboard navigation.
 *
 * @example
 * ```tsx
 * <SearchResults
 *   results={results}
 *   isLoading={isLoading}
 *   highlightedIndex={highlightedIndex}
 *   onSelect={handleSelect}
 *   onHighlightChange={setHighlightedIndex}
 * />
 * ```
 */
export function SearchResults({
  results,
  isLoading,
  highlightedIndex,
  onSelect,
  onHighlightChange,
}: SearchResultsProps) {
  const listRef = useRef<HTMLUListElement>(null);

  // Scroll highlighted item into view
  useEffect(() => {
    if (listRef.current && highlightedIndex >= 0) {
      const items = listRef.current.querySelectorAll("[data-index]");
      const item = items[highlightedIndex] as HTMLElement | undefined;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex]);

  if (isLoading) {
    return (
      <div
        data-slot="search-results"
        className="p-4 text-center text-[var(--text-secondary)]"
      >
        <div className="inline-flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--accent-primary)] border-t-transparent" />
          <span>Searching...</span>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div
        data-slot="search-results"
        className="p-4 text-center text-[var(--text-secondary)]"
      >
        No results found
      </div>
    );
  }

  return (
    <ul
      ref={listRef}
      data-slot="search-results"
      className="max-h-[300px] overflow-y-auto py-1"
      role="listbox"
    >
      {results.map((result, index) => {
        const Icon = getEntityIcon(result.type);
        const isHighlighted = index === highlightedIndex;

        return (
          <li
            key={`${result.type}-${result.id}`}
            data-index={index}
            role="option"
            aria-selected={isHighlighted}
            className={cn(
              "flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors",
              isHighlighted
                ? "bg-[var(--accent-primary)]/10 text-[var(--text-primary)]"
                : "text-[var(--text-secondary)] hover:bg-white/5"
            )}
            onClick={() => onSelect(result)}
            onMouseEnter={() => onHighlightChange(index)}
          >
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full",
                result.type === "player" && "bg-blue-500/20 text-blue-400",
                result.type === "team" && "bg-green-500/20 text-green-400",
                result.type === "season" && "bg-purple-500/20 text-purple-400",
                result.type === "league" && "bg-amber-500/20 text-amber-400"
              )}
            >
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1 overflow-hidden">
              <div className="truncate font-medium text-[var(--text-primary)]">
                {result.name}
              </div>
              {result.context && (
                <div className="truncate text-xs text-[var(--text-secondary)]">
                  {result.context}
                </div>
              )}
            </div>
            <span className="shrink-0 rounded bg-white/5 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">
              {getEntityLabel(result.type)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
