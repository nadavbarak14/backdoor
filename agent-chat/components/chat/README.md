# Chat Components

## Purpose

Modular, reusable chat UI components for the BACKDOOR AI Analytics interface. These components follow shadcn/ui patterns with `data-slot` attributes and use the `cn()` utility for className merging.

## Contents

| File | Description |
|------|-------------|
| `index.ts` | Public exports for all chat components |
| `ChatContainer.tsx` | Main layout wrapper with animated background, header, and footer |
| `ChatInput.tsx` | Text input with send button for composing messages |
| `ChatMessage.tsx` | Individual message rendering with user/assistant styling |
| `MessageList.tsx` | Scrollable message list with auto-scroll behavior |
| `StreamingIndicator.tsx` | Animated typing indicator for loading state |
| `WelcomeScreen.tsx` | Initial state with branding and quick prompts |

## Usage

```tsx
import {
  ChatContainer,
  ChatInput,
  MessageList,
  WelcomeScreen,
} from "@/components/chat";

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSubmit = () => {
    // Handle message submission
  };

  return (
    <ChatContainer
      footer={
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isTyping}
        />
      }
    >
      {messages.length === 0 ? (
        <WelcomeScreen onPromptSelect={setInput} />
      ) : (
        <MessageList messages={messages} isLoading={isTyping} />
      )}
    </ChatContainer>
  );
}
```

## Component Interfaces

### ChatContainer

Main layout wrapper providing the full chat UI structure.

```tsx
interface ChatContainerProps {
  children: React.ReactNode;  // Main content area
  footer?: React.ReactNode;   // Footer content (input area)
}
```

### ChatInput

Text input for composing messages with send button.

```tsx
interface ChatInputProps {
  value: string;                      // Current input value
  onChange: (value: string) => void;  // Input change handler
  onSubmit: () => void;               // Submit handler
  disabled?: boolean;                 // Disabled state
  placeholder?: string;               // Placeholder text
}
```

### ChatMessage

Renders a single chat message.

```tsx
interface ChatMessageProps extends React.ComponentProps<"div"> {
  message: Message;  // Message to render
}
```

### MessageList

Scrollable container for messages.

```tsx
interface MessageListProps {
  messages: Message[];   // Array of messages
  isLoading?: boolean;   // Show typing indicator
}
```

### WelcomeScreen

Initial empty state with quick prompts.

```tsx
interface WelcomeScreenProps {
  onPromptSelect: (prompt: string) => void;  // Quick prompt handler
}
```

### StreamingIndicator

Animated typing indicator (no props required).

## Dependencies

### Internal
- `@/lib/utils` - `cn()` utility for className merging
- `@/lib/chat/types` - TypeScript interfaces
- `@/lib/chat/constants` - Quick prompts and placeholder text
- `@/components/ui/button` - shadcn/ui Button component
- `@/components/ui/input` - shadcn/ui Input component

### External
- `react` - React hooks (useState, useRef, useEffect, useCallback)
- `lucide-react` - Send icon
- `react-markdown` - Markdown rendering for assistant messages

## Styling

All components use CSS classes defined in `app/globals.css`. The styles follow the "Arena Night / Sports Broadcast" theme with:

- Dark background (`--bg-primary: #0a0a0f`)
- Basketball orange accent (`--accent-primary: #ff6b35`)
- Electric blue secondary (`--accent-blue: #00d4ff`)
- Animated court background elements
- Smooth transitions and micro-interactions

## Accessibility

- Proper ARIA labels on interactive elements
- Role attributes (`log`, `status`, `group`)
- `aria-live="polite"` on message list for screen readers
- Minimum 44px touch targets for mobile
- Keyboard navigation support (Enter to submit)

## Related Documentation

- [Types](/lib/chat/types.ts) - TypeScript interfaces
- [Constants](/lib/chat/constants.ts) - Static data
- [Global Styles](/app/globals.css) - CSS theme and animations
