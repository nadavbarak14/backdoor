"use client";

/**
 * BrowsePanel Component
 *
 * Displays hierarchical browse navigation for the @-mention picker.
 * Allows drilling down through: League -> Season -> Team -> Player
 *
 * @module components/chat/BrowsePanel
 */

import { ChevronRight, ChevronLeft, User, Users, Calendar, Trophy, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EntityType, BrowsePanelProps } from "@/lib/chat/types";

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
      return Trophy;
  }
}

/**
 * BrowsePanel provides hierarchical navigation for selecting entities.
 *
 * @example
 * ```tsx
 * <BrowsePanel
 *   items={items}
 *   parent={parent}
 *   isLoading={isLoading}
 *   onNavigate={handleNavigate}
 *   onSelect={handleSelect}
 *   onBack={handleBack}
 * />
 * ```
 */
export function BrowsePanel({
  items,
  parent,
  isLoading,
  onNavigate,
  onSelect,
  onBack,
}: BrowsePanelProps) {
  if (isLoading) {
    return (
      <div
        data-slot="browse-panel"
        className="flex items-center justify-center p-8"
      >
        <Loader2 className="h-6 w-6 animate-spin text-[var(--accent-primary)]" />
      </div>
    );
  }

  return (
    <div data-slot="browse-panel" className="flex flex-col">
      {/* Back button / Breadcrumb */}
      {parent && (
        <button
          onClick={onBack}
          className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-white/5 hover:text-[var(--text-primary)]"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>Back to {parent.name}</span>
        </button>
      )}

      {/* Items list */}
      {items.length === 0 ? (
        <div className="p-4 text-center text-[var(--text-secondary)]">
          No items found
        </div>
      ) : (
        <ul className="max-h-[300px] overflow-y-auto py-1" role="listbox">
          {items.map((item) => {
            const Icon = getEntityIcon(item.type);

            return (
              <li
                key={`${item.type}-${item.id}`}
                role="option"
                aria-selected={false}
                className={cn(
                  "flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors",
                  "text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)]"
                )}
                onClick={() => {
                  if (item.hasChildren) {
                    onNavigate(item);
                  } else {
                    onSelect(item);
                  }
                }}
              >
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full",
                    item.type === "player" && "bg-blue-500/20 text-blue-400",
                    item.type === "team" && "bg-green-500/20 text-green-400",
                    item.type === "season" && "bg-purple-500/20 text-purple-400",
                    item.type === "league" && "bg-amber-500/20 text-amber-400"
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <span className="flex-1 truncate font-medium text-[var(--text-primary)]">
                  {item.name}
                </span>
                {item.hasChildren ? (
                  <ChevronRight className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" />
                ) : (
                  <span className="shrink-0 rounded bg-[var(--accent-primary)]/10 px-1.5 py-0.5 text-[10px] text-[var(--accent-primary)]">
                    Select
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
