/**
 * Browse Hook
 *
 * Provides hierarchical navigation for the @-mention browse feature.
 * Navigates: League -> Season -> Team -> Player
 *
 * @module hooks/useBrowse
 */

"use client";

import { useState, useCallback, useEffect } from "react";
import type {
  BrowseItem,
  BrowseParent,
  BrowseResponse,
  EntityType,
} from "@/lib/chat/types";
import { BACKEND_BACKEND_API_URL } from "@/lib/chat/constants";

/** Navigation path entry */
interface NavigationEntry {
  type: EntityType | "root";
  id?: string;
  name?: string;
}

interface UseBrowseResult {
  /** Current items at this level */
  items: BrowseItem[];
  /** Parent for breadcrumb navigation */
  parent: BrowseParent | null;
  /** Full navigation path for breadcrumb */
  path: NavigationEntry[];
  /** Whether data is being loaded */
  isLoading: boolean;
  /** Error message if load failed */
  error: string | null;
  /** Navigate into an item (drill down) */
  navigateInto: (item: BrowseItem) => void;
  /** Navigate back to parent level */
  navigateBack: () => void;
  /** Navigate to a specific path entry (breadcrumb click) */
  navigateTo: (index: number) => void;
  /** Reset to root level */
  reset: () => void;
}

/**
 * Hook for hierarchical browse navigation.
 *
 * @returns Browse state and navigation handlers
 *
 * @example
 * ```tsx
 * const { items, parent, isLoading, navigateInto, navigateBack } = useBrowse();
 *
 * return (
 *   <div>
 *     {parent && <button onClick={navigateBack}>Back to {parent.name}</button>}
 *     {items.map(item => (
 *       <button key={item.id} onClick={() => navigateInto(item)}>
 *         {item.name}
 *       </button>
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useBrowse(): UseBrowseResult {
  const [items, setItems] = useState<BrowseItem[]>([]);
  const [parent, setParent] = useState<BrowseParent | null>(null);
  const [path, setPath] = useState<NavigationEntry[]>([{ type: "root" }]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch data for the current navigation state.
   */
  const fetchData = useCallback(async (currentPath: NavigationEntry[]) => {
    setIsLoading(true);
    setError(null);

    try {
      const lastEntry = currentPath[currentPath.length - 1];
      let url: string;

      if (lastEntry.type === "root") {
        // Fetch leagues (root level)
        url = `${BACKEND_API_URL}/api/v1/browse/leagues`;
      } else if (lastEntry.type === "league") {
        // Fetch seasons for this league
        url = `${BACKEND_API_URL}/api/v1/browse/leagues/${lastEntry.id}/seasons`;
      } else if (lastEntry.type === "season") {
        // Fetch teams for this season
        url = `${BACKEND_API_URL}/api/v1/browse/seasons/${lastEntry.id}/teams`;
      } else if (lastEntry.type === "team") {
        // Fetch players for this team
        url = `${BACKEND_API_URL}/api/v1/browse/teams/${lastEntry.id}/players`;
      } else {
        // Player is a leaf node, no children
        setItems([]);
        setIsLoading(false);
        return;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to load: ${response.status}`);
      }

      const data: BrowseResponse = await response.json();

      setItems(data.items);
      setParent(data.parent);
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setItems([]);
      setIsLoading(false);
    }
  }, []);

  /**
   * Navigate into an item (drill down).
   */
  const navigateInto = useCallback(
    (item: BrowseItem) => {
      // Don't navigate into leaf nodes (players)
      if (!item.hasChildren) {
        return;
      }

      const newEntry: NavigationEntry = {
        type: item.type,
        id: item.id,
        name: item.name,
      };

      const newPath = [...path, newEntry];
      setPath(newPath);
      fetchData(newPath);
    },
    [path, fetchData]
  );

  /**
   * Navigate back to parent level.
   */
  const navigateBack = useCallback(() => {
    if (path.length <= 1) {
      return; // Already at root
    }

    const newPath = path.slice(0, -1);
    setPath(newPath);
    fetchData(newPath);
  }, [path, fetchData]);

  /**
   * Navigate to a specific path index (breadcrumb click).
   */
  const navigateTo = useCallback(
    (index: number) => {
      if (index < 0 || index >= path.length) {
        return;
      }

      const newPath = path.slice(0, index + 1);
      setPath(newPath);
      fetchData(newPath);
    },
    [path, fetchData]
  );

  /**
   * Reset to root level.
   */
  const reset = useCallback(() => {
    const rootPath: NavigationEntry[] = [{ type: "root" }];
    setPath(rootPath);
    fetchData(rootPath);
  }, [fetchData]);

  // Fetch initial data on mount
  useEffect(() => {
    fetchData(path);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    items,
    parent,
    path,
    isLoading,
    error,
    navigateInto,
    navigateBack,
    navigateTo,
    reset,
  };
}
