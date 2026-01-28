/**
 * Autocomplete Hook
 *
 * Provides debounced search functionality for the @-mention feature.
 * Searches across players, teams, seasons, and leagues.
 *
 * @module hooks/useAutocomplete
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { MentionEntity, AutocompleteResponse } from "@/lib/chat/types";

/** Default debounce delay in milliseconds */
const DEBOUNCE_DELAY = 150;

/** Default maximum results */
const DEFAULT_LIMIT = 10;

interface UseAutocompleteOptions {
  /** Debounce delay in ms (default: 150) */
  debounceMs?: number;
  /** Maximum results to fetch (default: 10) */
  limit?: number;
  /** Minimum query length to trigger search (default: 1) */
  minLength?: number;
}

interface UseAutocompleteResult {
  /** Search results */
  results: MentionEntity[];
  /** Whether a search is in progress */
  isLoading: boolean;
  /** Error message if search failed */
  error: string | null;
  /** Trigger a search with the given query */
  search: (query: string) => void;
  /** Clear results */
  clear: () => void;
}

/**
 * Hook for autocomplete search with debouncing.
 *
 * @param options - Configuration options
 * @returns Search state and handlers
 *
 * @example
 * ```tsx
 * const { results, isLoading, search, clear } = useAutocomplete();
 *
 * // Trigger search when user types after @
 * useEffect(() => {
 *   if (mentionQuery) {
 *     search(mentionQuery);
 *   } else {
 *     clear();
 *   }
 * }, [mentionQuery]);
 * ```
 */
export function useAutocomplete(
  options: UseAutocompleteOptions = {}
): UseAutocompleteResult {
  const {
    debounceMs = DEBOUNCE_DELAY,
    limit = DEFAULT_LIMIT,
    minLength = 1,
  } = options;

  const [results, setResults] = useState<MentionEntity[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track the latest query to handle race conditions
  const latestQueryRef = useRef<string>("");
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchResults = useCallback(
    async (query: string) => {
      // Cancel any in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Don't search if query is too short
      if (query.length < minLength) {
        setResults([]);
        setIsLoading(false);
        return;
      }

      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/v1/search/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`,
          {
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Search failed: ${response.status}`);
        }

        const data: AutocompleteResponse = await response.json();

        // Only update if this is still the latest query
        if (query === latestQueryRef.current) {
          setResults(data.results);
          setIsLoading(false);
        }
      } catch (err) {
        // Ignore abort errors
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }

        // Only update if this is still the latest query
        if (query === latestQueryRef.current) {
          setError(err instanceof Error ? err.message : "Search failed");
          setResults([]);
          setIsLoading(false);
        }
      }
    },
    [limit, minLength]
  );

  const search = useCallback(
    (query: string) => {
      latestQueryRef.current = query;

      // Clear any pending debounce
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      // If query is empty, clear immediately
      if (!query.trim()) {
        setResults([]);
        setIsLoading(false);
        return;
      }

      // Set loading immediately for responsive UI
      setIsLoading(true);

      // Debounce the actual fetch
      debounceTimeoutRef.current = setTimeout(() => {
        fetchResults(query);
      }, debounceMs);
    },
    [debounceMs, fetchResults]
  );

  const clear = useCallback(() => {
    latestQueryRef.current = "";
    setResults([]);
    setIsLoading(false);
    setError(null);

    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    results,
    isLoading,
    error,
    search,
    clear,
  };
}
