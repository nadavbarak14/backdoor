/**
 * ToolCallBlock Component
 *
 * Renders a collapsible tool call block showing the tool name, arguments,
 * and expandable JSON response.
 *
 * @module components/chat/ToolCallBlock
 */

"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, Wrench, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Props for the ToolCallBlock component.
 */
export interface ToolCallBlockProps {
  /** Name of the tool that was called */
  name: string;
  /** Arguments passed to the tool */
  args: Record<string, unknown>;
  /** JSON result from the tool */
  result: string;
  /** Whether the tool call succeeded */
  success: boolean;
}

/**
 * Renders a collapsible tool call with name, args, and expandable result.
 *
 * @example
 * ```tsx
 * <ToolCallBlock
 *   name="get_player_stats"
 *   args={{ player_id: "abc-123" }}
 *   result='{"points": 25, "rebounds": 10}'
 *   success={true}
 * />
 * ```
 */
export function ToolCallBlock({ name, args, result, success }: ToolCallBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format args for display
  const argsDisplay = Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");

  // Try to parse and pretty-print the result JSON
  let formattedResult = result;
  try {
    const parsed = JSON.parse(result);
    formattedResult = JSON.stringify(parsed, null, 2);
  } catch {
    // Keep original if not valid JSON
  }

  return (
    <div className="tool-call-block my-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-secondary)] overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2 text-left",
          "hover:bg-[var(--bg-tertiary)] transition-colors",
          "text-sm font-medium"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-[var(--text-secondary)] flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-[var(--text-secondary)] flex-shrink-0" />
        )}
        <Wrench className="w-4 h-4 text-[var(--accent-primary)] flex-shrink-0" />
        <code className="text-[var(--accent-blue)]">{name}</code>
        {argsDisplay && (
          <span className="text-[var(--text-secondary)] text-xs truncate">
            ({argsDisplay})
          </span>
        )}
        <span className="ml-auto flex-shrink-0">
          {success ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
        </span>
      </button>

      {isExpanded && (
        <div className="border-t border-[var(--border-subtle)]">
          <pre className="p-3 text-xs overflow-x-auto max-h-80 overflow-y-auto bg-[var(--bg-primary)] text-[var(--text-primary)] font-mono">
            {formattedResult}
          </pre>
        </div>
      )}
    </div>
  );
}
