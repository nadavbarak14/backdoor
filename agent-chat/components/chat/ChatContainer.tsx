/**
 * ChatContainer Component
 *
 * Main layout wrapper for the chat interface including the animated
 * background, header with branding, and footer area.
 *
 * @module components/chat/ChatContainer
 */

import { cn } from "@/lib/utils";
import type { ChatContainerProps } from "@/lib/chat/types";

/**
 * Animated basketball court background with visual effects.
 */
function CourtBackground() {
  return (
    <div data-slot="court-background" className="court-background" aria-hidden="true">
      <div className="court-lines">
        <div className="center-circle" />
        <div className="three-point-line left" />
        <div className="three-point-line right" />
        <div className="half-court-line" />
      </div>
      <div className="ambient-glow" />
      <div className="noise-overlay" />
    </div>
  );
}

/**
 * Basketball logo icon with animated SVG.
 */
function BasketballLogo() {
  return (
    <div className="logo-icon">
      <svg viewBox="0 0 40 40" className="basketball-icon" aria-hidden="true">
        <circle cx="20" cy="20" r="18" className="ball-outline" />
        <path d="M2 20 Q20 15 38 20" className="ball-seam" />
        <path d="M2 20 Q20 25 38 20" className="ball-seam" />
        <path d="M20 2 Q15 20 20 38" className="ball-seam" />
        <path d="M20 2 Q25 20 20 38" className="ball-seam" />
      </svg>
    </div>
  );
}

/**
 * Header section with branding and live indicator.
 */
function ChatHeader() {
  return (
    <header data-slot="chat-header" className="chat-header">
      <div className="logo-section">
        <BasketballLogo />
        <div className="logo-text">
          <h1>BACKDOOR</h1>
          <span className="logo-subtitle">AI ANALYTICS</span>
        </div>
      </div>
      <div className="live-indicator" role="status" aria-label="Live data connection active">
        <span className="pulse-dot" aria-hidden="true" />
        <span>LIVE DATA</span>
      </div>
    </header>
  );
}

/**
 * Footer wrapper with powered-by attribution.
 */
function ChatFooter({ children }: { children?: React.ReactNode }) {
  return (
    <footer data-slot="chat-footer" className="chat-footer">
      {children}
      <div className="footer-info">
        <span>Powered by advanced basketball analytics</span>
      </div>
    </footer>
  );
}

/**
 * Main container component for the chat interface.
 *
 * Provides the complete layout structure including:
 * - Animated court background
 * - Header with BACKDOOR branding and live indicator
 * - Main content area for messages or welcome screen
 * - Footer with input area and attribution
 *
 * @param children - Main content (MessageList or WelcomeScreen)
 * @param footer - Footer content (ChatInput)
 *
 * @example
 * ```tsx
 * <ChatContainer
 *   footer={<ChatInput value={input} onChange={setInput} onSubmit={handleSubmit} />}
 * >
 *   {messages.length === 0 ? (
 *     <WelcomeScreen onPromptSelect={setInput} />
 *   ) : (
 *     <MessageList messages={messages} isLoading={isTyping} />
 *   )}
 * </ChatContainer>
 * ```
 */
export function ChatContainer({
  children,
  footer,
  className,
  ...props
}: ChatContainerProps & React.ComponentProps<"div">) {
  return (
    <div
      data-slot="chat-container"
      className={cn("chat-container", className)}
      {...props}
    >
      <CourtBackground />
      <ChatHeader />

      <main data-slot="chat-main" className="chat-main">
        {children}
      </main>

      <ChatFooter>{footer}</ChatFooter>
    </div>
  );
}
