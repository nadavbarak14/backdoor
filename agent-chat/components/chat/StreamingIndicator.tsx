/**
 * StreamingIndicator Component
 *
 * Animated typing indicator shown while the AI assistant is generating a response.
 * Uses the existing CSS animation from globals.css.
 *
 * @module components/chat/StreamingIndicator
 */

import { cn } from "@/lib/utils";

/**
 * Displays an animated typing indicator with three bouncing dots.
 *
 * @example
 * ```tsx
 * {isLoading && <StreamingIndicator />}
 * ```
 */
export function StreamingIndicator({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="streaming-indicator"
      className={cn("typing-indicator", className)}
      aria-label="Assistant is typing"
      role="status"
      {...props}
    >
      <span />
      <span />
      <span />
    </div>
  );
}
