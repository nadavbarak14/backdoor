"use client";

/**
 * MentionPicker Component
 *
 * Main dropdown component for the @-mention feature.
 * Provides two modes:
 * - Browse mode: Hierarchical navigation (League -> Season -> Team -> Player)
 * - Search mode: Fast typeahead search across all entities
 *
 * @module components/chat/MentionPicker
 */

import { useEffect, useCallback, useState, useRef } from "react";
import { Search, FolderTree } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAutocomplete } from "@/hooks/useAutocomplete";
import { useBrowse } from "@/hooks/useBrowse";
import { SearchResults } from "./SearchResults";
import { BrowsePanel } from "./BrowsePanel";
import type { MentionPickerProps, BrowseItem } from "@/lib/chat/types";

type PickerMode = "search" | "browse";

/**
 * MentionPicker provides a dropdown for selecting entities to mention.
 *
 * When searchQuery is empty, shows browse mode.
 * When user types, automatically switches to search mode.
 *
 * @example
 * ```tsx
 * <MentionPicker
 *   isOpen={showPicker}
 *   searchQuery={mentionQuery}
 *   onSelect={handleMentionSelect}
 *   onClose={() => setShowPicker(false)}
 *   position={{ top: 100, left: 50 }}
 * />
 * ```
 */
export function MentionPicker({
  isOpen,
  searchQuery,
  onSelect,
  onClose,
  position,
}: MentionPickerProps) {
  const [mode, setMode] = useState<PickerMode>("browse");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Hooks for search and browse
  const {
    results: searchResults,
    isLoading: isSearchLoading,
    search,
    clear: clearSearch,
  } = useAutocomplete();

  const {
    items: browseItems,
    parent: browseParent,
    isLoading: isBrowseLoading,
    navigateInto,
    navigateBack,
    reset: resetBrowse,
  } = useBrowse();

  // Switch mode based on search query
  useEffect(() => {
    if (searchQuery && searchQuery.trim()) {
      setMode("search");
      search(searchQuery);
      setHighlightedIndex(0);
    } else {
      setMode("browse");
      clearSearch();
    }
  }, [searchQuery, search, clearSearch]);

  // Reset when opened
  useEffect(() => {
    if (isOpen) {
      setHighlightedIndex(0);
      if (!searchQuery) {
        resetBrowse();
      }
    }
  }, [isOpen, searchQuery, resetBrowse]);

  // Handle click outside to close
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!isOpen) return;

      const items = mode === "search" ? searchResults : browseItems;

      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          setHighlightedIndex((prev) =>
            prev < items.length - 1 ? prev + 1 : prev
          );
          break;

        case "ArrowUp":
          event.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
          break;

        case "Enter":
          event.preventDefault();
          if (mode === "search" && searchResults[highlightedIndex]) {
            onSelect(searchResults[highlightedIndex]);
          } else if (mode === "browse" && browseItems[highlightedIndex]) {
            const item = browseItems[highlightedIndex];
            if (item.hasChildren) {
              navigateInto(item);
              setHighlightedIndex(0);
            } else {
              onSelect({
                id: item.id,
                type: item.type,
                name: item.name,
              });
            }
          }
          break;

        case "Escape":
          event.preventDefault();
          onClose();
          break;

        case "Backspace":
          // In browse mode with no search query, go back
          if (mode === "browse" && !searchQuery && browseParent) {
            event.preventDefault();
            navigateBack();
            setHighlightedIndex(0);
          }
          break;

        case "Tab":
          // Switch modes
          event.preventDefault();
          setMode((prev) => (prev === "search" ? "browse" : "search"));
          setHighlightedIndex(0);
          break;
      }
    },
    [
      isOpen,
      mode,
      searchResults,
      browseItems,
      highlightedIndex,
      browseParent,
      searchQuery,
      onSelect,
      onClose,
      navigateInto,
      navigateBack,
    ]
  );

  // Attach keyboard listener
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Handle browse item selection
  const handleBrowseSelect = useCallback(
    (item: BrowseItem) => {
      onSelect({
        id: item.id,
        type: item.type,
        name: item.name,
      });
    },
    [onSelect]
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div
      ref={pickerRef}
      data-slot="mention-picker"
      className={cn(
        "absolute z-50 w-80 overflow-hidden rounded-lg",
        "border border-[var(--border-subtle)] bg-[var(--bg-secondary)]",
        "shadow-lg shadow-black/20"
      )}
      style={
        position
          ? { top: position.top, left: position.left }
          : { bottom: "100%", left: 0, marginBottom: "8px" }
      }
    >
      {/* Mode tabs */}
      <div className="flex border-b border-[var(--border-subtle)]">
        <button
          className={cn(
            "flex flex-1 items-center justify-center gap-2 px-3 py-2 text-sm transition-colors",
            mode === "search"
              ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          )}
          onClick={() => setMode("search")}
        >
          <Search className="h-4 w-4" />
          <span>Search</span>
        </button>
        <button
          className={cn(
            "flex flex-1 items-center justify-center gap-2 px-3 py-2 text-sm transition-colors",
            mode === "browse"
              ? "bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          )}
          onClick={() => {
            setMode("browse");
            clearSearch();
          }}
        >
          <FolderTree className="h-4 w-4" />
          <span>Browse</span>
        </button>
      </div>

      {/* Content */}
      {mode === "search" ? (
        <SearchResults
          results={searchResults}
          isLoading={isSearchLoading}
          highlightedIndex={highlightedIndex}
          onSelect={onSelect}
          onHighlightChange={setHighlightedIndex}
        />
      ) : (
        <BrowsePanel
          items={browseItems}
          parent={browseParent}
          isLoading={isBrowseLoading}
          onNavigate={(item) => {
            navigateInto(item);
            setHighlightedIndex(0);
          }}
          onSelect={handleBrowseSelect}
          onBack={() => {
            navigateBack();
            setHighlightedIndex(0);
          }}
        />
      )}

      {/* Keyboard hints */}
      <div className="border-t border-[var(--border-subtle)] px-3 py-1.5">
        <div className="flex items-center justify-between text-[10px] text-[var(--text-secondary)]">
          <span>
            <kbd className="rounded bg-white/10 px-1">↑↓</kbd> navigate
          </span>
          <span>
            <kbd className="rounded bg-white/10 px-1">Enter</kbd> select
          </span>
          <span>
            <kbd className="rounded bg-white/10 px-1">Tab</kbd> switch mode
          </span>
          <span>
            <kbd className="rounded bg-white/10 px-1">Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
