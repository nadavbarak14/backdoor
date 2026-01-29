/**
 * WelcomeScreen Component
 *
 * Initial state displayed when there are no messages in the chat.
 * Features an animated stats graphic and quick prompt buttons.
 *
 * @module components/chat/WelcomeScreen
 */

"use client";

import { cn } from "@/lib/utils";
import type { WelcomeScreenProps } from "@/lib/chat/types";
import { quickPrompts } from "@/lib/chat/constants";

/**
 * Animated bar chart graphic for visual interest.
 */
function StatsGraphic() {
  const barHeights = ["60%", "85%", "45%", "95%", "70%"];

  return (
    <div data-slot="stats-graphic" className="stats-graphic" aria-hidden="true">
      {barHeights.map((height, index) => (
        <div
          key={index}
          className="stat-bar"
          style={{ height }}
        />
      ))}
    </div>
  );
}

/**
 * Displays the welcome state with branding, description, and quick prompts.
 *
 * The quick prompts provide one-click access to common basketball analytics
 * queries, helping users get started quickly.
 *
 * @param onPromptSelect - Callback when a quick prompt button is clicked
 *
 * @example
 * ```tsx
 * <WelcomeScreen onPromptSelect={(prompt) => setInput(prompt)} />
 * ```
 */
export function WelcomeScreen({
  onPromptSelect,
  className,
  ...props
}: WelcomeScreenProps & React.ComponentProps<"div">) {
  return (
    <div
      data-slot="welcome-screen"
      className={cn("welcome-state", className)}
      style={{ overflow: 'visible', flex: 'none' }}
      {...props}
    >
      <div className="welcome-content">
        <StatsGraphic />

        <h2>READY TO ANALYZE</h2>
        <p>
          Ask me anything about basketball stats, player performance, team
          analytics, and game predictions.
        </p>

        <div data-slot="quick-prompts" className="quick-prompts" role="group" aria-label="Quick prompts">
          {quickPrompts.map((item, index) => (
            <button
              key={index}
              type="button"
              className="quick-prompt-btn"
              onClick={() => onPromptSelect(item.prompt)}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <item.icon className="prompt-icon" aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
